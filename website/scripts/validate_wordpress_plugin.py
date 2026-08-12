#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "wordpress-plugin" / "observer-research-registry"
REGISTRY = ROOT / "registry"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


required_files = {
    "observer-research-registry.php",
    "README.md",
    "readme.txt",
    "LICENSE.md",
    "uninstall.php",
    "data/manifest.json",
    "data/research_index.json",
    "data/wordpress_data_model.json",
    "src/class-registry.php",
    "src/class-meta-schema.php",
    "src/class-importer.php",
    "src/class-rest-fields.php",
    "src/class-json-ld.php",
    "src/class-renderer.php",
    "src/class-admin.php",
    "templates/archive-research_output.php",
    "templates/single-research_output.php",
    "assets/registry.css",
    "tests/run.php",
    "P1.6_IMPLEMENTATION_AUDIT.md",
}
actual_files = {str(path.relative_to(PLUGIN)) for path in PLUGIN.rglob("*") if path.is_file()}
require(required_files <= actual_files, f"Missing plugin files: {sorted(required_files - actual_files)}")

for name in ("research_index.json", "wordpress_data_model.json"):
    canonical = REGISTRY / name
    bundled = PLUGIN / "data" / name
    require(canonical.read_bytes() == bundled.read_bytes(), f"Bundled {name} is not byte-identical to canonical registry")

manifest = json.loads((PLUGIN / "data" / "manifest.json").read_text(encoding="utf-8"))
require(manifest["plugin_version"] == "0.1.0", "Manifest plugin version mismatch")
require(manifest["source_repository"] == "Observer1117/geometry-of-observation", "Manifest source repository mismatch")
require(manifest["source_commit"] == "bab4480e50f8abe32087da765a145575a4519f8a", "Manifest source commit mismatch")
for name in ("research_index.json", "wordpress_data_model.json"):
    require(manifest["files"][name]["sha256"] == sha256(PLUGIN / "data" / name), f"Manifest hash mismatch for {name}")

index = json.loads((REGISTRY / "research_index.json").read_text(encoding="utf-8"))
model = json.loads((REGISTRY / "wordpress_data_model.json").read_text(encoding="utf-8"))
require(len(index["works"]) == 5, "P1.6 must remain pinned to five works")
expected_meta = {field["key"] for field in model["machine_meta"]}
require(len(expected_meta) == 22, "P1.5 model must expose exactly 22 machine-meta fields")

registry_php = (PLUGIN / "src" / "class-registry.php").read_text(encoding="utf-8")
mapping_block = registry_php.split("public static function meta_for_work", 1)[1].split("public static function canonical_url", 1)[0]
mapped_meta = set(re.findall(r"'(observer_[a-z0-9_]+)'\s*=>", mapping_block))
require(mapped_meta == expected_meta, f"PHP meta projection differs from P1.5 model: {sorted(mapped_meta ^ expected_meta)}")

plugin_php = "\n".join(path.read_text(encoding="utf-8") for path in PLUGIN.rglob("*.php"))
for forbidden in ("wp_remote_get(", "wp_safe_remote_get(", "curl_exec(", "register_rest_route("):
    require(forbidden not in plugin_php, f"P1.6 must not introduce remote/import endpoint surface: {forbidden}")

plugin_main = (PLUGIN / "observer-research-registry.php").read_text(encoding="utf-8")
require("Version: 0.1.0" in plugin_main, "Plugin header version mismatch")
require("Requires PHP: 7.4" in plugin_main, "Declared PHP baseline is missing")

plugin_wiring = (PLUGIN / "src" / "class-plugin.php").read_text(encoding="utf-8")
require("admin_post_observer_registry_sync" in plugin_wiring, "Explicit admin POST synchronization is not wired")
require("rest_pre_insert_" in plugin_wiring, "REST write rejection is not wired")
require("update_post_metadata_by_mid" in plugin_wiring, "Metadata updates by meta ID are not guarded")
require("delete_post_metadata_by_mid" in plugin_wiring, "Metadata deletions by meta ID are not guarded")
require("Importer::sync" not in plugin_wiring, "Synchronization must not run automatically during bootstrap")

importer = (PLUGIN / "src" / "class-importer.php").read_text(encoding="utf-8")
for contract in (
    "'post_status'    => 'draft'",
    "add_option( self::LOCK_OPTION",
    "add_option( self::JOURNAL_OPTION",
    "Canonical slug collision",
    "Automatic rollback",
    "observer_work_id",
):
    require(contract in importer, f"Importer safety contract missing: {contract}")

renderer = (PLUGIN / "src" / "class-renderer.php").read_text(encoding="utf-8")
for flag in ("JSON_HEX_TAG", "JSON_HEX_AMP", "JSON_HEX_APOS", "JSON_HEX_QUOT"):
    require(flag in renderer, f"Safe JSON-LD flag missing: {flag}")

uninstall = (PLUGIN / "uninstall.php").read_text(encoding="utf-8")
require("wp_delete_post" not in uninstall and "delete_post_meta" not in uninstall, "Uninstall must preserve research posts and metadata")

workflow = ROOT.parent / ".github" / "workflows" / "wordpress-plugin-contract.yml"
require(workflow.is_file(), "WordPress plugin CI workflow is missing")
builder = ROOT / "scripts" / "build_wordpress_plugin.py"
require(builder.is_file(), "Deterministic plugin ZIP builder is missing")
workflow_text = workflow.read_text(encoding="utf-8")
require(
    workflow_text.count("- 'website/scripts/build_wordpress_plugin.py'") == 2,
    "Plugin ZIP builder must trigger both pull-request and main-branch contract checks",
)

print("Observer Research Registry static contract verified.")
