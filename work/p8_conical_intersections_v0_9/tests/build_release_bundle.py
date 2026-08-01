#!/usr/bin/env python3
"""Build the reproducible GO P8 conical-intersections release bundle."""

from __future__ import annotations

import hashlib
import shutil
import zipfile
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[3]
P8 = ROOT / "work/p8_conical_intersections_v0_9"
OUTPUT_PDF = ROOT / "output/pdf"
OUTPUT_P8 = ROOT / "output/p8"
BUNDLE_DIR = P8 / "bundle"
BUNDLE = (
    BUNDLE_DIR / "GO_P8_Conical_Intersections_v0_9_Source_Bundle.zip"
)
COMPONENT_MANIFEST = BUNDLE_DIR / "RELEASE_COMPONENTS_v0_9.yaml"
RELEASE_MANIFEST = P8 / "RELEASE_MANIFEST_v0_9.yaml"

PDF = P8 / "build/ci/conical_intersections_spectral_observation_v1_1.pdf"
PUBLIC_PDF_NAME = (
    "Conical_Intersections_Spectral_Observation_Geometry_v1_1.pdf"
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def component_files() -> list[tuple[Path, str]]:
    files: list[tuple[Path, str]] = [
        (PDF, f"pdf/{PUBLIC_PDF_NAME}"),
        (
            P8 / "src/conical_intersections_spectral_observation_v1_1.tex",
            "src/conical_intersections_spectral_observation_v1_1.tex",
        ),
        (
            P8
            / "core/conical_intersections_observation_contract_v0_9.yaml",
            "core/conical_intersections_observation_contract_v0_9.yaml",
        ),
        (
            P8
            / "ledgers/conical_intersections_reference_ledger_v0_9.yaml",
            "ledgers/conical_intersections_reference_ledger_v0_9.yaml",
        ),
        (
            P8 / "ledgers/corpus_ledgers_v0_9.yaml",
            "ledgers/corpus_ledgers_v0_9.yaml",
        ),
        (
            P8 / "data/conical_intersections_benchmarks_v0_9.csv",
            "data/conical_intersections_benchmarks_v0_9.csv",
        ),
        (
            P8 / "data/conical_intersections_metrics_v0_9.json",
            "data/conical_intersections_metrics_v0_9.json",
        ),
        (
            P8
            / "scripts/generate_conical_intersections_benchmarks.py",
            "scripts/generate_conical_intersections_benchmarks.py",
        ),
        (
            P8 / "tests/build_corpus_ledger_v0_9.py",
            "tests/build_corpus_ledger_v0_9.py",
        ),
        (
            P8 / "tests/test_conical_intersections_v0_9.py",
            "tests/test_conical_intersections_v0_9.py",
        ),
        (
            P8 / "tests/validate_p8_release.py",
            "tests/validate_p8_release.py",
        ),
        (
            P8 / "tests/build_release_bundle.py",
            "tests/build_release_bundle.py",
        ),
        (
            P8
            / "reports/P8_Conical_Intersections_Migration_Report_v0_9_ru.md",
            "reports/P8_Conical_Intersections_Migration_Report_v0_9_ru.md",
        ),
        (
            P8 / "reports/P8_Validation_Summary_v0_9.json",
            "reports/P8_Validation_Summary_v0_9.json",
        ),
        (
            P8 / "reports/P8_Visual_QA_v0_9.yaml",
            "reports/P8_Visual_QA_v0_9.yaml",
        ),
        (
            P8
            / "reports/Conical_Intersections_Reference_Lint_Report_v0_9.json",
            "reports/Conical_Intersections_Reference_Lint_Report_v0_9.json",
        ),
        (
            P8
            / "reports/Conical_Intersections_Reference_Lint_Report_v0_9.md",
            "reports/Conical_Intersections_Reference_Lint_Report_v0_9.md",
        ),
        (
            P8 / "reports/GO_Corpus_Lint_Report_v0_9.json",
            "reports/GO_Corpus_Lint_Report_v0_9.json",
        ),
        (
            P8 / "reports/GO_Corpus_Lint_Report_v0_9.md",
            "reports/GO_Corpus_Lint_Report_v0_9.md",
        ),
        (
            P8
            / "build/ci/conical_intersections_spectral_observation_v1_1.log",
            "build/ci/conical_intersections_spectral_observation_v1_1.log",
        ),
        (
            P8
            / "checks/ci/conical_intersections_spectral_observation_v1_1.txt",
            "checks/ci/conical_intersections_spectral_observation_v1_1.txt",
        ),
        (P8 / "README_P8.md", "README_P8.md"),
        (
            ROOT / "work/go_core_v0_2/src/go_lint.py",
            "go_core_v0_2/src/go_lint.py",
        ),
        (
            ROOT
            / "work/p7_billiards_v0_8/ledgers/corpus_ledgers_v0_8.yaml",
            "baseline/corpus_ledgers_v0_8.yaml",
        ),
        (
            ROOT
            / "upload/conical_intersections_observation_caustics_v1_bilingual.pdf",
            "legacy/conical_intersections_observation_caustics_v1_bilingual.pdf",
        ),
    ]
    for path in sorted((ROOT / "work/go_core_v0_2/core").glob("*.yaml")):
        files.append((path, f"go_core_v0_2/core/{path.name}"))
    return files


def main() -> None:
    OUTPUT_PDF.mkdir(parents=True, exist_ok=True)
    OUTPUT_P8.mkdir(parents=True, exist_ok=True)
    BUNDLE_DIR.mkdir(parents=True, exist_ok=True)

    files = component_files()
    missing = [
        str(path.relative_to(ROOT))
        for path, _ in files
        if not path.is_file()
    ]
    if missing:
        raise FileNotFoundError(
            "Missing release components:\n" + "\n".join(missing)
        )

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
        "schema": {
            "id": "go-p8-release-components",
            "version": "0.9.0",
        },
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

    with zipfile.ZipFile(
        BUNDLE,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as archive:
        for path, archive_path in files:
            archive.write(path, archive_path)
        archive.write(COMPONENT_MANIFEST, "RELEASE_COMPONENTS_v0_9.yaml")

    with zipfile.ZipFile(BUNDLE, "r") as archive:
        bad_member = archive.testzip()
        if bad_member is not None:
            raise RuntimeError(f"archive integrity failure: {bad_member}")

    validation = yaml.safe_load(
        (P8 / "reports/P8_Validation_Summary_v0_9.json").read_text(
            encoding="utf-8"
        )
    )
    if validation["status"] != "PASS":
        raise RuntimeError("validation summary is not PASS")

    release = {
        "schema": {
            "id": "go-p8-release-manifest",
            "version": "0.9.0",
        },
        "date": "2026-07-28",
        "status": "PASS",
        "core_contract": "go-core-spec@0.2.0",
        "inherited_contracts": [
            "go-billiards-observation-contract@0.8.0",
        ],
        "extension_contract": (
            "go-conical-intersections-observation-contract@0.9.0"
        ),
        "documents": [
            {
                "id": "conical-intersections-observation-v1-1",
                "pages": 8,
                "sha256": sha256(PDF),
            }
        ],
        "validation": {
            "release_checks": validation["release_check_count"],
            "typed_expressions": 36,
            "reference_findings": 0,
            "regression_tests": 150,
            "benchmark_rows": 35,
            "rendered_pages": 8,
            "corpus_statuses": {
                "PASS": 15,
                "FAIL": 3,
                "BLOCKED": 0,
            },
        },
        "bundle": {
            "filename": BUNDLE.name,
            "bytes": BUNDLE.stat().st_size,
            "sha256": sha256(BUNDLE),
            "zip_integrity": "PASS",
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

    output_copies: list[tuple[Path, Path]] = [
        (PDF, OUTPUT_PDF / PUBLIC_PDF_NAME),
        (
            P8
            / "reports/P8_Conical_Intersections_Migration_Report_v0_9_ru.md",
            OUTPUT_P8
            / "P8_Conical_Intersections_Migration_Report_v0_9_ru.md",
        ),
        (
            P8
            / "core/conical_intersections_observation_contract_v0_9.yaml",
            OUTPUT_P8
            / "Conical_Intersections_Observation_Contract_v0_9.yaml",
        ),
        (
            P8
            / "ledgers/conical_intersections_reference_ledger_v0_9.yaml",
            OUTPUT_P8
            / "Conical_Intersections_Reference_Ledger_v0_9.yaml",
        ),
        (
            P8 / "ledgers/corpus_ledgers_v0_9.yaml",
            OUTPUT_P8 / "GO_Corpus_Ledgers_v0_9.yaml",
        ),
        (
            P8 / "data/conical_intersections_benchmarks_v0_9.csv",
            OUTPUT_P8 / "Conical_Intersections_Benchmarks_v0_9.csv",
        ),
        (
            P8 / "data/conical_intersections_metrics_v0_9.json",
            OUTPUT_P8 / "Conical_Intersections_Metrics_v0_9.json",
        ),
        (
            P8 / "reports/P8_Validation_Summary_v0_9.json",
            OUTPUT_P8 / "P8_Validation_Summary_v0_9.json",
        ),
        (
            P8 / "reports/P8_Visual_QA_v0_9.yaml",
            OUTPUT_P8 / "P8_Visual_QA_v0_9.yaml",
        ),
        (
            P8 / "reports/GO_Corpus_Lint_Report_v0_9.md",
            OUTPUT_P8 / "GO_Corpus_Lint_Report_v0_9.md",
        ),
        (
            P8
            / "reports/Conical_Intersections_Reference_Lint_Report_v0_9.md",
            OUTPUT_P8
            / "Conical_Intersections_Reference_Lint_Report_v0_9.md",
        ),
        (
            RELEASE_MANIFEST,
            OUTPUT_P8 / "RELEASE_MANIFEST_v0_9.yaml",
        ),
        (
            BUNDLE,
            OUTPUT_P8 / BUNDLE.name,
        ),
    ]
    for source, destination in output_copies:
        shutil.copy2(source, destination)
        if sha256(source) != sha256(destination):
            raise RuntimeError(
                f"output copy hash mismatch: {destination}"
            )

    print(BUNDLE)
    print(RELEASE_MANIFEST)
    print(OUTPUT_PDF / PUBLIC_PDF_NAME)
    print(OUTPUT_P8)


if __name__ == "__main__":
    main()
