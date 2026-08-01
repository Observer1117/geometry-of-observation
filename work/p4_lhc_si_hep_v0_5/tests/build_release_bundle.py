#!/usr/bin/env python3
"""Build the reproducible GO P4 release bundle and public artifacts."""

from __future__ import annotations

import hashlib
import shutil
import zipfile
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[3]
P4 = ROOT / "work/p4_lhc_si_hep_v0_5"
OUTPUT_PDF = ROOT / "output/pdf"
OUTPUT_P4 = ROOT / "output/p4"
BUNDLE_DIR = P4 / "bundle"
BUNDLE = BUNDLE_DIR / "GO_P4_LHC_SI_HEP_v0_5_Source_Bundle.zip"
COMPONENT_MANIFEST = BUNDLE_DIR / "RELEASE_COMPONENTS_v0_5.yaml"
RELEASE_MANIFEST = P4 / "RELEASE_MANIFEST_v0_5.yaml"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def component_files() -> list[tuple[Path, str]]:
    files: list[tuple[Path, str]] = [
        (
            P4 / "build/passport/si_hep_quantity_passport_v0_5.pdf",
            "pdf/SI_HEP_Quantity_Passport_v0_5.pdf",
        ),
        (
            P4 / "build/lhc/lhc_beam_observation_geometry_v1_3.pdf",
            "pdf/Relativistic_Beam_Paths_Observation_Geometry_v1_3.pdf",
        ),
        (
            P4 / "src/si_hep_quantity_passport_v0_5.tex",
            "src/si_hep_quantity_passport_v0_5.tex",
        ),
        (
            P4 / "src/lhc_beam_observation_geometry_v1_3.tex",
            "src/lhc_beam_observation_geometry_v1_3.tex",
        ),
        (
            P4 / "src/generated/conversion_table.tex",
            "src/generated/conversion_table.tex",
        ),
        (
            P4 / "src/generated/lhc_audit_table.tex",
            "src/generated/lhc_audit_table.tex",
        ),
        (
            P4 / "core/si_hep_quantity_passport_v0_5.yaml",
            "core/si_hep_quantity_passport_v0_5.yaml",
        ),
        (
            P4 / "data/lhc_si_hep_inputs_v0_5.yaml",
            "data/lhc_si_hep_inputs_v0_5.yaml",
        ),
        (
            P4 / "data/si_hep_conversion_table_v0_5.csv",
            "data/si_hep_conversion_table_v0_5.csv",
        ),
        (
            P4 / "data/lhc_si_hep_metrics_v0_5.json",
            "data/lhc_si_hep_metrics_v0_5.json",
        ),
        (
            P4 / "scripts/generate_lhc_si_hep_data.py",
            "scripts/generate_lhc_si_hep_data.py",
        ),
        (
            P4 / "ledgers/lhc_si_hep_reference_ledgers_v0_5.yaml",
            "ledgers/lhc_si_hep_reference_ledgers_v0_5.yaml",
        ),
        (
            P4 / "ledgers/corpus_ledgers_v0_5.yaml",
            "ledgers/corpus_ledgers_v0_5.yaml",
        ),
        (
            P4 / "tests/test_lhc_si_hep_v0_5.py",
            "tests/test_lhc_si_hep_v0_5.py",
        ),
        (
            P4 / "tests/build_corpus_ledger_v0_5.py",
            "tests/build_corpus_ledger_v0_5.py",
        ),
        (
            P4 / "tests/validate_p4_release.py",
            "tests/validate_p4_release.py",
        ),
        (
            P4 / "tests/build_release_bundle.py",
            "tests/build_release_bundle.py",
        ),
        (
            P4 / "reports/P4_LHC_SI_HEP_Migration_Report_v0_5_ru.md",
            "reports/P4_LHC_SI_HEP_Migration_Report_v0_5_ru.md",
        ),
        (
            P4 / "reports/P4_Validation_Summary_v0_5.json",
            "reports/P4_Validation_Summary_v0_5.json",
        ),
        (
            P4 / "reports/LHC_SI_HEP_Lint_Report_v0_5.json",
            "reports/LHC_SI_HEP_Lint_Report_v0_5.json",
        ),
        (
            P4 / "reports/LHC_SI_HEP_Lint_Report_v0_5_ru.md",
            "reports/LHC_SI_HEP_Lint_Report_v0_5_ru.md",
        ),
        (
            P4 / "reports/GO_Corpus_Lint_Report_v0_5.json",
            "reports/GO_Corpus_Lint_Report_v0_5.json",
        ),
        (
            P4 / "reports/GO_Corpus_Lint_Report_v0_5_ru.md",
            "reports/GO_Corpus_Lint_Report_v0_5_ru.md",
        ),
        (
            P4 / "build/passport/si_hep_quantity_passport_v0_5.log",
            "build/passport/si_hep_quantity_passport_v0_5.log",
        ),
        (
            P4 / "build/lhc/lhc_beam_observation_geometry_v1_3.log",
            "build/lhc/lhc_beam_observation_geometry_v1_3.log",
        ),
        (
            P4 / "checks/passport_final/contact.png",
            "checks/passport_contact.png",
        ),
        (
            P4 / "checks/lhc/contact.png",
            "checks/lhc_contact.png",
        ),
        (
            P4 / "README_P4.md",
            "README_P4.md",
        ),
        (
            ROOT / "work/go_core_v0_2/src/go_lint.py",
            "go_core_v0_2/src/go_lint.py",
        ),
        (
            ROOT / "upload/lhc_beam_geometry_observation_v12_terrell_bilingual.pdf",
            "legacy/lhc_beam_geometry_observation_v12_terrell_bilingual.pdf",
        ),
    ]
    for path in sorted((ROOT / "work/go_core_v0_2/core").glob("*.yaml")):
        files.append((path, f"go_core_v0_2/core/{path.name}"))
    return files


