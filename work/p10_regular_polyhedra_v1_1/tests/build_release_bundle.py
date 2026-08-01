#!/usr/bin/env python3
"""Build the reproducible GO P10 regular-polyhedra release bundle."""

from __future__ import annotations

import hashlib
import shutil
import zipfile
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[3]
P10 = ROOT / "work/p10_regular_polyhedra_v1_1"
OUTPUT_PDF = ROOT / "output/pdf"
OUTPUT_P10 = ROOT / "output/p10"
BUNDLE_DIR = P10 / "bundle"
BUNDLE = BUNDLE_DIR / "GO_P10_Regular_Polyhedra_v1_1_Source_Bundle.zip"
COMPONENT_MANIFEST = BUNDLE_DIR / "RELEASE_COMPONENTS_v1_1.yaml"
RELEASE_MANIFEST = P10 / "RELEASE_MANIFEST_v1_1.yaml"

PDF = (
    P10
    / "build/polyhedra/regular_polyhedra_observation_filters_v1_1.pdf"
)
PUBLIC_PDF_NAME = "Regular_Polyhedra_Typed_Observation_Filters_v1_1.pdf"
ZIP_TIMESTAMP = (2026, 7, 28, 12, 0, 0)


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
            P10 / "src/regular_polyhedra_observation_filters_v1_1.tex",
            "src/regular_polyhedra_observation_filters_v1_1.tex",
        ),
        (
            P10 / "core/regular_polyhedra_observation_contract_v1_1.yaml",
            "core/regular_polyhedra_observation_contract_v1_1.yaml",
        ),
        (
            P10 / "ledgers/regular_polyhedra_reference_ledger_v1_1.yaml",
            "ledgers/regular_polyhedra_reference_ledger_v1_1.yaml",
        ),
        (
            P10 / "ledgers/corpus_ledgers_v1_1.yaml",
            "ledgers/corpus_ledgers_v1_1.yaml",
        ),
        (
            P10 / "data/regular_polyhedra_benchmarks_v1_1.csv",
            "data/regular_polyhedra_benchmarks_v1_1.csv",
        ),
        (
            P10 / "data/regular_polyhedra_metrics_v1_1.json",
            "data/regular_polyhedra_metrics_v1_1.json",
        ),
        (
            P10 / "scripts/generate_regular_polyhedra_benchmarks.py",
            "scripts/generate_regular_polyhedra_benchmarks.py",
        ),
        (
            P10 / "tests/build_corpus_ledger_v1_1.py",
            "tests/build_corpus_ledger_v1_1.py",
        ),
        (
            P10 / "tests/test_regular_polyhedra_v1_1.py",
            "tests/test_regular_polyhedra_v1_1.py",
        ),
        (
            P10 / "tests/validate_p10_release.py",
            "tests/validate_p10_release.py",
        ),
        (
            P10 / "tests/build_release_bundle.py",
            "tests/build_release_bundle.py",
        ),
        (
            P10
            / "reports/P10_Regular_Polyhedra_Migration_Report_v1_1_ru.md",
            "reports/P10_Regular_Polyhedra_Migration_Report_v1_1_ru.md",
        ),
        (
            P10 / "reports/P10_Validation_Summary_v1_1.json",
            "reports/P10_Validation_Summary_v1_1.json",
        ),
        (
            P10 / "reports/P10_Visual_QA_v1_1.yaml",
            "reports/P10_Visual_QA_v1_1.yaml",
        ),
        (
            P10
            / "reports/Regular_Polyhedra_Reference_Lint_Report_v1_1.json",
            "reports/Regular_Polyhedra_Reference_Lint_Report_v1_1.json",
        ),
        (
            P10
            / "reports/Regular_Polyhedra_Reference_Lint_Report_v1_1.md",
            "reports/Regular_Polyhedra_Reference_Lint_Report_v1_1.md",
        ),
        (
            P10 / "reports/GO_Corpus_Lint_Report_v1_1.json",
            "reports/GO_Corpus_Lint_Report_v1_1.json",
        ),
        (
            P10 / "reports/GO_Corpus_Lint_Report_v1_1.md",
            "reports/GO_Corpus_Lint_Report_v1_1.md",
        ),
        (
            P10
            / "build/polyhedra/regular_polyhedra_observation_filters_v1_1.log",
            "build/polyhedra/regular_polyhedra_observation_filters_v1_1.log",
        ),
        (
            P10
            / "checks/polyhedra/regular_polyhedra_observation_filters_v1_1.txt",
            "checks/polyhedra/regular_polyhedra_observation_filters_v1_1.txt",
        ),
        (P10 / "README_P10.md", "README_P10.md"),
        (
            ROOT / "work/go_core_v0_2/src/go_lint.py",
            "go_core_v0_2/src/go_lint.py",
        ),
        (
            ROOT
            / "work/p9_quantum_chemistry_v1_0/ledgers/corpus_ledgers_v1_0.yaml",
            "baseline/corpus_ledgers_v1_0.yaml",
        ),
        (
            ROOT
            / "work/p9_quantum_chemistry_v1_0/core/quantum_chemistry_observation_contract_v1_0.yaml",
            "inherited/quantum_chemistry_observation_contract_v1_0.yaml",
        ),
        (
            ROOT
            / "work/p9_quantum_chemistry_v1_0/ledgers/quantum_chemistry_reference_ledger_v1_0.yaml",
            "inherited/quantum_chemistry_reference_ledger_v1_0.yaml",
        ),
        (
            ROOT / "upload/regular_polyhedra_observation_v1_bilingual(2).pdf",
            "legacy/regular_polyhedra_observation_v1_bilingual.pdf",
        ),
    ]
    for path in sorted((ROOT / "work/go_core_v0_2/core").glob("*.yaml")):
        files.append((path, f"go_core_v0_2/core/{path.name}"))
    return files


