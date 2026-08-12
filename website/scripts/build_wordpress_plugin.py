#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import stat
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "wordpress-plugin" / "observer-research-registry"
ARCHIVE_ROOT = PLUGIN.name


def build(output: Path) -> str:
    if not PLUGIN.is_dir():
        raise SystemExit(f"Plugin source not found: {PLUGIN}")

    files = sorted(path for path in PLUGIN.rglob("*") if path.is_file())
    if not files:
        raise SystemExit("Plugin source contains no files")

    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in files:
            if path.is_symlink():
                raise SystemExit(f"Symlinks are forbidden in the plugin archive: {path}")
            if path.stat().st_size > 2 * 1024 * 1024:
                raise SystemExit(f"Unexpected oversized plugin file: {path}")

            relative = path.relative_to(PLUGIN)
            member = f"{ARCHIVE_ROOT}/{relative.as_posix()}"
            info = zipfile.ZipInfo(member, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            archive.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)

    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    return digest


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a deterministic Observer Research Registry WordPress ZIP")
    parser.add_argument(
        "output",
        nargs="?",
        type=Path,
        default=ROOT / "dist" / "observer-research-registry-0.1.0.zip",
    )
    args = parser.parse_args()
    output = args.output.resolve()
    digest = build(output)
    print(f"{digest}  {output}")


if __name__ == "__main__":
    main()

