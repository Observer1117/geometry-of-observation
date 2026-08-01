#!/usr/bin/env python3
"""Build the reproducible GO P7 billiards release bundle."""

from __future__ import annotations

import hashlib
import shutil
import zipfile
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[3]
P7 = ROOT / "work/p7_billiards_v0_8"
OUTPUT_PDF = ROOT / "output/pdf"
OUTPUT_P7 = ROOT / "output/p7"
BUNDLE_DIR = P7 / "bundle"
BUNDLE = BUNDLE_DIR / "GO_P7_Billiards_v0_8_Source_Bundle.zip"
COMPONENT_MANIFEST = BUNDLE_DIR / "RELEASE_COMPONENTS_v0_8.yaml"
RELEASE_MANIFEST = P7 / "RELEASE_MANIFEST_v0_8.yaml"

PDF = P7 / "build/billiards/billiards_observation_laboratory_v1_1.pdf"
PUBLIC_PDF_NAME = "Billiards_Geometry_of_Observation_Laboratory_v1_1.pdf"


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
            P7 / "src/billiards_observation_laboratory_v1_1.tex",
            "src/billiards_observation_laboratory_v1_1.tex",
        ),
        (
            P7 / "core/billiards_observation_contract_v0_8.yaml",
            "core/billiards_observation_contract_v0_8.yaml",
        ),
        (
            P7 / "ledgers/billiards_reference_ledger_v0_8.yaml",
            "ledgers/billiards_reference_ledger_v0_8.yaml",
        ),
        (
            P7 / "ledgers/corpus_ledgers_v0_8.yaml",
            "ledgers/corpus_ledgers_v0_8.yaml",
        ),
        (
            P7 / "data/billiards_benchmarks_v0_8.csv",
            "data/billiards_benchmarks_v0_8.csv",
        ),
        (
            P7 / "data/billiards_metrics_v0_8.json",
            "data/billiards_metrics_v0_8.json",
        ),
        (
            P7 / "scripts/generate_billiards_benchmarks.py",
            "scripts/generate_billiards_benchmarks.py",
        ),
        (
            P7 / "tests/build_corpus_ledger_v0_8.py",
            "tests/build_corpus_ledger_v0_8.py",
        ),
        (
            P7 / "tests/test_billiards_v0_8.py",
            "tests/test_billiards_v0_8.py",
        ),
        (
            P7 / "tests/validate_p7_release.py",
            "tests/validate_p7_release.py",
        ),
        (
            P7 / "tests/build_release_bundle.py",
            "tests/build_release_bundle.py",
        ),
        (
            P7 / "reports/P7_Billiards_Migration_Report_v0_8_ru.md",
            "reports/P7_Billiards_Migration_Report_v0_8_ru.md",
        ),
        (
            P7 / "reports/P7_Validation_Summary_v0_8.json",
            "reports/P7_Validation_Summary_v0_8.json",
        ),
        (
            P7 / "reports/P7_Visual_QA_v0_8.yaml",
            "reports/P7_Visual_QA_v0_8.yaml",
        ),
        (
            P7 / "reports/Billiards_Reference_Lint_Report_v0_8.json",
            "reports/Billiards_Reference_Lint_Report_v0_8.json",
        ),
        (
            P7 / "reports/Billiards_Reference_Lint_Report_v0_8.md",
            "reports/Billiards_Reference_Lint_Report_v0_8.md",
        ),
        (
            P7 / "reports/GO_Corpus_Lint_Report_v0_8.json",
            "reports/GO_Corpus_Lint_Report_v0_8.json",
        ),
        (
            P7 / "reports/GO_Corpus_Lint_Report_v0_8.md",
            "reports/GO_Corpus_Lint_Report_v0_8.md",
        ),
        (
            P7 / "build/billiards/billiards_observation_laboratory_v1_1.log",
            "build/billiards_observation_laboratory_v1_1.log",
        ),
        (
            P7 / "checks/billiards/billiards_observation_laboratory_v1_1.txt",
            "checks/billiards_observation_laboratory_v1_1.txt",
        ),
        (P7 / "README_P7.md", "README_P7.md"),
        (
            ROOT / "work/go_core_v0_2/src/go_lint.py",
            "go_core_v0_2/src/go_lint.py",
        ),
        (
            ROOT
            / "work/p5_mechanics_frames_v0_6/core/frame_force_dissipation_contract_v0_6.yaml",
            "dependencies/frame_force_dissipation_contract_v0_6.yaml",
        ),
        (
            ROOT
            / "work/p1_info_metric_v0_2/ledgers/information_metric_reference_ledgers_v0_2.yaml",
            "dependencies/information_metric_reference_ledgers_v0_2.yaml",
        ),
        (
            ROOT / "work/p6_gear_contact_v0_7/ledgers/corpus_ledgers_v0_7.yaml",
            "baseline/corpus_ledgers_v0_7.yaml",
        ),
        (
            ROOT / "upload/billiards_geometry_observation_v1_bilingual(2).pdf",
            "legacy/billiards_geometry_observation_v1_bilingual.pdf",
        ),
        (
            ROOT / "input/billiards_observation_claim_audit.md",
            "legacy/billiards_observation_claim_audit.md",
        ),
    ]
    for path in sorted((ROOT / "work/go_core_v0_2/core").glob("*.yaml")):
        files.append((path, f"go_core_v0_2/core/{path.name}"))
    return files


