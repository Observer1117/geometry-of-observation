#!/usr/bin/env python3
"""Build the reproducible GO P3 release bundle and public output artifacts."""

from __future__ import annotations

import hashlib
import shutil
import zipfile
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[3]
P3 = ROOT / "work/p3_planck_cosmos_v0_4"
OUTPUT_PDF = ROOT / "output/pdf"
OUTPUT_P3 = ROOT / "output/p3"
BUNDLE_DIR = P3 / "bundle"
BUNDLE = BUNDLE_DIR / "GO_P3_Planck_Cosmos_v0_4_Source_Bundle.zip"
COMPONENT_MANIFEST = BUNDLE_DIR / "RELEASE_COMPONENTS_v0_4.yaml"
RELEASE_MANIFEST = P3 / "RELEASE_MANIFEST_v0_4.yaml"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def component_files() -> list[tuple[Path, str]]:
    files: list[tuple[Path, str]] = [
        (
            P3 / "build/planck/planck_cosmos_observation_rulers_v1_1.pdf",
            "pdf/Planck_to_Cosmos_Observation_Rulers_v1_1.pdf",
        ),
        (
            P3 / "src/planck_cosmos_observation_rulers_v1_1.tex",
            "src/planck_cosmos_observation_rulers_v1_1.tex",
        ),
        (
            P3 / "src/generated/planck_anchor_table.tex",
            "src/generated/planck_anchor_table.tex",
        ),
        (
            P3 / "src/generated/cosmic_landmark_table.tex",
            "src/generated/cosmic_landmark_table.tex",
        ),
        (
            P3 / "src/generated/selected_scale_catalogue_table.tex",
            "src/generated/selected_scale_catalogue_table.tex",
        ),
        (
            P3 / "core/planck_cosmos_scale_contract_v0_4.yaml",
            "core/planck_cosmos_scale_contract_v0_4.yaml",
        ),
        (
            P3 / "data/planck_cosmos_inputs_v0_4.yaml",
            "data/planck_cosmos_inputs_v0_4.yaml",
        ),
        (
            P3 / "data/planck_cosmos_landmarks_v0_4.csv",
            "data/planck_cosmos_landmarks_v0_4.csv",
        ),
        (
            P3 / "data/planck_cosmos_metrics_v0_4.json",
            "data/planck_cosmos_metrics_v0_4.json",
        ),
        (
            P3 / "scripts/generate_planck_cosmos_data.py",
            "scripts/generate_planck_cosmos_data.py",
        ),
        (
            P3 / "ledgers/planck_cosmos_reference_ledger_v0_4.yaml",
            "ledgers/planck_cosmos_reference_ledger_v0_4.yaml",
        ),
        (
            P3 / "ledgers/corpus_ledgers_v0_4.yaml",
            "ledgers/corpus_ledgers_v0_4.yaml",
        ),
        (
            P3 / "tests/test_planck_cosmos_v0_4.py",
            "tests/test_planck_cosmos_v0_4.py",
        ),
        (
            P3 / "tests/build_corpus_ledger_v0_4.py",
            "tests/build_corpus_ledger_v0_4.py",
        ),
        (
            P3 / "tests/validate_p3_release.py",
            "tests/validate_p3_release.py",
        ),
        (
            P3 / "tests/build_release_bundle.py",
            "tests/build_release_bundle.py",
        ),
        (
            P3 / "reports/P3_Planck_Cosmos_Migration_Report_v0_4_ru.md",
            "reports/P3_Planck_Cosmos_Migration_Report_v0_4_ru.md",
        ),
        (
            P3 / "reports/P3_Validation_Summary_v0_4.json",
            "reports/P3_Validation_Summary_v0_4.json",
        ),
        (
            P3 / "reports/Planck_Cosmos_Lint_Report_v0_4.json",
            "reports/Planck_Cosmos_Lint_Report_v0_4.json",
        ),
        (
            P3 / "reports/Planck_Cosmos_Lint_Report_v0_4_ru.md",
            "reports/Planck_Cosmos_Lint_Report_v0_4_ru.md",
        ),
        (
            P3 / "reports/GO_Corpus_Lint_Report_v0_4.json",
            "reports/GO_Corpus_Lint_Report_v0_4.json",
        ),
        (
            P3 / "reports/GO_Corpus_Lint_Report_v0_4_ru.md",
            "reports/GO_Corpus_Lint_Report_v0_4_ru.md",
        ),
        (
            P3 / "checks/planck/contact.png",
            "checks/planck_contact.png",
        ),
        (P3 / "README_P3.md", "README_P3.md"),
        (
            ROOT / "work/go_core_v0_2/src/go_lint.py",
            "go_core_v0_2/src/go_lint.py",
        ),
        (
            ROOT / "work/p2_distance_scale_v0_3/core/distance_scale_contract_v0_3.yaml",
            "inherited/distance_scale_contract_v0_3.yaml",
        ),
        (
            ROOT / "upload/planck_cosmos_observation_rulers_v1_bilingual(3).pdf",
            "legacy/planck_cosmos_observation_rulers_v1_bilingual.pdf",
        ),
    ]
    for path in sorted((ROOT / "work/go_core_v0_2/core").glob("*.yaml")):
        files.append((path, f"go_core_v0_2/core/{path.name}"))
    return files


