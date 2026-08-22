#!/usr/bin/env python3
"""Anonymous external HTTP/SEO evidence collector for the P1.7 staging gate.

The default mode is deliberately offline.  Network requests are made only when
``--allow-network`` is supplied.  The auditor performs anonymous GET requests,
does not use cookies or authentication handlers, refuses cross-host redirects,
and records hashes/counts instead of response bodies.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


SCHEMA_NAME = "observer-p1.7-http-audit"
SCHEMA_VERSION = "1.0.0"
MAX_BODY_BYTES = 2 * 1024 * 1024
NETWORK_SKIP_REASON = "network-disabled-use-allow-network"
FORBIDDEN_PRODUCTION_HOST = "theobserverofmultiverses.info"
NATIVE_STAGING_SUFFIX = ".wpcomstaging.com"
LOCAL_FIXTURE_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})
REDIRECT_CODES = frozenset({301, 302, 307, 308})
CACHE_HEADER_NAMES = (
    "cache-control",
    "etag",
    "last-modified",
    "age",
    "vary",
    "cf-cache-status",
    "x-cache",
    "x-cache-status",
)


class AuditConfigurationError(ValueError):
    """A deterministic, user-correctable configuration error."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class HTTPRecord:
    request_url: str
    final_url: str
    status: int
    headers: Mapping[str, str]
    body: bytes
    truncated: bool

    def body_evidence(self) -> dict[str, Any]:
        return {
            "body_bytes_observed": len(self.body),
            "body_sha256": hashlib.sha256(self.body).hexdigest(),
            "body_truncated": self.truncated,
        }