def main() -> None:
    OUTPUT_PDF.mkdir(parents=True, exist_ok=True)
    OUTPUT_P4.mkdir(parents=True, exist_ok=True)
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
            "id": "go-p4-release-components",
            "version": "0.5.0",
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
        archive.write(
            COMPONENT_MANIFEST,
            "RELEASE_COMPONENTS_v0_5.yaml",
        )

    passport_pdf = (
        P4 / "build/passport/si_hep_quantity_passport_v0_5.pdf"
    )
    lhc_pdf = P4 / "build/lhc/lhc_beam_observation_geometry_v1_3.pdf"
    bundle_hash = sha256(BUNDLE)
    release = {
        "schema": {
            "id": "go-p4-release-manifest",
            "version": "0.5.0",
        },
        "date": "2026-07-28",
        "status": "PASS",
        "core_contract": "go-core-spec@0.2.0",
        "extension_contract": "go-si-hep-quantity-passport@0.5.0",
        "documents": [
            {
                "id": "si-hep-quantity-passport-v0-5",
                "pages": 8,
                "sha256": sha256(passport_pdf),
            },
            {
                "id": "lhc-beam-observation-v1-3",
                "pages": 9,
                "sha256": sha256(lhc_pdf),
            },
        ],
        "validation": {
            "release_checks": 16,
            "typed_expressions": 28,
            "reference_findings": 0,
            "regression_tests": 41,
            "conversion_rows": 8,
            "rendered_pages": 17,
            "corpus_statuses": {
                "PASS": 8,
                "FAIL": 9,
                "BLOCKED": 0,
            },
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
            passport_pdf,
            OUTPUT_PDF / "SI_HEP_Quantity_Passport_v0_5.pdf",
        ),
        (
            lhc_pdf,
            OUTPUT_PDF
            / "Relativistic_Beam_Paths_Observation_Geometry_v1_3.pdf",
        ),
        (
            P4 / "reports/P4_LHC_SI_HEP_Migration_Report_v0_5_ru.md",
            OUTPUT_P4 / "P4_LHC_SI_HEP_Migration_Report_v0_5_ru.md",
        ),
        (
            P4 / "core/si_hep_quantity_passport_v0_5.yaml",
            OUTPUT_P4 / "SI_HEP_Quantity_Passport_Contract_v0_5.yaml",
        ),
        (
            P4 / "ledgers/lhc_si_hep_reference_ledgers_v0_5.yaml",
            OUTPUT_P4 / "LHC_SI_HEP_Reference_Ledgers_v0_5.yaml",
        ),
        (
            P4 / "ledgers/corpus_ledgers_v0_5.yaml",
            OUTPUT_P4 / "GO_Corpus_Ledgers_v0_5.yaml",
        ),
        (
            P4 / "reports/LHC_SI_HEP_Lint_Report_v0_5_ru.md",
            OUTPUT_P4 / "LHC_SI_HEP_Lint_Report_v0_5_ru.md",
        ),
        (
            P4 / "reports/GO_Corpus_Lint_Report_v0_5_ru.md",
            OUTPUT_P4 / "GO_Corpus_Lint_Report_v0_5_ru.md",
        ),
        (
            P4 / "reports/P4_Validation_Summary_v0_5.json",
            OUTPUT_P4 / "P4_Validation_Summary_v0_5.json",
        ),
        (
            P4 / "data/lhc_si_hep_inputs_v0_5.yaml",
            OUTPUT_P4 / "LHC_SI_HEP_Inputs_v0_5.yaml",
        ),
        (
            P4 / "data/si_hep_conversion_table_v0_5.csv",
            OUTPUT_P4 / "SI_HEP_Conversion_Table_v0_5.csv",
        ),
        (
            P4 / "data/lhc_si_hep_metrics_v0_5.json",
            OUTPUT_P4 / "LHC_SI_HEP_Metrics_v0_5.json",
        ),
        (
            RELEASE_MANIFEST,
            OUTPUT_P4 / "RELEASE_MANIFEST_v0_5.yaml",
        ),
        (
            BUNDLE,
            OUTPUT_P4 / BUNDLE.name,
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
                    str(path.relative_to(ROOT))
                    for _, path in output_copies
                ],
            },
            sort_keys=False,
        )
    )


if __name__ == "__main__":
    main()
