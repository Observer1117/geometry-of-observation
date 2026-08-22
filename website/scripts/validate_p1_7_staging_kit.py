#!/usr/bin/env python3
"""Validate P1.7 staging sources and deterministic release bytes."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import subprocess
import tempfile
import zipfile
from pathlib import Path
from types import ModuleType


WEBSITE_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = WEBSITE_ROOT.parent
STAGING_ROOT = WEBSITE_ROOT / "staging"
BUILDER_PATH = WEBSITE_ROOT / "scripts" / "build_p1_7_staging_kit.py"
EXPECTED_PLUGIN_SHA256 = "0d29a680f9aa478d2da3167b64bdbd0570839b2fd7cf9168159e8d4317e3e3d7"
EXPECTED_GATES = {
    "E1", "E2", "E3", "E4", "E5",
    "A1", "A2", "A3",
    "I1", "I2", "I3", "I4", "I5", "I6", "I7", "I8",
    "R1", "R2", "R3", "R4", "R5",
    "T1", "T2", "T3", "T4",
    "C1", "C2", "C3", "C4",
    "S1", "S2", "S3", "S4", "S5",
    "Q1", "Q2", "Q3",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def load_builder() -> ModuleType:
    spec = importlib.util.spec_from_file_location("p1_7_builder", BUILDER_PATH)
    require(spec is not None and spec.loader is not None, "Unable to load P1.7 builder")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


required_files = {
    "README.md",
    "P1.7_EXECUTION_LEDGER_TEMPLATE.md",
    "p1-7-evidence.schema.json",
    "p1-7-environment-probe.php",
    "p1-7-http-audit.py",
    "p1-7-wp-runner.sh",
    "tests/test_environment_probe_contract.py",
    "tests/test_http_audit.py",
    "tests/test_wp_runner_contract.py",
}
actual_files = {
    str(path.relative_to(STAGING_ROOT))
    for path in STAGING_ROOT.rglob("*")
    if path.is_file() and "__pycache__" not in path.parts and path.suffix not in {".pyc", ".pyo"}
}
require(required_files <= actual_files, f"Missing P1.7 files: {sorted(required_files - actual_files)}")

schema = json.loads((STAGING_ROOT / "p1-7-evidence.schema.json").read_text(encoding="utf-8"))
require(schema.get("$schema") == "https://json-schema.org/draft/2020-12/schema", "Evidence schema draft mismatch")
require(schema.get("additionalProperties") is False, "Evidence schema root must fail closed")
require("gates" in schema.get("required", []), "Evidence schema must require the complete gate object")
require("decision" in schema.get("required", []), "Evidence schema must require an explicit decision")
schema_gates = schema.get("$defs", {}).get("gates", {})
require(set(schema_gates.get("required", [])) == EXPECTED_GATES, "Evidence schema gate set differs from the 37-gate matrix")
require(schema_gates.get("additionalProperties") is False, "Evidence gates must fail closed")
decision = schema.get("$defs", {}).get("decision", {})
require("verdict" in decision.get("required", []), "Evidence decision must require an explicit verdict")
require(
    decision.get("properties", {}).get("production_activation_authorized", {}).get("const") is False,
    "P1.7 evidence must never authorize production",
)


def resolve_local_ref(reference: str) -> object:
    require(reference.startswith("#/"), f"Only local evidence-schema references are permitted: {reference}")
    current: object = schema
    for raw_token in reference[2:].split("/"):
        token = raw_token.replace("~1", "/").replace("~0", "~")
        require(isinstance(current, dict) and token in current, f"Unresolved evidence-schema reference: {reference}")
        current = current[token]
    return current


def walk_schema(node: object) -> None:
    if isinstance(node, dict):
        reference = node.get("$ref")
        if isinstance(reference, str):
            resolve_local_ref(reference)
        for value in node.values():
            walk_schema(value)
    elif isinstance(node, list):
        for value in node:
            walk_schema(value)


walk_schema(schema)

readme = (STAGING_ROOT / "README.md").read_text(encoding="utf-8")
ledger = (STAGING_ROOT / "P1.7_EXECUTION_LEDGER_TEMPLATE.md").read_text(encoding="utf-8")
combined_docs = readme + "\n" + ledger
for phrase in (
    "observermultiversesresearch.wordpress.com",
    "theobserverofmultiverses.info",
    EXPECTED_PLUGIN_SHA256,
    "4e7dff23bb53056d559fe44fc43a74c55eb27b10",
    "Gravatar",
    "NO-GO",
):
    require(phrase in combined_docs, f"P1.7 boundary missing from documentation: {phrase}")
for gate in sorted(EXPECTED_GATES):
    require(re.search(rf"\b{re.escape(gate)}\b", combined_docs) is not None, f"Gate {gate} is undocumented")

environment_probe = (STAGING_ROOT / "p1-7-environment-probe.php").read_text(encoding="utf-8")
for contract in (
    "GET_LOCK", "IS_USED_LOCK", "CONNECTION_ID", "RELEASE_LOCK",
    "permalink_structure", "environment_type", "object_cache",
):
    require(contract in environment_probe, f"Environment probe contract missing: {contract}")
for forbidden in ("DB_PASSWORD", "AUTH_KEY", "SECURE_AUTH_KEY", "wp-config.php", "$_COOKIE", "HTTP_AUTHORIZATION"):
    require(forbidden not in environment_probe, f"Environment probe may expose a secret surface: {forbidden}")

http_audit = (STAGING_ROOT / "p1-7-http-audit.py").read_text(encoding="utf-8")
for contract in ("--base-url", "--expected-host", "--allow-network", "--output"):
    require(contract in http_audit, f"HTTP auditor option missing: {contract}")
require("urllib.request" in http_audit, "HTTP auditor must remain standard-library only")
require("Authorization" not in http_audit and "Cookie" not in http_audit, "HTTP auditor must remain unauthenticated")
require("production-target-forbidden" in http_audit, "HTTP auditor lacks the production-host guard")
require("staging.sitemap_disabled" in http_audit, "HTTP auditor does not enforce staging sitemap suppression")
require("social_metadata" in http_audit, "HTTP auditor does not check title/description/social metadata coherence")

wp_runner = (STAGING_ROOT / "p1-7-wp-runner.sh").read_text(encoding="utf-8")
require("--execute" in wp_runner, "WordPress runner must require an explicit mutation flag")
require("WP_ENVIRONMENT_TYPE is not staging" in wp_runner, "WordPress runner lacks its staging-only guard")
require("Refusing to target the production/Gravatar domain" in wp_runner, "WordPress runner lacks the production guard")
require(".wpcomstaging.com" in wp_runner, "WordPress runner is not bound to native WordPress.com staging")
require("restore_proof_id" in wp_runner and "access_proof_id" in wp_runner, "WordPress runner lacks restore/access proof guards")
require('assert_sync_counts "$evidence_dir/registry-sync-first.log" 5 0 0' in wp_runner, "First import counts are not asserted")
require('assert_sync_counts "$evidence_dir/registry-sync-second.log" 0 0 5' in wp_runner, "Second import counts are not asserted")
require(wp_runner.index("blog_public") < wp_runner.index('wp plugin install "$plugin_zip"'), "Visibility guard must precede plugin installation")
subprocess.run(["bash", "-n", str(STAGING_ROOT / "p1-7-wp-runner.sh")], check=True)
compile(http_audit, str(STAGING_ROOT / "p1-7-http-audit.py"), "exec")

builder = load_builder()
with tempfile.TemporaryDirectory(prefix="observer-p1-7-validate-") as temporary:
    first = Path(temporary) / "first.zip"
    second = Path(temporary) / "second.zip"
    first_digest = builder.build(first)
    second_digest = builder.build(second)
    require(first_digest == second_digest, "P1.7 builder is not deterministic")
    require(first.read_bytes() == second.read_bytes(), "P1.7 ZIP bytes differ across consecutive builds")

    with zipfile.ZipFile(first) as archive:
        members = archive.namelist()
        require(len(members) == len(set(members)), "P1.7 ZIP contains duplicate members")
        require(all(not name.startswith("/") and ".." not in Path(name).parts for name in members), "Unsafe ZIP path")
        root = f"p1-7-staging-kit-{builder.KIT_VERSION}/"
        manifest = json.loads(archive.read(root + "MANIFEST.json"))
        require(
            manifest["authority"]["plugin_sha256"] == EXPECTED_PLUGIN_SHA256,
            "Manifest does not bind the verified P1.6 ZIP",
        )
        require(
            manifest["deployment_boundary"]["public_domain_must_remain_gravatar_until_p1_7_go"] is True,
            "Manifest weakens the Gravatar/domain boundary",
        )
        require(
            manifest["deployment_boundary"]["production_activation_authorized"] is False,
            "Manifest must not authorize production",
        )
        for name, metadata in manifest["files"].items():
            payload = archive.read(root + name)
            require(len(payload) == metadata["size"], f"Size mismatch for {name}")
            require(sha256(payload) == metadata["sha256"], f"Hash mismatch for {name}")
        require(
            sha256(archive.read(root + builder.PLUGIN_ARCHIVE_NAME)) == EXPECTED_PLUGIN_SHA256,
            "Bundled plugin bytes differ from P1.6 release candidate",
        )

print("P1.7 staging kit contract verified.")