@dataclass(frozen=True)
class FetchOutcome:
    record: HTTPRecord | None = None
    error_code: str | None = None


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(  # type: ignore[override]
        self,
        req: urllib.request.Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> None:
        return None


class _SameHostRedirect(urllib.request.HTTPRedirectHandler):
    def __init__(self, expected_host: str, allowed_ports: set[int | None]) -> None:
        super().__init__()
        self.expected_host = expected_host
        self.allowed_ports = allowed_ports

    def redirect_request(  # type: ignore[override]
        self,
        req: urllib.request.Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> urllib.request.Request | None:
        parsed = urllib.parse.urlsplit(newurl)
        host = (parsed.hostname or "").rstrip(".").casefold()
        try:
            port = parsed.port
        except ValueError as exc:
            raise urllib.error.URLError("redirect-policy") from exc
        if (
            parsed.scheme.casefold() not in {"http", "https"}
            or host != self.expected_host
            or parsed.username is not None
            or parsed.password is not None
            or port not in self.allowed_ports
        ):
            raise urllib.error.URLError("redirect-policy")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class AnonymousFetcher:
    """Small urllib client with no proxy, cookies, or authentication state."""

    def __init__(
        self,
        *,
        allow_network: bool,
        expected_host: str,
        allowed_ports: set[int | None],
    ) -> None:
        self.allow_network = allow_network
        self.expected_host = expected_host
        proxyless = urllib.request.ProxyHandler({})
        self.following_opener = urllib.request.build_opener(
            proxyless,
            _SameHostRedirect(expected_host, allowed_ports),
        )
        self.raw_opener = urllib.request.build_opener(proxyless, _NoRedirect())

    def get(self, url: str, *, follow_redirects: bool = True) -> FetchOutcome:
        if not self.allow_network:
            return FetchOutcome(error_code=NETWORK_SKIP_REASON)

        parsed = urllib.parse.urlsplit(url)
        host = (parsed.hostname or "").rstrip(".").casefold()
        try:
            port = parsed.port
        except ValueError:
            return FetchOutcome(error_code="request-url-invalid-port")
        if (
            parsed.scheme.casefold() not in {"http", "https"}
            or host != self.expected_host
            or parsed.username is not None
            or parsed.password is not None
            or port not in {None, 80, 443, *self._configured_ports()}
        ):
            return FetchOutcome(error_code="request-url-policy-rejected")

        request = urllib.request.Request(
            url,
            method="GET",
            headers={
                "Accept": "text/html,application/json,application/xml,text/xml,text/plain;q=0.9,*/*;q=0.1",
                "Accept-Encoding": "identity",
                "User-Agent": "Observer-P1.7-Anonymous-Auditor/1.0",
            },
        )
        opener = self.following_opener if follow_redirects else self.raw_opener
        try:
            with opener.open(request, timeout=15.0) as response:
                return FetchOutcome(record=self._read_response(url, response))
        except urllib.error.HTTPError as exc:
            # Raw redirects and ordinary 4xx/5xx responses are evidence, not
            # transport failures.  HTTPError still exposes headers and a body.
            try:
                return FetchOutcome(record=self._read_response(url, exc))
            finally:
                exc.close()
        except urllib.error.URLError as exc:
            reason_name = type(getattr(exc, "reason", None)).__name__
            if str(getattr(exc, "reason", "")) == "redirect-policy":
                return FetchOutcome(error_code="redirect-policy-rejected")
            return FetchOutcome(error_code="network-error-" + reason_name)
        except TimeoutError:
            return FetchOutcome(error_code="network-timeout")
        except OSError as exc:
            return FetchOutcome(error_code="network-error-" + type(exc).__name__)

    def _configured_ports(self) -> set[int]:
        ports: set[int] = set()
        for opener in (self.following_opener,):
            for handler in opener.handlers:
                if isinstance(handler, _SameHostRedirect):
                    ports.update(port for port in handler.allowed_ports if port is not None)
        return ports

    @staticmethod
    def _read_response(request_url: str, response: Any) -> HTTPRecord:
        body = response.read(MAX_BODY_BYTES + 1)
        truncated = len(body) > MAX_BODY_BYTES
        if truncated:
            body = body[:MAX_BODY_BYTES]
        headers: dict[str, str] = {}
        for name in response.headers.keys():
            values = response.headers.get_all(name) or []
            headers[name.casefold()] = ", ".join(str(value).strip() for value in values)
        return HTTPRecord(
            request_url=request_url,
            final_url=response.geturl(),
            status=int(response.status),
            headers=headers,
            body=body,
            truncated=truncated,
        )


class _PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.canonical_hrefs: list[str] = []
        self.jsonld_scripts: list[str] = []
        self.robot_directives: list[str] = []
        self.anchor_hrefs: list[str] = []
        self.titles: list[str] = []
        self.meta_values: dict[str, list[str]] = {}
        self.visible_chunks: list[str] = []
        self._jsonld_buffer: list[str] | None = None
        self._title_buffer: list[str] | None = None
        self._ignored_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        lowered = tag.casefold()
        attributes = {name.casefold(): value or "" for name, value in attrs}
        if lowered in {"script", "style"}:
            self._ignored_depth += 1
        if lowered == "script" and attributes.get("type", "").casefold().split(";", 1)[0].strip() == "application/ld+json":
            self._jsonld_buffer = []
        elif lowered == "title":
            self._title_buffer = []
        elif lowered == "link":
            rel_tokens = {token.casefold() for token in attributes.get("rel", "").split()}
            if "canonical" in rel_tokens and attributes.get("href"):
                self.canonical_hrefs.append(attributes["href"])
        elif lowered == "meta":
            if attributes.get("name", "").casefold() in {"robots", "googlebot", "bingbot"}:
                self.robot_directives.append(attributes.get("content", ""))
            key = (attributes.get("property") or attributes.get("name") or "").casefold()
            if key in {
                "description",
                "og:title",
                "og:description",
                "og:url",
                "twitter:card",
                "twitter:title",
                "twitter:description",
            }:
                self.meta_values.setdefault(key, []).append(attributes.get("content", "").strip())
        elif lowered == "a" and attributes.get("href"):
            self.anchor_hrefs.append(attributes["href"])

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.casefold()
        if lowered == "script" and self._jsonld_buffer is not None:
            self.jsonld_scripts.append("".join(self._jsonld_buffer))
            self._jsonld_buffer = None
        if lowered == "title" and self._title_buffer is not None:
            self.titles.append(" ".join(" ".join(self._title_buffer).split()))
            self._title_buffer = None
        if lowered in {"script", "style"} and self._ignored_depth:
            self._ignored_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._jsonld_buffer is not None:
            self._jsonld_buffer.append(data)
        elif self._title_buffer is not None:
            self._title_buffer.append(data)
        elif self._ignored_depth == 0 and data.strip():
            self.visible_chunks.append(data)

    @property
    def visible_text(self) -> str:
        return " ".join(" ".join(self.visible_chunks).split())


@dataclass
class ParsedPage:
    parser: _PageParser
    jsonld_documents: list[Any]
    jsonld_parse_errors: int
    definition_ids: list[str]


class Ledger:
    def __init__(self) -> None:
        self.checks: list[dict[str, Any]] = []

    def add(
        self,
        check_id: str,
        status: str,
        *,
        target: str,
        evidence: Mapping[str, Any] | None = None,
    ) -> None:
        if status not in {"PASS", "FAIL", "SKIP"}:
            raise ValueError("invalid audit status")
        self.checks.append(
            {
                "id": check_id,
                "status": status,
                "target": target,
                "evidence": dict(evidence or {}),
            }
        )


class Auditor:
    def __init__(
        self,
        *,
        base_url: str,
        expected_host: str,
        allow_network: bool,
    ) -> None:
        self.base_url, self.base_parts, self.expected_host = self._validate_target(
            base_url, expected_host
        )
        self.netloc = self._normalized_netloc(self.base_parts)
        allowed_ports = {None, 80, 443, self.base_parts.port}
        self.fetcher = AnonymousFetcher(
            allow_network=allow_network,
            expected_host=self.expected_host,
            allowed_ports=allowed_ports,
        )
        self.allow_network = allow_network
        self.ledger = Ledger()
        self.registry_path = (
            Path(__file__).resolve().parents[1]
            / "wordpress-plugin"
            / "observer-research-registry"
            / "data"
            / "research_index.json"
        )
        try:
            self.registry_bytes = self.registry_path.read_bytes()
            self.registry = json.loads(self.registry_bytes.decode("utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise AuditConfigurationError("bundled-registry-unreadable") from exc
        self.works = sorted(self.registry.get("works", []), key=lambda item: item["priority"])
        if len(self.works) != 5:
            raise AuditConfigurationError("bundled-registry-work-count-not-five")
        self.archive_path = str(self.registry["index_page"]["site_path"])

    @staticmethod
    def _validate_target(
        base_url: str, expected_host: str
    ) -> tuple[str, urllib.parse.SplitResult, str]:
        expected = expected_host.strip().rstrip(".").casefold()
        if not expected or any(token in expected for token in ("/", "@", "?", "#", "://")):
            raise AuditConfigurationError("expected-host-invalid")
        if expected == FORBIDDEN_PRODUCTION_HOST or expected.endswith("." + FORBIDDEN_PRODUCTION_HOST):
            raise AuditConfigurationError("production-target-forbidden")
        local_fixture = expected in LOCAL_FIXTURE_HOSTS
        if not local_fixture and not (
            expected.startswith("staging-") and expected.endswith(NATIVE_STAGING_SUFFIX)
        ):
            raise AuditConfigurationError("expected-host-not-native-wordpress-staging")
        parsed = urllib.parse.urlsplit(base_url.strip())
        try:
            parsed_port = parsed.port
        except ValueError as exc:
            raise AuditConfigurationError("base-url-invalid-port") from exc
        host = (parsed.hostname or "").rstrip(".").casefold()
        if parsed.scheme.casefold() not in {"http", "https"}:
            raise AuditConfigurationError("base-url-scheme-not-http-or-https")
        if not local_fixture and parsed.scheme.casefold() != "https":
            raise AuditConfigurationError("native-staging-base-url-must-use-https")
        if parsed.username is not None or parsed.password is not None:
            raise AuditConfigurationError("base-url-credentials-forbidden")
        if parsed.query or parsed.fragment or parsed.path not in {"", "/"}:
            raise AuditConfigurationError("base-url-must-be-origin")
        if host != expected:
            raise AuditConfigurationError("base-url-host-mismatch")
        normalized_netloc = Auditor._normalized_netloc(parsed)
        normalized = urllib.parse.urlunsplit(
            (parsed.scheme.casefold(), normalized_netloc, "", "", "")
        )
        # Accessing parsed_port above also validates the port even when unused.
        _ = parsed_port
        return normalized, urllib.parse.urlsplit(normalized), expected

    @staticmethod
    def _normalized_netloc(parsed: urllib.parse.SplitResult) -> str:
        host = (parsed.hostname or "").rstrip(".").casefold()
        host_part = f"[{host}]" if ":" in host else host
        try:
            port = parsed.port
        except ValueError as exc:
            raise AuditConfigurationError("url-invalid-port") from exc
        if port is None:
            return host_part
        return f"{host_part}:{port}"

    def url(self, path: str, *, scheme: str | None = None, query: str = "") -> str:
        return urllib.parse.urlunsplit(
            (scheme or self.base_parts.scheme, self.netloc, path, query, "")
        )

    def canonical_url(self, path: str) -> str:
        return self.url(path, scheme="https")

    def run(self) -> dict[str, Any]:
        self.ledger.add(
            "config.registry_contract",
            "PASS",
            target="bundled-research-index",
            evidence={
                "archive_path": self.archive_path,
                "work_count": len(self.works),
                "work_ids": [work["id"] for work in self.works],
            },
        )
        self.ledger.add(
            "safety.anonymous_get_policy",
            "PASS",
            target=self.base_url,
            evidence={
                "allowed_method": "GET",
                "authentication": False,
                "cookies": False,
                "cross_host_redirects": False,
                "maximum_response_bytes": MAX_BODY_BYTES,
                "network_enabled": self.allow_network,
            },
        )

        routes: list[tuple[str, str, Mapping[str, Any] | None]] = [
            ("archive", self.archive_path, None)
        ]
        routes.extend((str(work["slug"]), str(work["site_path"]), work) for work in self.works)

        parsed_pages: dict[str, ParsedPage | None] = {}
        page_records: dict[str, HTTPRecord | None] = {}
        for key, path, _work in routes:
            record, parsed = self._audit_page_route(key, path)
            page_records[key] = record
            parsed_pages[key] = parsed

        self._audit_archive_coverage(parsed_pages["archive"], page_records["archive"])
        self._audit_unknown_route()
        self._audit_rest_endpoint()
        self._audit_robots()
        self._audit_sitemap()
        self._audit_qmd_boundary(parsed_pages.get("quantitative-modularity-defects"))
        self._audit_article_two_boundary(
            parsed_pages.get("weighted-gray-codon-external-validation")
        )
        self._audit_article_one_negative_exclusion(
            parsed_pages.get("weighted-gray-codon-geometry")
        )

        checks = sorted(self.ledger.checks, key=lambda item: item["id"])
        counts = Counter(check["status"] for check in checks)
        return {
            "schema": {"name": SCHEMA_NAME, "version": SCHEMA_VERSION},
            "target": {
                "base_url": self.base_url,
                "expected_host": self.expected_host,
                "network_allowed": self.allow_network,
            },
            "registry": {
                "sha256": hashlib.sha256(self.registry_bytes).hexdigest(),
                "source": "bundled-plugin-data/research_index.json",
            },
            "summary": {
                "PASS": counts.get("PASS", 0),
                "FAIL": counts.get("FAIL", 0),
                "SKIP": counts.get("SKIP", 0),
                "total": len(checks),
            },
            "checks": checks,
        }

    def _audit_page_route(self, key: str, path: str) -> tuple[HTTPRecord | None, ParsedPage | None]:
        prefix = f"route.{key}"
        target = self.canonical_url(path)
        outcome = self.fetcher.get(self.url(path))
        record = outcome.record
        if record is None:
            status = "SKIP" if outcome.error_code == NETWORK_SKIP_REASON else "FAIL"
            self.ledger.add(
                prefix + ".http_status",
                status,
                target=target,
                evidence={"reason": outcome.error_code},
            )
            for suffix in (
                "canonical_https",
                "canonical_tag",
                "social_metadata",
                "jsonld_parse",
                "jsonld_id_uniqueness",
                "stage_noindex",
                "cache_headers",
            ):
                self.ledger.add(
                    prefix + "." + suffix,
                    "SKIP",
                    target=target,
                    evidence={"reason": "route-fetch-unavailable"},
                )
            self._audit_redirect(prefix + ".trailing_slash_redirect", path.rstrip("/"), path)
            self._audit_redirect(prefix + ".http_to_https_redirect", path, path, force_http=True)
            return None, None

        content_type = record.headers.get("content-type", "").split(";", 1)[0].strip().casefold()
        status_ok = record.status == 200 and content_type == "text/html" and not record.truncated
        self.ledger.add(
            prefix + ".http_status",
            "PASS" if status_ok else "FAIL",
            target=target,
            evidence={
                "status": record.status,
                "content_type": content_type,
                **record.body_evidence(),
            },
        )
        final = self._normalize_url(record.final_url)
        expected = self._normalize_url(target)
        self.ledger.add(
            prefix + ".canonical_https",
            "PASS" if final == expected else "FAIL",
            target=target,
            evidence={"expected": expected, "observed": final},
        )
        self._audit_redirect(prefix + ".trailing_slash_redirect", path.rstrip("/"), path)
        self._audit_redirect(prefix + ".http_to_https_redirect", path, path, force_http=True)

        if not status_ok:
            for suffix in (
                "canonical_tag",
                "social_metadata",
                "jsonld_parse",
                "jsonld_id_uniqueness",
                "stage_noindex",
                "cache_headers",
            ):
                self.ledger.add(
                    prefix + "." + suffix,
                    "SKIP",
                    target=target,
                    evidence={"reason": "html-route-precondition-failed"},
                )
            return record, None

        page = self._parse_page(record)
        canonical_hrefs = [
            self._normalize_url(urllib.parse.urljoin(record.final_url, href))
            for href in page.parser.canonical_hrefs
        ]
        canonical_ok = len(canonical_hrefs) == 1 and canonical_hrefs[0] == expected
        self.ledger.add(
            prefix + ".canonical_tag",
            "PASS" if canonical_ok else "FAIL",
            target=target,
            evidence={
                "canonical_count": len(canonical_hrefs),
                "expected": expected,
                "observed": canonical_hrefs,
            },
        )
        metadata = page.parser.meta_values
        required_meta = (
            "description",
            "og:title",
            "og:description",
            "og:url",
            "twitter:card",
            "twitter:title",
            "twitter:description",
        )
        singleton = len(page.parser.titles) == 1 and all(
            len(metadata.get(key, [])) == 1 and bool(metadata[key][0]) for key in required_meta
        )
        title_coherent = singleton and (
            page.parser.titles[0] == metadata["og:title"][0] == metadata["twitter:title"][0]
        )
        description_coherent = singleton and (
            metadata["description"][0]
            == metadata["og:description"][0]
            == metadata["twitter:description"][0]
        )
        og_url_canonical = singleton and self._normalize_url(metadata["og:url"][0]) == expected
        social_ok = singleton and title_coherent and description_coherent and og_url_canonical
        self.ledger.add(
            prefix + ".social_metadata",
            "PASS" if social_ok else "FAIL",
            target=target,
            evidence={
                "title_count": len(page.parser.titles),
                "meta_counts": {key: len(metadata.get(key, [])) for key in required_meta},
                "title_sets_coherent": title_coherent,
                "description_sets_coherent": description_coherent,
                "og_url_is_canonical": og_url_canonical,
            },
        )
        parse_ok = bool(page.parser.jsonld_scripts) and page.jsonld_parse_errors == 0
        self.ledger.add(
            prefix + ".jsonld_parse",
            "PASS" if parse_ok else "FAIL",
            target=target,
            evidence={
                "script_count": len(page.parser.jsonld_scripts),
                "parsed_count": len(page.jsonld_documents),
                "parse_error_count": page.jsonld_parse_errors,
            },
        )
        if not parse_ok:
            self.ledger.add(
                prefix + ".jsonld_id_uniqueness",
                "SKIP",
                target=target,
                evidence={"reason": "jsonld-parse-precondition-failed"},
            )
        else:
            id_counts = Counter(page.definition_ids)
            duplicates = sorted(item for item, count in id_counts.items() if count > 1)
            ids_ok = bool(page.definition_ids) and not duplicates
            self.ledger.add(
                prefix + ".jsonld_id_uniqueness",
                "PASS" if ids_ok else "FAIL",
                target=target,
                evidence={
                    "definition_id_count": len(page.definition_ids),
                    "unique_definition_id_count": len(id_counts),
                    "duplicate_ids": duplicates,
                },
            )

        meta_noindex = any(
            re.search(r"(?:^|[\s,])noindex(?:$|[\s,])", directive.casefold())
            for directive in page.parser.robot_directives
        )
        header_noindex = "noindex" in record.headers.get("x-robots-tag", "").casefold()
        self.ledger.add(
            prefix + ".stage_noindex",
            "PASS" if meta_noindex or header_noindex else "FAIL",
            target=target,
            evidence={
                "meta_noindex": meta_noindex,
                "x_robots_tag_noindex": header_noindex,
            },
        )
        self._audit_cache(prefix + ".cache_headers", target, record)
        return record, page

    def _audit_redirect(
        self,
        check_id: str,
        request_path: str,
        canonical_path: str,
        *,
        force_http: bool = False,
    ) -> None:
        target = self.canonical_url(canonical_path)
        request_url = self.url(request_path, scheme="http" if force_http else None)
        outcome = self.fetcher.get(request_url, follow_redirects=False)
        if outcome.record is None:
            status = "SKIP" if outcome.error_code == NETWORK_SKIP_REASON else "FAIL"
            self.ledger.add(
                check_id,
                status,
                target=target,
                evidence={"reason": outcome.error_code},
            )
            return
        record = outcome.record
        location = record.headers.get("location", "")
        resolved = self._normalize_url(urllib.parse.urljoin(request_url, location)) if location else ""
        expected = self._normalize_url(target)
        passed = record.status in REDIRECT_CODES and resolved == expected
        self.ledger.add(
            check_id,
            "PASS" if passed else "FAIL",
            target=target,
            evidence={
                "request_scheme": urllib.parse.urlsplit(request_url).scheme,
                "status": record.status,
                "location": resolved,
                "expected": expected,
            },
        )

    def _audit_cache(self, check_id: str, target: str, record: HTTPRecord) -> None:
        present = sorted(name for name in CACHE_HEADER_NAMES if record.headers.get(name))
        directives: list[str] = []
        for value in record.headers.get("cache-control", "").split(","):
            normalized = value.strip().casefold()
            if normalized:
                directives.append(normalized)
        vary_tokens = sorted(
            token.strip().casefold()
            for token in record.headers.get("vary", "").split(",")
            if token.strip()
        )
        self.ledger.add(
            check_id,
            "PASS" if present else "FAIL",
            target=target,
            evidence={
                "cache_signal_headers": present,
                "cache_control_directives": sorted(directives),
                "vary_tokens": vary_tokens,
            },
        )

    def _audit_archive_coverage(
        self, page: ParsedPage | None, record: HTTPRecord | None
    ) -> None:
        check_id = "archive.registry_coverage"
        target = self.canonical_url(self.archive_path)
        if page is None or record is None:
            self.ledger.add(
                check_id,
                "SKIP",
                target=target,
                evidence={"reason": "archive-page-precondition-failed"},
            )
            return
        links = [
            self._normalize_url(urllib.parse.urljoin(record.final_url, href))
            for href in page.parser.anchor_hrefs
        ]
        counts = Counter(links)
        expected = [self._normalize_url(self.canonical_url(work["site_path"])) for work in self.works]
        missing = [url for url in expected if counts[url] == 0]
        self.ledger.add(
            check_id,
            "PASS" if not missing else "FAIL",
            target=target,
            evidence={
                "expected_work_links": len(expected),
                "matched_work_links": len(expected) - len(missing),
                "missing": missing,
            },
        )

    def _audit_unknown_route(self) -> None:
        path = "/.well-known/observer-p1-7-audit-definitely-missing/"
        target = self.canonical_url(path)
        outcome = self.fetcher.get(self.url(path))
        if outcome.record is None:
            status = "SKIP" if outcome.error_code == NETWORK_SKIP_REASON else "FAIL"
            self.ledger.add(
                "routing.unknown_404",
                status,
                target=target,
                evidence={"reason": outcome.error_code},
            )
            return
        record = outcome.record
        final_host = (urllib.parse.urlsplit(record.final_url).hostname or "").casefold()
        self.ledger.add(
            "routing.unknown_404",
            "PASS" if record.status == 404 and final_host == self.expected_host else "FAIL",
            target=target,
            evidence={"status": record.status, "final_host": final_host, **record.body_evidence()},
        )

    def _audit_rest_endpoint(self) -> None:
        path = "/wp-json/wp/v2/research"
        query = "per_page=100&_fields=slug,link,observer_registry_record,observer_badges"
        target = self.canonical_url(path)
        outcome = self.fetcher.get(self.url(path, query=query))
        if outcome.record is None:
            status = "SKIP" if outcome.error_code == NETWORK_SKIP_REASON else "FAIL"
            self.ledger.add(
                "routing.rest_endpoint",
                status,
                target=target,
                evidence={"reason": outcome.error_code},
            )
            return
        record = outcome.record
        parse_ok = False
        payload: Any = None
        try:
            payload = json.loads(record.body.decode("utf-8"))
            parse_ok = isinstance(payload, list)
        except (UnicodeError, json.JSONDecodeError):
            pass
        actual_ids: list[str] = []
        actual_slugs: list[str] = []
        links_ok = False
        if parse_ok:
            actual_ids = sorted(
                str(item.get("observer_registry_record", {}).get("id", ""))
                for item in payload
                if isinstance(item, dict)
                and isinstance(item.get("observer_registry_record"), dict)
            )
            actual_slugs = sorted(
                str(item.get("slug", "")) for item in payload if isinstance(item, dict)
            )
            links_ok = all(
                self._url_has_expected_https_host(str(item.get("link", "")))
                for item in payload
                if isinstance(item, dict)
            ) and len(payload) == len(self.works)
        expected_ids = sorted(str(work["id"]) for work in self.works)
        expected_slugs = sorted(str(work["slug"]) for work in self.works)
        passed = (
            record.status == 200
            and not record.truncated
            and parse_ok
            and actual_ids == expected_ids
            and actual_slugs == expected_slugs
            and links_ok
        )
        self.ledger.add(
            "routing.rest_endpoint",
            "PASS" if passed else "FAIL",
            target=target,
            evidence={
                "status": record.status,
                "json_list": parse_ok,
                "record_count": len(payload) if isinstance(payload, list) else 0,
                "work_ids_match": actual_ids == expected_ids,
                "slugs_match": actual_slugs == expected_slugs,
                "canonical_links_match": links_ok,
                **record.body_evidence(),
            },
        )

    def _audit_robots(self) -> None:
        path = "/robots.txt"
        target = self.canonical_url(path)
        outcome = self.fetcher.get(self.url(path))
        if outcome.record is None:
            status = "SKIP" if outcome.error_code == NETWORK_SKIP_REASON else "FAIL"
            self.ledger.add(
                "routing.robots_txt",
                status,
                target=target,
                evidence={"reason": outcome.error_code},
            )
            self.ledger.add(
                "staging.robots_disallow_all",
                "SKIP",
                target=target,
                evidence={"reason": "robots-fetch-unavailable"},
            )
            return
        record = outcome.record
        content_type = record.headers.get("content-type", "").split(";", 1)[0].casefold()
        routing_ok = record.status == 200 and content_type == "text/plain" and not record.truncated
        self.ledger.add(
            "routing.robots_txt",
            "PASS" if routing_ok else "FAIL",
            target=target,
            evidence={"status": record.status, "content_type": content_type, **record.body_evidence()},
        )
        if not routing_ok:
            self.ledger.add(
                "staging.robots_disallow_all",
                "SKIP",
                target=target,
                evidence={"reason": "robots-route-precondition-failed"},
            )
            return
        text = record.body.decode("utf-8", errors="replace")
        disallow_all = self._robots_disallows_all(text)
        self.ledger.add(
            "staging.robots_disallow_all",
            "PASS" if disallow_all else "FAIL",
            target=target,
            evidence={"wildcard_user_agent_disallow_all": disallow_all},
        )

    def _audit_sitemap(self) -> None:
        path = "/wp-sitemap.xml"
        target = self.canonical_url(path)
        outcome = self.fetcher.get(self.url(path))
        if outcome.record is None:
            status = "SKIP" if outcome.error_code == NETWORK_SKIP_REASON else "FAIL"
            self.ledger.add(
                "routing.sitemap",
                status,
                target=target,
                evidence={"reason": outcome.error_code},
            )
            self.ledger.add(
                "staging.sitemap_disabled",
                status,
                target=target,
                evidence={"reason": outcome.error_code},
            )
            return
        record = outcome.record
        if record.status in {403, 404, 410} and not record.truncated:
            evidence = {"status": record.status, **record.body_evidence()}
            self.ledger.add("routing.sitemap", "PASS", target=target, evidence=evidence)
            self.ledger.add("staging.sitemap_disabled", "PASS", target=target, evidence=evidence)
            return
        parse_ok = False
        locations: list[str] = []
        try:
            root = ET.fromstring(record.body)
            parse_ok = True
            locations = [
                (node.text or "").strip()
                for node in root.iter()
                if node.tag.rsplit("}", 1)[-1] == "loc" and (node.text or "").strip()
            ]
        except ET.ParseError:
            pass
        locations_ok = all(
            self._url_has_expected_https_host(location) for location in locations
        )
        content_type = record.headers.get("content-type", "").split(";", 1)[0].casefold()
        passed = (
            record.status == 200
            and not record.truncated
            and parse_ok
            and locations_ok
            and ("xml" in content_type)
        )
        self.ledger.add(
            "routing.sitemap",
            "PASS" if passed else "FAIL",
            target=target,
            evidence={
                "status": record.status,
                "content_type": content_type,
                "xml_parse": parse_ok,
                "location_count": len(locations),
                "all_locations_https_expected_host": locations_ok,
                **record.body_evidence(),
            },
        )
        self.ledger.add(
            "staging.sitemap_disabled",
            "PASS" if passed and not locations else "FAIL",
            target=target,
            evidence={
                "status": record.status,
                "location_count": len(locations),
                "sitemap_has_no_indexable_locations": passed and not locations,
            },
        )

    def _audit_qmd_boundary(self, page: ParsedPage | None) -> None:
        work = next(work for work in self.works if work["id"] == "QMD-2.0-rc2")
        target = self.canonical_url(work["site_path"])
        if page is None:
            self.ledger.add(
                "boundary.qmd_doi_g2_g6",
                "SKIP",
                target=target,
                evidence={"reason": "qmd-page-precondition-failed"},
            )
            return
        text = page.parser.visible_text.casefold()
        nodes = self._graph_nodes(page.jsonld_documents)
        work_node = self._find_work_node(nodes, target)
        properties = self._additional_properties(work_node)
        doi_links = [
            href
            for href in page.parser.anchor_hrefs
            if (urllib.parse.urlsplit(urllib.parse.urljoin(target, href)).hostname or "").casefold()
            == "doi.org"
        ]
        identifier = work_node.get("identifier") if isinstance(work_node, dict) else None
        same_as = work_node.get("sameAs", []) if isinstance(work_node, dict) else []
        if not isinstance(same_as, list):
            same_as = [same_as]
        jsonld_doi_absent = identifier in {None, ""} and not any(
            str(value).casefold().startswith("https://doi.org/") for value in same_as
        )
        facts = {
            "registry_doi_is_null": work.get("doi") is None,
            "doi_link_count": len(doi_links),
            "jsonld_doi_absent": jsonld_doi_absent,
            "g2_badge_present": "g2 novelty gate open" in text,
            "g6_badge_present": "g6 verification gate open" in text,
            "g2_jsonld_boundary": properties.get("Novelty gate") == "G2-not-passed",
            "g6_jsonld_boundary": properties.get("Independent verification gate") == "G6-not-passed",
        }
        self.ledger.add(
            "boundary.qmd_doi_g2_g6",
            "PASS" if all(value == 0 if key == "doi_link_count" else bool(value) for key, value in facts.items()) else "FAIL",
            target=target,
            evidence=facts,
        )

    def _audit_article_two_boundary(self, page: ParsedPage | None) -> None:
        work = next(work for work in self.works if work["id"] == "WGCX-1.0.0")
        target = self.canonical_url(work["site_path"])
        if page is None:
            self.ledger.add(
                "boundary.article_two_negative_result",
                "SKIP",
                target=target,
                evidence={"reason": "article-two-page-precondition-failed"},
            )
            return
        text = page.parser.visible_text.casefold()
        work_node = self._find_work_node(self._graph_nodes(page.jsonld_documents), target)
        properties = self._additional_properties(work_node)
        facts = {
            "registry_result_class_negative_benchmark": work.get("result_class") == "negative-benchmark",
            "negative_result_badge_present": "negative result" in text,
            "jsonld_result_class_negative_benchmark": properties.get("Result class") == "negative-benchmark",
        }
        self.ledger.add(
            "boundary.article_two_negative_result",
            "PASS" if all(facts.values()) else "FAIL",
            target=target,
            evidence=facts,
        )

    def _audit_article_one_negative_exclusion(self, page: ParsedPage | None) -> None:
        work = next(work for work in self.works if work["id"] == "WGCG-1.0.0")
        target = self.canonical_url(work["site_path"])
        if page is None:
            self.ledger.add(
                "boundary.article_one_not_negative",
                "SKIP",
                target=target,
                evidence={"reason": "article-one-page-precondition-failed"},
            )
            return
        text = page.parser.visible_text.casefold()
        work_node = self._find_work_node(self._graph_nodes(page.jsonld_documents), target)
        properties = self._additional_properties(work_node)
        facts = {
            "registry_result_class_is_not_negative": work.get("result_class") != "negative-benchmark",
            "negative_result_badge_absent": "negative result" not in text,
            "jsonld_result_class_is_not_negative": properties.get("Result class") != "negative-benchmark",
        }
        self.ledger.add(
            "boundary.article_one_not_negative",
            "PASS" if all(facts.values()) else "FAIL",
            target=target,
            evidence=facts,
        )

    @staticmethod
    def _parse_page(record: HTTPRecord) -> ParsedPage:
        parser = _PageParser()
        parser.feed(record.body.decode("utf-8", errors="replace"))
        parser.close()
        documents: list[Any] = []
        errors = 0
        for source in parser.jsonld_scripts:
            try:
                documents.append(json.loads(source))
            except json.JSONDecodeError:
                errors += 1
        ids: list[str] = []
        for document in documents:
            for node in Auditor._definition_nodes(document):
                identifier = node.get("@id")
                if isinstance(identifier, str) and identifier:
                    ids.append(identifier)
        return ParsedPage(parser, documents, errors, ids)

    @staticmethod
    def _definition_nodes(document: Any) -> Iterable[Mapping[str, Any]]:
        if isinstance(document, list):
            for item in document:
                if isinstance(item, dict):
                    yield item
            return
        if not isinstance(document, dict):
            return
        if "@id" in document:
            yield document
        graph = document.get("@graph")
        if isinstance(graph, list):
            for item in graph:
                if isinstance(item, dict):
                    yield item

    @staticmethod
    def _graph_nodes(documents: Sequence[Any]) -> list[Mapping[str, Any]]:
        nodes: list[Mapping[str, Any]] = []
        for document in documents:
            nodes.extend(Auditor._definition_nodes(document))
        return nodes

    @staticmethod
    def _find_work_node(
        nodes: Sequence[Mapping[str, Any]], canonical_url: str
    ) -> Mapping[str, Any]:
        expected = canonical_url + "#work"
        for node in nodes:
            if node.get("@id") == expected:
                return node
        return {}

    @staticmethod
    def _additional_properties(node: Mapping[str, Any]) -> dict[str, str]:
        raw = node.get("additionalProperty", [])
        if isinstance(raw, dict):
            raw = [raw]
        result: dict[str, str] = {}
        if isinstance(raw, list):
            for item in raw:
                if isinstance(item, dict) and isinstance(item.get("name"), str):
                    result[str(item["name"])] = str(item.get("value", ""))
        return result

    @staticmethod
    def _robots_disallows_all(text: str) -> bool:
        active_agents: list[str] = []
        groups: list[tuple[list[str], list[str]]] = []
        directives: list[str] = []
        for raw_line in text.splitlines():
            line = raw_line.split("#", 1)[0].strip()
            if not line or ":" not in line:
                continue
            name, value = (part.strip() for part in line.split(":", 1))
            name = name.casefold()
            if name == "user-agent":
                if directives:
                    groups.append((active_agents, directives))
                    active_agents, directives = [], []
                active_agents.append(value.casefold())
            elif name == "disallow":
                directives.append(value)
        if active_agents or directives:
            groups.append((active_agents, directives))
        return any("*" in agents and "/" in disallows for agents, disallows in groups)

    def _url_has_expected_https_host(self, value: str) -> bool:
        parsed = urllib.parse.urlsplit(value)
        return (
            parsed.scheme.casefold() == "https"
            and (parsed.hostname or "").rstrip(".").casefold() == self.expected_host
            and parsed.username is None
            and parsed.password is None
        )

    @staticmethod
    def _normalize_url(value: str) -> str:
        parsed = urllib.parse.urlsplit(value)
        scheme = parsed.scheme.casefold()
        host = (parsed.hostname or "").rstrip(".").casefold()
        host_part = f"[{host}]" if ":" in host else host
        try:
            port = parsed.port
        except ValueError:
            return "invalid-url"
        if port is not None and not ((scheme == "https" and port == 443) or (scheme == "http" and port == 80)):
            host_part += f":{port}"
        path = parsed.path or "/"
        return urllib.parse.urlunsplit((scheme, host_part, path, parsed.query, parsed.fragment))


def _write_report(report: Mapping[str, Any], output: str) -> None:
    serialized = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if output == "-":
        sys.stdout.write(serialized)
        return
    destination = Path(output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(serialized, encoding="utf-8", newline="\n")


def _configuration_failure_report(
    base_url: str, expected_host: str, allow_network: bool, code: str
) -> dict[str, Any]:
    return {
        "schema": {"name": SCHEMA_NAME, "version": SCHEMA_VERSION},
        "target": {
            "base_url": base_url,
            "expected_host": expected_host,
            "network_allowed": allow_network,
        },
        "registry": {"sha256": None, "source": "bundled-plugin-data/research_index.json"},
        "summary": {"PASS": 0, "FAIL": 1, "SKIP": 0, "total": 1},
        "checks": [
            {
                "id": "config.target",
                "status": "FAIL",
                "target": "audit-configuration",
                "evidence": {"reason": code},
            }
        ],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Anonymous, fail-closed HTTP/SEO audit for P1.7 staging."
    )
    parser.add_argument("--base-url", required=True, help="Staging origin, without a path.")
    parser.add_argument("--expected-host", required=True, help="Exact permitted hostname.")
    parser.add_argument("--output", required=True, help="JSON evidence path, or '-' for stdout.")
    parser.add_argument(
        "--allow-network",
        action="store_true",
        help="Explicitly permit anonymous GET requests. Without this flag every network check is SKIP.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        auditor = Auditor(
            base_url=args.base_url,
            expected_host=args.expected_host,
            allow_network=bool(args.allow_network),
        )
        report = auditor.run()
    except AuditConfigurationError as exc:
        report = _configuration_failure_report(
            args.base_url, args.expected_host, bool(args.allow_network), exc.code
        )
        _write_report(report, args.output)
        return 2
    _write_report(report, args.output)
    return 1 if report["summary"]["FAIL"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
