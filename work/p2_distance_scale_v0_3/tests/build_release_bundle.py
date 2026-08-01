#!/usr/bin/env python3
"""Build the reproducible GO P2 release bundle and final output artifacts."""

from __future__ import annotations

import hashlib
import shutil
import zipfile
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[3]
P2 = ROOT / "work/p2_distance_scale_v0_3"
OUTPUT_PDF = ROOT / "output/pdf"
OUTPUT_P2 = ROOT / "output/p2"
BUNDLE_DIR = P2 / "bundle"
BUNDLE = BUNDLE_DIR / "GO_P2_Distance_Scale_Mandelbrot_v0_3_Source_Bundle.zip"
COMPONENT_MANIFEST = BUNDLE_DIR / "RELEASE_COMPONENTS_v0_3.yaml"
RELEASE_MANIFEST = P2 / "RELEASE_MANIFEST_v0_3.yaml"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def component_files() -> list[tuple[Path, str]]:
    files: list[tuple[Path, str]] = [
        (
            P2 / "build/distance/distance_scale_interface_observation_maps_v0_2.pdf",
            "pdf/Distance_and_Scale_Interface_under_Observation_Maps_v0_2.pdf",
        ),
        (
            P2 / "build/mandelbrot/mandelbrot_rulers_observation_scale_v1_1.pdf",
            "pdf/Mandelbrot_Rulers_Observation_Scale_Geometry_v1_1.pdf",
        ),
        (
            P2 / "src/distance_scale_interface_observation_maps_v0_2.tex",
            "src/distance_scale_interface_observation_maps_v0_2.tex",
        ),
        (
            P2 / "src/mandelbrot_rulers_observation_scale_v1_1.tex",
            "src/mandelbrot_rulers_observation_scale_v1_1.tex",
        ),
        (
            P2 / "core/distance_scale_contract_v0_3.yaml",
            "core/distance_scale_contract_v0_3.yaml",
        ),
        (
            P2 / "ledgers/distance_scale_mandelbrot_reference_ledgers_v0_3.yaml",
            "ledgers/distance_scale_mandelbrot_reference_ledgers_v0_3.yaml",
        ),
        (
            P2 / "ledgers/corpus_ledgers_v0_3.yaml",
            "ledgers/corpus_ledgers_v0_3.yaml",
        ),
        (
            ROOT / "work/go_core_v0_2/src/go_lint.py",
            "go_core_v0_2/src/go_lint.py",
        ),
        (
            P2 / "tests/test_distance_scale_mandelbrot_v0_3.py",
            "tests/test_distance_scale_mandelbrot_v0_3.py",
        ),
        (
            P2 / "tests/build_corpus_ledger_v0_3.py",
            "tests/build_corpus_ledger_v0_3.py",
        ),
        (
            P2 / "tests/validate_p2_release.py",
            "tests/validate_p2_release.py",
        ),
        (
            P2 / "tests/build_release_bundle.py",
            "tests/build_release_bundle.py",
        ),
        (
            P2 / "reports/P2_Distance_Scale_Mandelbrot_Migration_Report_v0_3_ru.md",
            "reports/P2_Distance_Scale_Mandelbrot_Migration_Report_v0_3_ru.md",
        ),
        (
            P2 / "reports/P2_Validation_Summary_v0_3.json",
            "reports/P2_Validation_Summary_v0_3.json",
        ),
        (
            P2 / "reports/Distance_Scale_Mandelbrot_Lint_Report_v0_3.json",
            "reports/Distance_Scale_Mandelbrot_Lint_Report_v0_3.json",
        ),
        (
            P2 / "reports/Distance_Scale_Mandelbrot_Lint_Report_v0_3_ru.md",
            "reports/Distance_Scale_Mandelbrot_Lint_Report_v0_3_ru.md",
        ),
        (
            P2 / "reports/GO_Corpus_Lint_Report_v0_3.json",
            "reports/GO_Corpus_Lint_Report_v0_3.json",
        ),
        (
            P2 / "reports/GO_Corpus_Lint_Report_v0_3_ru.md",
            "reports/GO_Corpus_Lint_Report_v0_3_ru.md",
        ),
        (
            P2 / "checks/distance/contact.png",
            "checks/distance_contact.png",
        ),
        (
            P2 / "checks/mandelbrot/contact.png",
            "checks/mandelbrot_contact.png",
        ),
        (P2 / "README_P2.md", "README_P2.md"),
    ]
    for path in sorted((ROOT / "work/go_core_v0_2/core").glob("*.yaml")):
        files.append((path, f"go_core_v0_2/core/{path.name}"))
    return files


