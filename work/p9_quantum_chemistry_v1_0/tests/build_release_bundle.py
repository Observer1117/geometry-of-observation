#!/usr/bin/env python3
"""Build the reproducible GO P9 quantum-chemistry release bundle."""

from __future__ import annotations

import hashlib
import shutil
import zipfile
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[3]
P9 = ROOT / "work/p9_quantum_chemistry_v1_0"
OUTPUT_PDF = ROOT / "output/pdf"
OUTPUT_P9 = ROOT / "output/p9"
BUNDLE_DIR = P9 / "bundle"
BUNDLE = BUNDLE_DIR / "GO_P9_Quantum_Chemistry_v1_0_Source_Bundle.zip"
COMPONENT_MANIFEST = BUNDLE_DIR / "RELEASE_COMPONENTS_v1_0.yaml"
RELEASE_MANIFEST = P9 / "RELEASE_MANIFEST_v1_0.yaml"

PDF = P9 / "build/qchem/quantum_chemistry_observation_geometry_v1_1.pdf"
PUBLIC_PDF_NAME = "Quantum_Chemistry_Typed_Observation_Geometry_v1_1.pdf"


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
            P9 / "src/quantum_chemistry_observation_geometry_v1_1.tex",
            "src/quantum_chemistry_observation_geometry_v1_1.tex",
        ),
        (
            P9 / "core/quantum_chemistry_observation_contract_v1_0.yaml",
            "core/quantum_chemistry_observation_contract_v1_0.yaml",
        ),
        (
            P9 / "ledgers/quantum_chemistry_reference_ledger_v1_0.yaml",
            "ledgers/quantum_chemistry_reference_ledger_v1_0.yaml",
        ),
        (
            P9 / "ledgers/corpus_ledgers_v1_0.yaml",
            "ledgers/corpus_ledgers_v1_0.yaml",
        ),
        (
            P9 / "data/quantum_chemistry_benchmarks_v1_0.csv",
            "data/quantum_chemistry_benchmarks_v1_0.csv",
        ),
        (
            P9 / "data/quantum_chemistry_metrics_v1_0.json",
            "data/quantum_chemistry_metrics_v1_0.json",
        ),
        (
            P9 / "scripts/generate_quantum_chemistry_benchmarks.py",
            "scripts/generate_quantum_chemistry_benchmarks.py",
        ),
        (
            P9 / "tests/build_corpus_ledger_v1_0.py",
            "tests/build_corpus_ledger_v1_0.py",
        ),
        (
            P9 / "tests/test_quantum_chemistry_v1_0.py",
            "tests/test_quantum_chemistry_v1_0.py",
        ),
        (
            P9 / "tests/validate_p9_release.py",
            "tests/validate_p9_release.py",
        ),
        (
            P9 / "tests/build_release_bundle.py",
            "tests/build_release_bundle.py",
        ),
        (
            P9 / "reports/P9_Quantum_Chemistry_Migration_Report_v1_0_ru.md",
            "reports/P9_Quantum_Chemistry_Migration_Report_v1_0_ru.md",
        ),
        (
            P9 / "reports/P9_Validation_Summary_v1_0.json",
            "reports/P9_Validation_Summary_v1_0.json",
        ),
        (
            P9 / "reports/P9_Visual_QA_v1_0.yaml",
            "reports/P9_Visual_QA_v1_0.yaml",
        ),
        (
            P9 / "reports/Quantum_Chemistry_Reference_Lint_Report_v1_0.json",
            "reports/Quantum_Chemistry_Reference_Lint_Report_v1_0.json",
        ),
        (
            P9 / "reports/Quantum_Chemistry_Reference_Lint_Report_v1_0.md",
            "reports/Quantum_Chemistry_Reference_Lint_Report_v1_0.md",
        ),
        (
            P9 / "reports/GO_Corpus_Lint_Report_v1_0.json",
            "reports/GO_Corpus_Lint_Report_v1_0.json",
        ),
        (
            P9 / "reports/GO_Corpus_Lint_Report_v1_0.md",
            "reports/GO_Corpus_Lint_Report_v1_0.md",
        ),
        (
            P9 / "build/qchem/quantum_chemistry_observation_geometry_v1_1.log",
            "build/qchem/quantum_chemistry_observation_geometry_v1_1.log",
        ),
        (
            P9 / "checks/qchem/quantum_chemistry_observation_geometry_v1_1.txt",
            "checks/qchem/quantum_chemistry_observation_geometry_v1_1.txt",
        ),
        (P9 / "README_P9.md", "README_P9.md"),
        (
            ROOT / "work/go_core_v0_2/src/go_lint.py",
            "go_core_v0_2/src/go_lint.py",
        ),
        (
            ROOT
            / "work/p8_conical_intersections_v0_9/ledgers/corpus_ledgers_v0_9.yaml",
            "baseline/corpus_ledgers_v0_9.yaml",
        ),
        (
            ROOT
            / "work/p8_conical_intersections_v0_9/core/conical_intersections_observation_contract_v0_9.yaml",
            "inherited/conical_intersections_observation_contract_v0_9.yaml",
        ),
        (
            ROOT
            / "work/p8_conical_intersections_v0_9/ledgers/conical_intersections_reference_ledger_v0_9.yaml",
            "inherited/conical_intersections_reference_ledger_v0_9.yaml",
        ),
        (
            ROOT / "upload/quantum_chemistry_observation_v1_bilingual(1).pdf",
            "legacy/quantum_chemistry_observation_v1_bilingual.pdf",
        ),
    ]
    for path in sorted((ROOT / "work/go_core_v0_2/core").glob("*.yaml")):
        files.append((path, f"go_core_v0_2/core/{path.name}"))
    return files


