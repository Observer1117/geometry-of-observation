#!/usr/bin/env python3
"""Static contract tests for the P1.7 WordPress environment probe.

The target probe must run inside a real WordPress/WP-CLI environment. These
tests deliberately need neither PHP nor WordPress: they check the frozen JSON
contract, output allowlist, deterministic encoding/sorting, and advisory-lock
protocol directly from the source.
"""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path
from typing import Any


PROBE = Path(__file__).resolve().parents[1] / "p1-7-environment-probe.php"
SOURCE = PROBE.read_text(encoding="utf-8")


REQUIRED_TOP_LEVEL_KEYS = [
    "schema_version",
    "status",
    "wordpress",
    "runtime",
    "urls",
    "permalinks",
    "https",
    "theme",
    "plugins",
    "mu_plugins",
    "cache",
    "dropins",
    "search",
    "advisory_lock",
    "error_codes",
]


def validate_static_fixture(document: dict[str, Any]) -> None:
    """Validate the public shape without importing a PHP runtime."""

    if list(document) != REQUIRED_TOP_LEVEL_KEYS:
        raise AssertionError("top-level JSON key order changed")
    if document["schema_version"] != "observer-p1.7-environment-probe/v1":
        raise AssertionError("schema version changed")
    if document["status"] not in {"pass", "fail"}:
        raise AssertionError("invalid status")
    if set(document["wordpress"]) != {"version", "multisite", "environment_type"}:
        raise AssertionError("unexpected WordPress fields")
    if set(document["runtime"]) != {"php", "database", "server"}:
        raise AssertionError("unexpected runtime fields")
    if set(document["urls"]) != {"siteurl", "home"}:
        raise AssertionError("unexpected URL fields")
    if set(document["advisory_lock"]) != {"status", "checks", "error_code"}:
        raise AssertionError("unexpected advisory-lock fields")


STATIC_PASS_FIXTURE: dict[str, Any] = {
    "schema_version": "observer-p1.7-environment-probe/v1",
    "status": "pass",
    "wordpress": {"version": "6.8.2", "multisite": False, "environment_type": "staging"},
    "runtime": {
        "php": {"version": "8.3.11", "sapi": "cli"},
        "database": {"engine": "mysql", "version": "8.0.39"},
        "server": {"family": "nginx", "version": "1.27.1"},
    },
    "urls": {"siteurl": "https://staging.example.test", "home": "https://staging.example.test"},
    "permalinks": {"structure": "/%postname%/", "pretty": True},
    "https": {
        "siteurl_uses_https": True,
        "home_uses_https": True,
        "wordpress_uses_https": True,
        "current_request_is_ssl": False,
    },
    "theme": {
        "stylesheet": "twentytwentyfive",
        "stylesheet_version": "1.3",
        "template": "twentytwentyfive",
        "template_version": "1.3",
        "is_child": False,
    },
    "plugins": [{"id": "example/example.php", "version": "1.0.0", "active": True, "network_active": False}],
    "mu_plugins": [],
    "cache": {
        "using_external_object_cache": False,
        "wp_cache_constant": False,
        "object_cache_dropin": False,
        "advanced_cache_dropin": False,
    },
    "dropins": [],
    "search": {"public_indexing_enabled": False},
    "advisory_lock": {
        "status": "pass",
        "checks": {
            "connection_id_available": True,
            "get_lock_acquired": True,
            "is_used_lock_query_succeeded": True,
            "owner_matches_connection": True,
            "connection_id_stable": True,
            "release_lock_succeeded": True,
            "released_state_confirmed": True,
            "cleanup_release_succeeded": True,
        },
        "error_code": None,
    },
    "error_codes": [],
}