def main() -> None:
    OUTPUT_PDF.mkdir(parents=True, exist_ok=True)
    OUTPUT_P2.mkdir(parents=True, exist_ok=True)
    BUNDLE_DIR.mkdir(parents=True, exist_ok=True)

    files = component_files()
    for path, _ in files:
        if not path.is_file():
            raise FileNotFoundError(path)

    components = [
        {
            "archive_path": archive_path,
            "source_path": str(path.relative_to(ROOT)),
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
        }
        for path, archive_path in files
    ]
    internal_manifest = {
        "schema": {"id": "go-p2-release-components", "version": "0.3.0"},
        "date": "2026-07-28",
        "components": components,
    }
    with COMPONENT_MANIFEST.open("w", encoding="utf-8") as stream:
        yaml.safe_dump(
            internal_manifest,
            stream,
            sort_keys=False,
            allow_unicode=True,
            width=100,
        )

    with zipfile.ZipFile(BUNDLE, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path, archive_path in files:
            archive.write(path, archive_path)
        archive.write(COMPONENT_MANIFEST, "RELEASE_COMPONENTS_v0_3.yaml")

    bundle_hash = sha256(BUNDLE)
    release = {
        "schema": {"id": "go-p2-release-manifest", "version": "0.3.0"},
        "date": "2026-07-28",
        "status": "PASS",
        "core_contract": "go-core-spec@0.2.0",
        "extension_contract": "go-distance-scale-contract@0.3.0",
        "documents": [
            {
                "id": "distance-scale-interface-v0-2",
                "pages": 9,
                "sha256": sha256(files[0][0]),
            },
            {
                "id": "mandelbrot-rulers-v1-1",
                "pages": 11,
                "sha256": sha256(files[1][0]),
            },
        ],
        "validation": {
            "typed_expressions": 24,
            "reference_findings": 0,
            "regression_tests": 27,
            "rendered_pages": 20,
            "corpus_statuses": {"PASS": 6, "BLOCKED": 2, "FAIL": 9},
        },
        "bundle": {
            "filename": BUNDLE.name,
            "bytes": BUNDLE.stat().st_size,
            "sha256": bundle_hash,
        },
    }
    with RELEASE_MANIFEST.open("w", encoding="utf-8") as stream:
        yaml.safe_dump(
            release,
            stream,
            sort_keys=False,
            allow_unicode=True,
            width=100,
        )

    output_copies = [
        (
            files[0][0],
            OUTPUT_PDF / "Distance_and_Scale_Interface_under_Observation_Maps_v0_2.pdf",
        ),
        (
            files[1][0],
            OUTPUT_PDF / "Mandelbrot_Rulers_Observation_Scale_Geometry_v1_1.pdf",
        ),
        (
            P2 / "core/distance_scale_contract_v0_3.yaml",
            OUTPUT_P2 / "Distance_Scale_Contract_v0_3.yaml",
        ),
        (
            P2 / "ledgers/distance_scale_mandelbrot_reference_ledgers_v0_3.yaml",
            OUTPUT_P2 / "Distance_Scale_Mandelbrot_Reference_Ledgers_v0_3.yaml",
        ),
        (
            P2 / "ledgers/corpus_ledgers_v0_3.yaml",
            OUTPUT_P2 / "GO_Corpus_Ledgers_v0_3.yaml",
        ),
        (
            P2 / "reports/P2_Distance_Scale_Mandelbrot_Migration_Report_v0_3_ru.md",
            OUTPUT_P2 / "P2_Distance_Scale_Mandelbrot_Migration_Report_v0_3_ru.md",
        ),
        (
            P2 / "reports/P2_Validation_Summary_v0_3.json",
            OUTPUT_P2 / "P2_Validation_Summary_v0_3.json",
        ),
        (
            P2 / "reports/GO_Corpus_Lint_Report_v0_3_ru.md",
            OUTPUT_P2 / "GO_Corpus_Lint_Report_v0_3_ru.md",
        ),
        (RELEASE_MANIFEST, OUTPUT_P2 / "RELEASE_MANIFEST_v0_3.yaml"),
        (BUNDLE, OUTPUT_P2 / BUNDLE.name),
    ]
    for source, destination in output_copies:
        shutil.copy2(source, destination)

    print(
        yaml.safe_dump(
            {
                "bundle": str(BUNDLE.relative_to(ROOT)),
                "bundle_sha256": bundle_hash,
                "output_files": [str(path.relative_to(ROOT)) for _, path in output_copies],
            },
            sort_keys=False,
        )
    )


if __name__ == "__main__":
    main()