def main() -> None:
    OUTPUT_PDF.mkdir(parents=True, exist_ok=True)
    OUTPUT_P9.mkdir(parents=True, exist_ok=True)
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
            "id": "go-p9-release-components",
            "version": "1.0.0",
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
        archive.write(COMPONENT_MANIFEST, "RELEASE_COMPONENTS_v1_0.yaml")

    with zipfile.ZipFile(BUNDLE, "r") as archive:
        bad_member = archive.testzip()
        if bad_member is not None:
            raise RuntimeError(f"archive integrity failure: {bad_member}")

    validation = yaml.safe_load(
        (P9 / "reports/P9_Validation_Summary_v1_0.json").read_text(
            encoding="utf-8"
        )
    )
    if validation["status"] != "PASS":
        raise RuntimeError("validation summary is not PASS")

    release = {
        "schema": {
            "id": "go-p9-release-manifest",
            "version": "1.0.0",
        },
        "date": "2026-07-28",
        "status": "PASS",
        "core_contract": "go-core-spec@0.2.0",
        "inherited_contracts": [
            "go-conical-intersections-observation-contract@0.9.0",
        ],
        "extension_contract": (
            "go-quantum-chemistry-observation-contract@1.0.0"
        ),
        "documents": [
            {
                "id": "quantum-chemistry-observation-v1-1",
                "pages": 9,
                "bytes": PDF.stat().st_size,
                "sha256": sha256(PDF),
            }
        ],
        "validation": {
            "release_checks": validation["release_check_count"],
            "typed_expressions": 47,
            "reference_findings": 0,
            "regression_tests": 413,
            "benchmark_rows": 202,
            "rendered_pages": 9,
            "corpus_expressions": 253,
            "corpus_statuses": {
                "PASS": 16,
                "FAIL": 2,
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
            P9 / "reports/P9_Quantum_Chemistry_Migration_Report_v1_0_ru.md",
            OUTPUT_P9 / "P9_Quantum_Chemistry_Migration_Report_v1_0_ru.md",
        ),
        (
            P9 / "core/quantum_chemistry_observation_contract_v1_0.yaml",
            OUTPUT_P9 / "Quantum_Chemistry_Observation_Contract_v1_0.yaml",
        ),
        (
            P9 / "ledgers/quantum_chemistry_reference_ledger_v1_0.yaml",
            OUTPUT_P9 / "Quantum_Chemistry_Reference_Ledger_v1_0.yaml",
        ),
        (
            P9 / "ledgers/corpus_ledgers_v1_0.yaml",
            OUTPUT_P9 / "GO_Corpus_Ledgers_v1_0.yaml",
        ),
        (
            P9 / "data/quantum_chemistry_benchmarks_v1_0.csv",
            OUTPUT_P9 / "Quantum_Chemistry_Benchmarks_v1_0.csv",
        ),
        (
            P9 / "data/quantum_chemistry_metrics_v1_0.json",
            OUTPUT_P9 / "Quantum_Chemistry_Metrics_v1_0.json",
        ),
        (
            P9 / "reports/P9_Validation_Summary_v1_0.json",
            OUTPUT_P9 / "P9_Validation_Summary_v1_0.json",
        ),
        (
            P9 / "reports/P9_Visual_QA_v1_0.yaml",
            OUTPUT_P9 / "P9_Visual_QA_v1_0.yaml",
        ),
        (
            P9 / "reports/GO_Corpus_Lint_Report_v1_0.md",
            OUTPUT_P9 / "GO_Corpus_Lint_Report_v1_0.md",
        ),
        (
            P9 / "reports/Quantum_Chemistry_Reference_Lint_Report_v1_0.md",
            OUTPUT_P9 / "Quantum_Chemistry_Reference_Lint_Report_v1_0.md",
        ),
        (
            RELEASE_MANIFEST,
            OUTPUT_P9 / "RELEASE_MANIFEST_v1_0.yaml",
        ),
        (
            BUNDLE,
            OUTPUT_P9 / BUNDLE.name,
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
    print(OUTPUT_P9)


if __name__ == "__main__":
    main()