def main() -> None:
    OUTPUT_PDF.mkdir(parents=True, exist_ok=True)
    OUTPUT_P3.mkdir(parents=True, exist_ok=True)
    BUNDLE_DIR.mkdir(parents=True, exist_ok=True)

    files = component_files()
    missing = [str(path) for path, _ in files if not path.is_file()]
    if missing:
        raise FileNotFoundError("Missing release components:\n" + "\n".join(missing))

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
        "schema": {"id": "go-p3-release-components", "version": "0.4.0"},
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
        archive.write(COMPONENT_MANIFEST, "RELEASE_COMPONENTS_v0_4.yaml")

    pdf = P3 / "build/planck/planck_cosmos_observation_rulers_v1_1.pdf"
    bundle_hash = sha256(BUNDLE)
    release = {
        "schema": {"id": "go-p3-release-manifest", "version": "0.4.0"},
        "date": "2026-07-28",
        "status": "PASS",
        "core_contract": "go-core-spec@0.2.0",
        "inherited_contract": "go-distance-scale-contract@0.3.0",
        "extension_contract": "go-planck-cosmos-scale-contract@0.4.0",
        "documents": [
            {
                "id": "planck-cosmos-rulers-v1-1",
                "pages": 12,
                "sha256": sha256(pdf),
            }
        ],
        "validation": {
            "release_checks": 13,
            "typed_expressions": 19,
            "reference_findings": 0,
            "regression_tests": 29,
            "catalogue_rows": 24,
            "rendered_pages": 12,
            "corpus_statuses": {"PASS": 7, "BLOCKED": 1, "FAIL": 9},
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
            pdf,
            OUTPUT_PDF / "Planck_to_Cosmos_Observation_Rulers_v1_1.pdf",
        ),
        (
            P3 / "reports/P3_Planck_Cosmos_Migration_Report_v0_4_ru.md",
            OUTPUT_P3 / "P3_Planck_Cosmos_Migration_Report_v0_4_ru.md",
        ),
        (
            P3 / "core/planck_cosmos_scale_contract_v0_4.yaml",
            OUTPUT_P3 / "Planck_Cosmos_Scale_Contract_v0_4.yaml",
        ),
        (
            P3 / "ledgers/planck_cosmos_reference_ledger_v0_4.yaml",
            OUTPUT_P3 / "Planck_Cosmos_Reference_Ledger_v0_4.yaml",
        ),
        (
            P3 / "ledgers/corpus_ledgers_v0_4.yaml",
            OUTPUT_P3 / "GO_Corpus_Ledgers_v0_4.yaml",
        ),
        (
            P3 / "reports/GO_Corpus_Lint_Report_v0_4_ru.md",
            OUTPUT_P3 / "GO_Corpus_Lint_Report_v0_4_ru.md",
        ),
        (
            P3 / "reports/P3_Validation_Summary_v0_4.json",
            OUTPUT_P3 / "P3_Validation_Summary_v0_4.json",
        ),
        (
            P3 / "data/planck_cosmos_landmarks_v0_4.csv",
            OUTPUT_P3 / "Planck_Cosmos_Landmarks_v0_4.csv",
        ),
        (
            P3 / "data/planck_cosmos_metrics_v0_4.json",
            OUTPUT_P3 / "Planck_Cosmos_Metrics_v0_4.json",
        ),
        (
            RELEASE_MANIFEST,
            OUTPUT_P3 / "RELEASE_MANIFEST_v0_4.yaml",
        ),
        (
            BUNDLE,
            OUTPUT_P3 / BUNDLE.name,
        ),
    ]
    for source, destination in output_copies:
        shutil.copy2(source, destination)

    print(
        yaml.safe_dump(
            {
                "bundle": str(BUNDLE.relative_to(ROOT)),
                "bundle_sha256": bundle_hash,
                "output_files": [
                    str(path.relative_to(ROOT)) for _, path in output_copies
                ],
            },
            sort_keys=False,
        )
    )


if __name__ == "__main__":
    main()