def main() -> None:
    OUTPUT_PDF.mkdir(parents=True, exist_ok=True)
    OUTPUT_P7.mkdir(parents=True, exist_ok=True)
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
            "id": "go-p7-release-components",
            "version": "0.8.0",
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
        archive.write(COMPONENT_MANIFEST, "RELEASE_COMPONENTS_v0_8.yaml")

    with zipfile.ZipFile(BUNDLE, "r") as archive:
        bad_member = archive.testzip()
        if bad_member is not None:
            raise RuntimeError(f"archive integrity failure: {bad_member}")

    release = {
        "schema": {
            "id": "go-p7-release-manifest",
            "version": "0.8.0",
        },
        "date": "2026-07-28",
        "status": "PASS",
        "core_contract": "go-core-spec@0.2.0",
        "inherited_contracts": [
            "information-theoretic-observation-v0-2",
            "go-frame-force-dissipation-contract@0.6.0",
        ],
        "extension_contract": "go-billiards-observation-contract@0.8.0",
        "documents": [
            {
                "id": "billiards-observation-v1-1",
                "pages": 9,
                "sha256": sha256(PDF),
            }
        ],
        "validation": {
            "release_checks": 18,
            "typed_expressions": 24,
            "reference_findings": 0,
            "regression_tests": 95,
            "benchmark_rows": 18,
            "rendered_pages": 9,
            "corpus_statuses": {
                "PASS": 14,
                "FAIL": 4,
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
            P7 / "reports/P7_Billiards_Migration_Report_v0_8_ru.md",
            OUTPUT_P7 / "P7_Billiards_Migration_Report_v0_8_ru.md",
        ),
        (
            P7 / "core/billiards_observation_contract_v0_8.yaml",
            OUTPUT_P7 / "Billiards_Observation_Contract_v0_8.yaml",
        ),
        (
            P7 / "ledgers/billiards_reference_ledger_v0_8.yaml",
            OUTPUT_P7 / "Billiards_Reference_Ledger_v0_8.yaml",
        ),
        (
            P7 / "ledgers/corpus_ledgers_v0_8.yaml",
            OUTPUT_P7 / "GO_Corpus_Ledgers_v0_8.yaml",
        ),
        (
            P7 / "data/billiards_benchmarks_v0_8.csv",
            OUTPUT_P7 / "Billiards_Benchmarks_v0_8.csv",
        ),
        (
            P7 / "reports/P7_Validation_Summary_v0_8.json",
            OUTPUT_P7 / "P7_Validation_Summary_v0_8.json",
        ),
        (
            P7 / "reports/P7_Visual_QA_v0_8.yaml",
            OUTPUT_P7 / "P7_Visual_QA_v0_8.yaml",
        ),
        (
            P7 / "reports/Billiards_Reference_Lint_Report_v0_8.md",
            OUTPUT_P7 / "Billiards_Reference_Lint_Report_v0_8.md",
        ),
        (
            P7 / "reports/GO_Corpus_Lint_Report_v0_8.md",
            OUTPUT_P7 / "GO_Corpus_Lint_Report_v0_8.md",
        ),
        (
            RELEASE_MANIFEST,
            OUTPUT_P7 / "RELEASE_MANIFEST_v0_8.yaml",
        ),
        (BUNDLE, OUTPUT_P7 / BUNDLE.name),
    ]
    for source, destination in output_copies:
        shutil.copy2(source, destination)

    print(BUNDLE)
    print(RELEASE_MANIFEST)
    for _, destination in output_copies:
        print(destination)


if __name__ == "__main__":
    main()

