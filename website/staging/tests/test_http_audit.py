from __future__ import annotations

import importlib.util
import html
import json
import sys
import tempfile
import threading
import unittest
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "p1-7-http-audit.py"
SPEC = importlib.util.spec_from_file_location("p1_7_http_audit", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
AUDIT = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = AUDIT
SPEC.loader.exec_module(AUDIT)


class _FixtureHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, format: str, *args: object) -> None:
        return

    def do_GET(self) -> None:
        server = self.server
        server.requests.append(self.path)  # type: ignore[attr-defined]
        for header in ("Authorization", "Proxy-Authorization", "Cookie"):
            if self.headers.get(header):
                server.forbidden_headers.append(header)  # type: ignore[attr-defined]

        parsed = urllib.parse.urlsplit(self.path)
        path = parsed.path
        routes = server.routes  # type: ignore[attr-defined]
        if path in {route.rstrip("/") for route in routes}:
            self._send_redirect(server.https_origin + path + "/")  # type: ignore[attr-defined]
            return
        if path == "/.well-known/observer-p1-7-audit-definitely-missing/":
            self._send(404, "text/plain; charset=utf-8", b"SECRET-BODY-MARKER missing")
            return
        if path == "/wp-json/wp/v2/research":
            payload = []
            for work in server.works:  # type: ignore[attr-defined]
                payload.append(
                    {
                        "slug": work["slug"],
                        "link": server.https_origin + work["site_path"],  # type: ignore[attr-defined]
                        "observer_registry_record": {"id": work["id"]},
                        "observer_badges": [],
                    }
                )
            self._send_json(payload)
            return
        if path == "/robots.txt":
            self._send(
                200,
                "text/plain; charset=utf-8",
                b"User-agent: *\nDisallow: /\n",
            )
            return
        if path == "/wp-sitemap.xml":
            self._send(404, "text/plain; charset=utf-8", b"sitemap disabled on staging")
            return
        if path in routes:
            self._send_page(path)
            return
        self._send(404, "text/plain; charset=utf-8", b"not found")

    def _send_page(self, path: str) -> None:
        server = self.server
        canonical = server.https_origin + path  # type: ignore[attr-defined]
        if path == "/research/":
            metadata_text = "Research Index"
            graph = {
                "@context": "https://schema.org",
                "@graph": [
                    {"@id": canonical + "#page", "@type": "CollectionPage"},
                    {"@id": canonical + "#index", "@type": "ItemList"},
                ],
            }
            links = "".join(
                f'<a href="{server.https_origin}{work["site_path"]}">{work["short_title"]}</a>'  # type: ignore[attr-defined]
                for work in server.works  # type: ignore[attr-defined]
            )
            visible = "Research Index " + links
        else:
            work = next(item for item in server.works if item["site_path"] == path)  # type: ignore[attr-defined]
            metadata_text = str(work["title"])
            properties = [
                {"@type": "PropertyValue", "name": "Release status", "value": work["release_status"]},
                {"@type": "PropertyValue", "name": "Review status", "value": work["review_status"]},
            ]
            visible = work["title"]
            if work["id"] == "QMD-2.0-rc2":
                visible += " G2 novelty gate open G6 verification gate open"
                properties.extend(
                    [
                        {"@type": "PropertyValue", "name": "Novelty gate", "value": "G2-not-passed"},
                        {
                            "@type": "PropertyValue",
                            "name": "Independent verification gate",
                            "value": "G6-not-passed",
                        },
                    ]
                )
            if work["id"] == "WGCX-1.0.0":
                visible += " Negative result"
                properties.append(
                    {"@type": "PropertyValue", "name": "Result class", "value": "negative-benchmark"}
                )
            graph = {
                "@context": "https://schema.org",
                "@graph": [
                    {"@id": canonical + "#work", "@type": work["jsonld_profile"]["primary_type"], "additionalProperty": properties},
                    {"@id": canonical + "#page", "@type": "WebPage"},
                ],
            }
        body = (
            "<!doctype html><html><head>"
            f"<title>{html.escape(metadata_text)}</title>"
            f'<meta name="description" content="{html.escape(metadata_text, quote=True)}">'
            f'<meta property="og:title" content="{html.escape(metadata_text, quote=True)}">'
            f'<meta property="og:description" content="{html.escape(metadata_text, quote=True)}">'
            f'<meta property="og:url" content="{canonical}">'
            '<meta name="twitter:card" content="summary">'
            f'<meta name="twitter:title" content="{html.escape(metadata_text, quote=True)}">'
            f'<meta name="twitter:description" content="{html.escape(metadata_text, quote=True)}">'
            f'<link rel="canonical" href="{canonical}">'
            '<meta name="robots" content="noindex,nofollow">'
            f'<script type="application/ld+json">{json.dumps(graph, sort_keys=True)}</script>'
            "</head><body>SECRET-BODY-MARKER "
            f"{visible}</body></html>"
        ).encode("utf-8")
        self._send(200, "text/html; charset=utf-8", body)

    def _send_redirect(self, location: str) -> None:
        self.send_response(308)
        self.send_header("Location", location)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _send_json(self, payload: object) -> None:
        self._send(
            200,
            "application/json; charset=utf-8",
            json.dumps(payload, sort_keys=True).encode("utf-8"),
        )

    def _send(self, status: int, content_type: str, body: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "public, max-age=60")
        self.send_header("X-Robots-Tag", "noindex, nofollow")
        self.end_headers()
        self.wfile.write(body)


class HTTPAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        registry_path = (
            SCRIPT.parents[1]
            / "wordpress-plugin"
            / "observer-research-registry"
            / "data"
            / "research_index.json"
        )
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), _FixtureHandler)
        port = cls.server.server_address[1]
        cls.server.works = registry["works"]
        cls.server.routes = {registry["index_page"]["site_path"], *(work["site_path"] for work in registry["works"])}
        cls.server.https_origin = f"https://127.0.0.1:{port}"
        cls.server.requests = []
        cls.server.forbidden_headers = []
        cls.base_url = f"http://127.0.0.1:{port}"
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)

    def setUp(self) -> None:
        self.server.requests.clear()
        self.server.forbidden_headers.clear()

    def test_default_mode_is_offline_and_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            first = Path(temporary) / "first.json"
            second = Path(temporary) / "second.json"
            before = len(self.server.requests)
            exit_one = AUDIT.main(
                [
                    "--base-url",
                    self.base_url,
                    "--expected-host",
                    "127.0.0.1",
                    "--output",
                    str(first),
                ]
            )
            exit_two = AUDIT.main(
                [
                    "--base-url",
                    self.base_url,
                    "--expected-host",
                    "127.0.0.1",
                    "--output",
                    str(second),
                ]
            )
            self.assertEqual(0, exit_one)
            self.assertEqual(0, exit_two)
            self.assertEqual(before, len(self.server.requests))
            self.assertEqual(first.read_bytes(), second.read_bytes())
            report = json.loads(first.read_text(encoding="utf-8"))
            self.assertFalse(report["target"]["network_allowed"])
            self.assertEqual(0, report["summary"]["FAIL"])
            self.assertGreater(report["summary"]["SKIP"], 0)

    def test_local_fixture_covers_routes_seo_boundaries_and_safety(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "online.json"
            exit_code = AUDIT.main(
                [
                    "--base-url",
                    self.base_url,
                    "--expected-host",
                    "127.0.0.1",
                    "--output",
                    str(output),
                    "--allow-network",
                ]
            )
            # The fixture intentionally speaks plaintext.  The auditor must
            # therefore fail the final-HTTPS and HTTP-upgrade checks while all
            # content/routing contracts remain independently testable.
            self.assertEqual(1, exit_code)
            report = json.loads(output.read_text(encoding="utf-8"))
            checks = {check["id"]: check for check in report["checks"]}
            for route in (
                "archive",
                "geometry-of-observation",
                "compact-resolvent-spectral-encodings",
                "weighted-gray-codon-geometry",
                "weighted-gray-codon-external-validation",
                "quantitative-modularity-defects",
            ):
                self.assertEqual("PASS", checks[f"route.{route}.http_status"]["status"])
                self.assertEqual("PASS", checks[f"route.{route}.canonical_tag"]["status"])
                self.assertEqual("PASS", checks[f"route.{route}.social_metadata"]["status"])
                self.assertEqual("PASS", checks[f"route.{route}.jsonld_parse"]["status"])
                self.assertEqual("PASS", checks[f"route.{route}.jsonld_id_uniqueness"]["status"])
                self.assertEqual("PASS", checks[f"route.{route}.trailing_slash_redirect"]["status"])
                self.assertEqual("PASS", checks[f"route.{route}.stage_noindex"]["status"])
                self.assertEqual("PASS", checks[f"route.{route}.cache_headers"]["status"])
                self.assertEqual("FAIL", checks[f"route.{route}.canonical_https"]["status"])
                self.assertEqual("FAIL", checks[f"route.{route}.http_to_https_redirect"]["status"])

            for check_id in (
                "archive.registry_coverage",
                "routing.unknown_404",
                "routing.rest_endpoint",
                "routing.robots_txt",
                "routing.sitemap",
                "staging.sitemap_disabled",
                "staging.robots_disallow_all",
                "boundary.qmd_doi_g2_g6",
                "boundary.article_two_negative_result",
                "boundary.article_one_not_negative",
            ):
                self.assertEqual("PASS", checks[check_id]["status"], check_id)

            self.assertEqual([], self.server.forbidden_headers)
            serialized = output.read_text(encoding="utf-8")
            self.assertNotIn("SECRET-BODY-MARKER", serialized)
            self.assertNotIn("Authorization", serialized)

    def test_credentials_in_base_url_are_rejected_without_request(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "failure.json"
            before = len(self.server.requests)
            exit_code = AUDIT.main(
                [
                    "--base-url",
                    self.base_url.replace("http://", "http://user:secret@"),
                    "--expected-host",
                    "127.0.0.1",
                    "--output",
                    str(output),
                    "--allow-network",
                ]
            )
            self.assertEqual(2, exit_code)
            self.assertEqual(before, len(self.server.requests))
            report = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual("base-url-credentials-forbidden", report["checks"][0]["evidence"]["reason"])

    def test_production_and_non_native_targets_are_rejected_without_request(self) -> None:
        for host, expected_reason in (
            ("theobserverofmultiverses.info", "production-target-forbidden"),
            ("www.theobserverofmultiverses.info", "production-target-forbidden"),
            ("observermultiversesresearch.wpcomstaging.com", "expected-host-not-native-wordpress-staging"),
        ):
            with self.subTest(host=host), tempfile.TemporaryDirectory() as temporary:
                output = Path(temporary) / "failure.json"
                before = len(self.server.requests)
                exit_code = AUDIT.main(
                    [
                        "--base-url",
                        f"https://{host}",
                        "--expected-host",
                        host,
                        "--output",
                        str(output),
                    ]
                )
                self.assertEqual(2, exit_code)
                self.assertEqual(before, len(self.server.requests))
                report = json.loads(output.read_text(encoding="utf-8"))
                self.assertEqual(expected_reason, report["checks"][0]["evidence"]["reason"])


if __name__ == "__main__":
    unittest.main()