class EnvironmentProbeContractTests(unittest.TestCase):
    def test_static_fixture_has_frozen_public_shape(self) -> None:
        validate_static_fixture(STATIC_PASS_FIXTURE)
        encoded_once = json.dumps(STATIC_PASS_FIXTURE, ensure_ascii=False, indent=2, separators=(",", ": "))
        encoded_twice = json.dumps(STATIC_PASS_FIXTURE, ensure_ascii=False, indent=2, separators=(",", ": "))
        self.assertEqual(encoded_once, encoded_twice)

    def test_probe_is_wp_cli_only_and_has_stable_encoding(self) -> None:
        self.assertIn("defined( 'WP_CLI' )", SOURCE)
        self.assertIn("'wp_cli_required'", SOURCE)
        for flag in (
            "JSON_PRETTY_PRINT",
            "JSON_UNESCAPED_SLASHES",
            "JSON_UNESCAPED_UNICODE",
            "JSON_HEX_TAG",
            "JSON_HEX_AMP",
            "JSON_HEX_APOS",
            "JSON_HEX_QUOT",
        ):
            self.assertIn(flag, SOURCE)
        self.assertNotRegex(SOURCE, r"\b(?:gmdate|date|time|microtime)\s*\(")

    def test_environment_contract_collects_every_required_dimension(self) -> None:
        required_tokens = (
            "$wp_version",
            "PHP_VERSION",
            "$wpdb->db_version()",
            "$wpdb->db_server_info()",
            "SERVER_SOFTWARE",
            "get_option( 'siteurl'",
            "get_option( 'home'",
            "get_option( 'permalink_structure'",
            "is_multisite()",
            "wp_get_environment_type()",
            "wp_get_theme()",
            "get_plugins()",
            "get_mu_plugins()",
            "get_dropins()",
            "wp_using_ext_object_cache()",
            "get_option( 'blog_public'",
            "wp_is_using_https",
            "is_ssl()",
        )
        for token in required_tokens:
            self.assertIn(token, SOURCE, token)

    def test_option_reads_are_exactly_allowlisted(self) -> None:
        ordinary = set(re.findall(r"\bget_option\(\s*'([^']+)'", SOURCE))
        network = set(re.findall(r"\bget_site_option\(\s*'([^']+)'", SOURCE))
        self.assertEqual(ordinary, {"active_plugins", "siteurl", "home", "permalink_structure", "blog_public"})
        self.assertEqual(network, {"active_sitewide_plugins"})
        self.assertNotIn("get_options", SOURCE)
        self.assertNotIn("wp_load_alloptions", SOURCE)

    def test_advisory_lock_protocol_is_connection_owned_and_fail_closed(self) -> None:
        for sql_function in ("CONNECTION_ID()", "GET_LOCK(%s, %d)", "IS_USED_LOCK(%s)", "RELEASE_LOCK(%s)"):
            self.assertIn(sql_function, SOURCE)
        self.assertIn("random_bytes( 16 )", SOURCE)
        self.assertIn("(int) $owner === (int) $connection_before", SOURCE)
        self.assertIn("null === $owner_after_release", SOURCE)
        self.assertIn("'advisory_lock_contract_failed'", SOURCE)
        self.assertRegex(SOURCE, r"observer_p17_emit\(\s*\$document,\s*empty\( \$error_codes \) \? 0 : 1")

    def test_ephemeral_lock_material_and_connection_id_are_not_emitted(self) -> None:
        document_block = SOURCE.split("$document = array(", 1)[1].split("observer_p17_emit( $document", 1)[0]
        for private_variable in ("$lock_name", "$connection_before", "$connection_during", "$connection_after", "$owner"):
            self.assertNotIn(private_variable, document_block)
        self.assertNotIn("connection_id' =>", SOURCE)
        self.assertNotIn("lock_name' =>", SOURCE)

    def test_secret_and_identity_surfaces_are_absent(self) -> None:
        forbidden = (
            "DB_HOST",
            "DB_NAME",
            "DB_USER",
            "DB_PASSWORD",
            "AUTH_KEY",
            "SECURE_AUTH_KEY",
            "LOGGED_IN_KEY",
            "NONCE_KEY",
            "AUTH_SALT",
            "wp_get_current_user",
            "get_users(",
            "get_userdata(",
            "phpinfo(",
            "getenv(",
            "$_ENV",
            "var_dump(",
            "print_r(",
        )
        for token in forbidden:
            self.assertNotIn(token, SOURCE, token)

    def test_paths_and_raw_server_metadata_are_reduced_before_output(self) -> None:
        self.assertIn("observer_p17_safe_component_id", SOURCE)
        self.assertIn("observer_p17_server_signature", SOURCE)
        self.assertIn("observer_p17_public_url", SOURCE)
        self.assertIn("false !== strpos( $value, '../' )", SOURCE)
        self.assertIn("User information, query strings, and fragments are intentionally discarded", SOURCE)
        document_block = SOURCE.split("$document = array(", 1)[1].split("observer_p17_emit( $document", 1)[0]
        self.assertNotIn("$server_software,", document_block)
        self.assertNotIn("ABSPATH", document_block)

    def test_component_inventories_and_errors_are_sorted(self) -> None:
        self.assertIn("observer_p17_sort_components( $components )", SOURCE)
        self.assertIn("sort( $error_codes, SORT_STRING )", SOURCE)
        self.assertGreaterEqual(SOURCE.count("observer_p17_sort_components( $components )"), 3)


if __name__ == "__main__":
    unittest.main(verbosity=2)
