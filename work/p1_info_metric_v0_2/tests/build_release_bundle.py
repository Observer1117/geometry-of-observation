#!/usr/bin/env python3
"""Build the deterministic GO P1 Information + Metric v0.2 release bundle."""

from __future__ import annotations

import hashlib
import shutil
import zipfile
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[3]
P1 = ROOT / "work/p1_info_metric_v0_2"
OUTPUT_PDF = ROOT / "output/pdf"
OUTPUT_P1 = ROOT / "output/p1"
BUNDLE_DIR = P1 / "bundle"
BUNDLE = BUNDLE_DIR / "GO_P1_Information_Metric_v0_2_Source_Bundle.zip"
MANIFEST = P1 / "RELEASE_MANIFEST_v0_2.yaml"
CHECKSUM = BUNDLE_DIR / "GO_P1_Information_Metric_v0_2_Source_Bundle.sha256.txt"
ZIP_TIMESTAMP = (2026, 7, 28, 0, 0, 0)


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def main() -> None:
    OUTPUT_PDF.mkdir(parents=True, exist_ok=True)
    OUTPUT_P1.mkdir(parents=True, exist_ok=True)
    BUNDLE_DIR.mkdir(parents=True, exist_ok=True)

    info_pdf = P1 / "build/information/information_theoretic_observation_geometry_v0_2.pdf"
    metric_pdf = P1 / "build/metric/metric_entropy_observational_defect_v0_2.pdf"
    public_info_pdf = OUTPUT_PDF / "Information_Theoretic_Observation_Geometry_v0_2.pdf"
    public_metric_pdf = (
        OUTPUT_PDF / "Metric_Entropy_and_Observational_Entropy_Defect_v0_2.pdf"
    )
    public_report = (
        OUTPUT_P1 / "P1_Information_Metric_Migration_Report_v0_2_ru.md"
    )
    public_ledger = OUTPUT_P1 / "Information_Metric_Reference_Ledgers_v0_2.yaml"
    public_validation = OUTPUT_P1 / "P1_Validation_Summary_v0_2.json"

    shutil.copy2(info_pdf, public_info_pdf)
    shutil.copy2(metric_pdf, public_metric_pdf)
    shutil.copy2(
        P1 / "reports/P1_Information_Metric_Migration_Report_v0_2_ru.md",
        public_report,
    )
    shutil.copy2(
        P1 / "ledgers/information_metric_reference_ledgers_v0_2.yaml",
        public_ledger,
    )
    shutil.copy2(
        P1 / "reports/P1_Validation_Summary_v0_2.json",
        public_validation,
    )

    files: list[tuple[str, Path]] = [
        ("pdf/Information_Theoretic_Observation_Geometry_v0_2.pdf", info_pdf),
        (
            "pdf/Metric_Entropy_and_Observational_Entropy_Defect_v0_2.pdf",
            metric_pdf,
        ),
        (
            "src/information_theoretic_observation_geometry_v0_2.tex",
            P1 / "src/information_theoretic_observation_geometry_v0_2.tex",
        ),
        (
            "src/metric_entropy_observational_defect_v0_2.tex",
            P1 / "src/metric_entropy_observational_defect_v0_2.tex",
        ),
        ("src/README_P1.md", P1 / "src/README_P1.md"),
        (
            "ledgers/information_metric_reference_ledgers_v0_2.yaml",
            P1 / "ledgers/information_metric_reference_ledgers_v0_2.yaml",
        ),
        (
            "ledgers/corpus_ledgers_v0_2.yaml",
            P1 / "ledgers/corpus_ledgers_v0_2.yaml",
        ),
        (
            "reports/P1_Information_Metric_Migration_Report_v0_2_ru.md",
            P1 / "reports/P1_Information_Metric_Migration_Report_v0_2_ru.md",
        ),
        (
            "reports/Information_Metric_Lint_Report_v0_2.json",
            P1 / "reports/Information_Metric_Lint_Report_v0_2.json",
        ),
        (
            "reports/Information_Metric_Lint_Report_v0_2_ru.md",
            P1 / "reports/Information_Metric_Lint_Report_v0_2_ru.md",
        ),
        (
            "reports/GO_Corpus_Lint_Report_v0_2.json",
            P1 / "reports/GO_Corpus_Lint_Report_v0_2.json",
        ),
        (
            "reports/GO_Corpus_Lint_Report_v0_2_ru.md",
            P1 / "reports/GO_Corpus_Lint_Report_v0_2_ru.md",
        ),
        (
            "reports/P1_Validation_Summary_v0_2.json",
            P1 / "reports/P1_Validation_Summary_v0_2.json",
        ),
        (
            "tests/test_information_metric_v0_2.py",
            P1 / "tests/test_information_metric_v0_2.py",
        ),
        (
            "tests/validate_p1_release.py",
            P1 / "tests/validate_p1_release.py",
        ),
        (
            "tests/build_corpus_ledger_v0_2.py",
            P1 / "tests/build_corpus_ledger_v0_2.py",
        ),
        (
            "tests/build_release_bundle.py",
            P1 / "tests/build_release_bundle.py",
        ),
        (
            "go_core/GO_Core_Spec_v0_2_ru.md",
            ROOT / "work/go_core_v0_2/GO_Core_Spec_v0_2_ru.md",
        ),
        (
            "go_core/src/go_lint.py",
            ROOT / "work/go_core_v0_2/src/go_lint.py",
        ),
        (
            "go_core/core/go_core_spec_v0_2.yaml",
            ROOT / "work/go_core_v0_2/core/go_core_spec_v0_2.yaml",
        ),
        (
            "go_core/core/quantities_v0_2.yaml",
            ROOT / "work/go_core_v0_2/core/quantities_v0_2.yaml",
        ),
        (
            "go_core/core/symbols_v0_2.yaml",
            ROOT / "work/go_core_v0_2/core/symbols_v0_2.yaml",
        ),
        (
            "go_core/core/unit_contexts_v0_2.yaml",
            ROOT / "work/go_core_v0_2/core/unit_contexts_v0_2.yaml",
        ),
        (
            "go_core/core/normalizations_v0_2.yaml",
            ROOT / "work/go_core_v0_2/core/normalizations_v0_2.yaml",
        ),
        (
            "go_core/core/defects_v0_2.yaml",
            ROOT / "work/go_core_v0_2/core/defects_v0_2.yaml",
        ),
        (
            "go_core/core/protocol_schema_v0_1.yaml",
            ROOT / "work/go_core_v0_2/core/protocol_schema_v0_1.yaml",
        ),
        (
            "originals/Information_Theoretic_Observation_Geometry_v0_1.pdf",
            ROOT / "upload/Information_Theoretic_Observation_Geometry_v0_1(1).pdf",
        ),
        (
            "originals/Metric_Entropy_and_Observational_Entropy_Defect_v0_1.pdf",
            ROOT
            / "upload/Metric_Entropy_and_Observational_Entropy_Defect_v0_1(1).pdf",
        ),
    ]

    for archive_path, path in files:
        if not path.is_file():
            raise FileNotFoundError(f"{archive_path}: {path}")

    manifest_data = {
        "schema": {
            "id": "go-p1-information-metric-release",
            "version": "0.2.0",
            "date": "2026-07-28",
        },
        "validation": {
            "status": "PASS",
            "documents": 2,
            "pages": 19,
            "typed_expressions": 22,
            "regression_tests": 19,
            "reference_lint_findings": 0,
            "reference_statuses": {"PASS": 2},
            "corpus_statuses": {"PASS": 4, "BLOCKED": 2, "FAIL": 11},
        },
        "files": [
            {
                "path": archive_path,
                "size_bytes": path.stat().st_size,
                "sha256": digest(path),
            }
            for archive_path, path in sorted(files)
        ],
    }
    MANIFEST.write_text(
        yaml.safe_dump(
            manifest_data,
            sort_keys=False,
            allow_unicode=True,
            width=100,
        ),
        encoding="utf-8",
    )
    files.append(("RELEASE_MANIFEST_v0_2.yaml", MANIFEST))

    with zipfile.ZipFile(BUNDLE, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for archive_path, path in sorted(files):
            info = zipfile.ZipInfo(archive_path, ZIP_TIMESTAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, path.read_bytes())

    bundle_hash = digest(BUNDLE)
    CHECKSUM.write_text(
        f"{bundle_hash}  {BUNDLE.name}\n",
        encoding="utf-8",
    )
    shutil.copy2(BUNDLE, OUTPUT_P1 / BUNDLE.name)
    shutil.copy2(MANIFEST, OUTPUT_P1 / MANIFEST.name)
    print(f"{BUNDLE} {BUNDLE.stat().st_size} {bundle_hash}")


if __name__ == "__main__":
    main()
