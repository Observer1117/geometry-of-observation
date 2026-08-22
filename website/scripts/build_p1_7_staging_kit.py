#!/usr/bin/env python3
"""Build the deterministic P1.7 target-staging operations bundle."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import stat
import tempfile
import zipfile
from pathlib import Path
from types import ModuleType


WEBSITE_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = WEBSITE_ROOT.parent
STAGING_ROOT = WEBSITE_ROOT / "staging"
REGISTRY_ROOT = WEBSITE_ROOT / "registry"
PLUGIN_BUILDER = WEBSITE_ROOT / "scripts" / "build_wordpress_plugin.py"

KIT_VERSION = "0.1.0"
ARCHIVE_ROOT = f"p1-7-staging-kit-{KIT_VERSION}"
PLUGIN_ARCHIVE_NAME = "observer-research-registry-0.1.0.zip"
EXPECTED_PLUGIN_SHA256 = "0d29a680f9aa478d2da3167b64bdbd0570839b2fd7cf9168159e8d4317e3e3d7"
P1_6_HEAD_COMMIT = "4e7dff23bb53056d559fe44fc43a74c55eb27b10"
P1_5_REGISTRY_COMMIT = "bab4480e50f8abe32087da765a145575a4519f8a"


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def load_plugin_builder() -> ModuleType:
    spec = importlib.util.spec_from_file_location("observer_plugin_builder", PLUGIN_BUILDER)
    if spec is None or spec.loader is None:
        raise SystemExit(f"Unable to load plugin builder: {PLUGIN_BUILDER}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def staging_files() -> dict[str, bytes]:
    if not STAGING_ROOT.is_dir():
        raise SystemExit(f"Staging source not found: {STAGING_ROOT}")

    payloads: dict[str, bytes] = {}
    for path in sorted(STAGING_ROOT.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(STAGING_ROOT)
        if "__pycache__" in relative.parts or path.suffix in {".pyc", ".pyo"}:
            continue
        if path.is_symlink():
            raise SystemExit(f"Symlinks are forbidden in the staging kit: {path}")
        if path.stat().st_size > 2 * 1024 * 1024:
            raise SystemExit(f"Unexpected oversized staging-kit file: {path}")
        payloads[f"staging/{relative.as_posix()}"] = path.read_bytes()

    for name in ("research_index.json", "wordpress_data_model.json"):
        path = REGISTRY_ROOT / name
        payloads[f"registry/{name}"] = path.read_bytes()

    return payloads


def write_member(archive: zipfile.ZipFile, name: str, payload: bytes) -> None:
    info = zipfile.ZipInfo(f"{ARCHIVE_ROOT}/{name}", date_time=(1980, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.create_system = 3
    info.external_attr = (stat.S_IFREG | 0o644) << 16
    archive.writestr(info, payload, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)


def build(output: Path) -> str:
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="observer-p1-7-") as temporary:
        plugin_path = Path(temporary) / PLUGIN_ARCHIVE_NAME
        plugin_digest = load_plugin_builder().build(plugin_path)
        if plugin_digest != EXPECTED_PLUGIN_SHA256:
            raise SystemExit(
                "P1.6 plugin bytes drifted: "
                f"expected {EXPECTED_PLUGIN_SHA256}, obtained {plugin_digest}"
            )

        payloads = staging_files()
        payloads[PLUGIN_ARCHIVE_NAME] = plugin_path.read_bytes()

    manifest = {
        "schema": "observer-p1-7-staging-kit-manifest/1.0.0",
        "kit_version": KIT_VERSION,
        "authority": {
            "repository": "Observer1117/geometry-of-observation",
            "p1_6_head_commit": P1_6_HEAD_COMMIT,
            "p1_5_registry_commit": P1_5_REGISTRY_COMMIT,
            "plugin_sha256": EXPECTED_PLUGIN_SHA256,
        },
        "deployment_boundary": {
            "selected_hosting": "WordPress.com Business",
            "temporary_site": "observermultiversesresearch.wordpress.com",
            "public_domain": "theobserverofmultiverses.info",
            "public_domain_must_remain_gravatar_until_p1_7_go": True,
            "production_activation_authorized": False,
        },
        "files": {
            name: {"sha256": sha256_bytes(payload), "size": len(payload)}
            for name, payload in sorted(payloads.items())
        },
    }
    manifest_bytes = (json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    payloads["MANIFEST.json"] = manifest_bytes

    sums = "".join(f"{sha256_bytes(payload)}  {name}\n" for name, payload in sorted(payloads.items()))
    payloads["SHA256SUMS.txt"] = sums.encode("utf-8")

    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, payload in sorted(payloads.items()):
            write_member(archive, name, payload)

    return sha256_bytes(output.read_bytes())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "output",
        nargs="?",
        type=Path,
        default=WEBSITE_ROOT / "dist" / f"p1-7-staging-kit-{KIT_VERSION}.zip",
    )
    args = parser.parse_args()
    digest = build(args.output)
    print(f"{digest}  {args.output.resolve()}")


if __name__ == "__main__":
    main()