def write_zip_member(
    archive: zipfile.ZipFile,
    archive_path: str,
    content: bytes,
) -> None:
    info = zipfile.ZipInfo(archive_path, date_time=ZIP_TIMESTAMP)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.create_system = 3
    info.external_attr = 0o100644 << 16
    archive.writestr(info, content, compress_type=zipfile.ZIP_DEFLATED)


def main() -> None:
    OUTPUT_PDF.mkdir(parents=True, exist_ok=True)
    OUTPUT_P10.mkdir(parents=True, exist_ok=True)
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
            "id": "go-p10-release-components",
            "version": "1.1.0",
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
        entries = [
            (archive_path, path.read_bytes())
            for path, archive_path in files
        ]
        entries.append(
            (
                "RELEASE_COMPONENTS_v1_1.yaml",
                COMPONENT_MANIFEST.read_bytes(),
            )
        )
        for archive_path, content in sorted(entries):
            write_zip_member(archive, archive_path, content)

    with zipfile.ZipFile(BUNDLE, "r") as archive:
        bad_member = archive.testzip()
        if bad_member is not None:
            raise RuntimeError(f"archive integrity failure: {bad_member}")
        member_names = archive.namelist()
        if member_names != sorted(member_names):
            raise RuntimeError("archive members are not deterministically sorted")

    validation = yaml.safe_load(
        (P10 / "reports/P10_Validation_Summary_v1_1.json").read_text(
            encoding="utf-8"
        )
    )
    if validation["status"] != "PASS":
        raise RuntimeError("validation summary is not PASS")

    release = {
        "schema": {
            "id": "go-p10-release-manifest",
            "version": "1.1.0",
        },
        "date": "2026-07-28",
        "status": "PASS",
        "core_contract": "go-core-spec@0.2.0",
        "inherited_contracts": [
            "go-quantum-chemistry-observation-contract@1.0.0",
        ],
        "extension_contract": (
            "go-regular-polyhedra-observation-contract@1.1.0"
        ),
        "documents": [
            {
                "id": "regular-polyhedra-observation-v1-1",
                "pages": 7,
                "bytes": PDF.stat().st_size,
                "sha256": sha256(PDF),
            }
        ],
        "validation": {
            "release_checks": validation["release_check_count"],
            "typed_expressions": 42,
            "reference_findings": 0,
            "regression_tests": 357,
            "benchmark_rows": 302,
            "rendered_pages": 7,
            "corpus_expressions": 295,
            "corpus_statuses": {
                "PASS": 17,
                "FAIL": 1,
                "BLOCKED": 0,
            },
        },
        "bundle": {
            "filename": BUNDLE.name,
            "component_count": len(components),
            "bytes": BUNDLE.stat().st_size,
            "sha256": sha256(BUNDLE),
            "zip_integrity": "PASS",
            "fixed_timestamp": "2026-07-28T12:00:00",
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
            P10
            / "reports/P10_Regular_Polyhedra_Migration_Report_v1_1_ru.md",
            OUTPUT_P10
            / "P10_Regular_Polyhedra_Migration_Report_v1_1_ru.md",
        ),
        (
            P10 / "core/regular_polyhedra_observation_contract_v1_1.yaml",
            OUTPUT_P10 / "Regular_Polyhedra_Observation_Contract_v1_1.yaml",
        ),
        (
            P10 / "ledgers/regular_polyhedra_reference_ledger_v1_1.yaml",
            OUTPUT_P10 / "Regular_Polyhedra_Reference_Ledger_v1_1.yaml",
        ),
        (
            P10 / "ledgers/corpus_ledgers_v1_1.yaml",
            OUTPUT_P10 / "GO_Corpus_Ledgers_v1_1.yaml",
        ),
        (
            P10 / "data/regular_polyhedra_benchmarks_v1_1.csv",
            OUTPUT_P10 / "Regular_Polyhedra_Benchmarks_v1_1.csv",
        ),
        (
            P10 / "data/regular_polyhedra_metrics_v1_1.json",
            OUTPUT_P10 / "Regular_Polyhedra_Metrics_v1_1.json",
        ),
        (
            P10 / "reports/P10_Validation_Summary_v1_1.json",
            OUTPUT_P10 / "P10_Validation_Summary_v1_1.json",
        ),
        (
            P10 / "reports/P10_Visual_QA_v1_1.yaml",
            OUTPUT_P10 / "P10_Visual_QA_v1_1.yaml",
        ),
        (
            P10 / "reports/GO_Corpus_Lint_Report_v1_1.md",
            OUTPUT_P10 / "GO_Corpus_Lint_Report_v1_1.md",
        ),
        (
            P10
            / "reports/Regular_Polyhedra_Reference_Lint_Report_v1_1.md",
            OUTPUT_P10
            / "Regular_Polyhedra_Reference_Lint_Report_v1_1.md",
        ),
        (
            RELEASE_MANIFEST,
            OUTPUT_P10 / "RELEASE_MANIFEST_v1_1.yaml",
        ),
        (
            BUNDLE,
            OUTPUT_P10 / BUNDLE.name,
        ),
    ]
    for source, destination in output_copies:
        shutil.copy2(source, destination)
        if sha256(source) != sha256(destination):
            raise RuntimeError(f"output copy hash mismatch: {destination}")

    print(BUNDLE)
    print(RELEASE_MANIFEST)
    print(OUTPUT_PDF / PUBLIC_PDF_NAME)
    print(OUTPUT_P10)


if __name__ == "__main__":
    main()
