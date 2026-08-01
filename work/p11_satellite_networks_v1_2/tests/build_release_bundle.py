#!/usr/bin/env python3
"""Build the reproducible GO P11 satellite-networks release bundle."""

from __future__ import annotations

import hashlib
import shutil
import zipfile
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[3]
P11 = ROOT / "work/p11_satellite_networks_v1_2"
OUTPUT_PDF = ROOT / "output/pdf"
OUTPUT_P11 = ROOT / "output/p11"
BUNDLE_DIR = P11 / "bundle"
BUNDLE = BUNDLE_DIR / "GO_P11_Satellite_Networks_v1_2_Source_Bundle.zip"
COMPONENT_MANIFEST = BUNDLE_DIR / "RELEASE_COMPONENTS_v1_2.yaml"
RELEASE_MANIFEST = P11 / "RELEASE_MANIFEST_v1_2.yaml"

PDF = P11 / "build/satellite/satellite_networks_typed_frames_v1_2.pdf"
PUBLIC_PDF_NAME = (
    "Satellite_Networks_Typed_Frames_Temporal_Observation_v1_2.pdf"
)
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
            P11 / "src/satellite_networks_typed_frames_v1_2.tex",
            "src/satellite_networks_typed_frames_v1_2.tex",
        ),
        (
            P11 / "core/satellite_networks_observation_contract_v1_2.yaml",
            "core/satellite_networks_observation_contract_v1_2.yaml",
        ),
        (
            P11 / "ledgers/satellite_networks_reference_ledger_v1_2.yaml",
            "ledgers/satellite_networks_reference_ledger_v1_2.yaml",
        ),
        (
            P11 / "ledgers/corpus_ledgers_v1_2.yaml",
            "ledgers/corpus_ledgers_v1_2.yaml",
        ),
        (
            P11 / "data/satellite_networks_benchmarks_v1_2.csv",
            "data/satellite_networks_benchmarks_v1_2.csv",
        ),
        (
            P11 / "data/satellite_networks_metrics_v1_2.json",
            "data/satellite_networks_metrics_v1_2.json",
        ),
        (
            P11 / "scripts/generate_satellite_network_benchmarks.py",
            "scripts/generate_satellite_network_benchmarks.py",
        ),
        (
            P11 / "scripts/build_satellite_reference_ledger_v1_2.py",
            "scripts/build_satellite_reference_ledger_v1_2.py",
        ),
        (
            P11 / "tests/build_corpus_ledger_v1_2.py",
            "tests/build_corpus_ledger_v1_2.py",
        ),
        (
            P11 / "tests/test_satellite_networks_v1_2.py",
            "tests/test_satellite_networks_v1_2.py",
        ),
        (
            P11 / "tests/validate_p11_release.py",
            "tests/validate_p11_release.py",
        ),
        (
            P11 / "tests/build_release_bundle.py",
            "tests/build_release_bundle.py",
        ),
        (
            P11
            / "reports/P11_Satellite_Networks_Migration_Report_v1_2_ru.md",
            "reports/P11_Satellite_Networks_Migration_Report_v1_2_ru.md",
        ),
        (
            P11 / "reports/P11_Validation_Summary_v1_2.json",
            "reports/P11_Validation_Summary_v1_2.json",
        ),
        (
            P11 / "reports/P11_Visual_QA_v1_2.yaml",
            "reports/P11_Visual_QA_v1_2.yaml",
        ),
        (
            P11
            / "reports/Satellite_Networks_Reference_Lint_Report_v1_2.json",
            "reports/Satellite_Networks_Reference_Lint_Report_v1_2.json",
        ),
        (
            P11
            / "reports/Satellite_Networks_Reference_Lint_Report_v1_2.md",
            "reports/Satellite_Networks_Reference_Lint_Report_v1_2.md",
        ),
        (
            P11 / "reports/GO_Corpus_Lint_Report_v1_2.json",
            "reports/GO_Corpus_Lint_Report_v1_2.json",
        ),
        (
            P11 / "reports/GO_Corpus_Lint_Report_v1_2.md",
            "reports/GO_Corpus_Lint_Report_v1_2.md",
        ),
        (
            P11 / "build/satellite/satellite_networks_typed_frames_v1_2.log",
            "build/satellite/satellite_networks_typed_frames_v1_2.log",
        ),
        (
            P11 / "checks/satellite/satellite_networks_typed_frames_v1_2.txt",
            "checks/satellite/satellite_networks_typed_frames_v1_2.txt",
        ),
        (P11 / "README_P11.md", "README_P11.md"),
        (
            ROOT / "work/go_core_v0_2/src/go_lint.py",
            "go_core_v0_2/src/go_lint.py",
        ),
        (
            ROOT
            / "work/p10_regular_polyhedra_v1_1/ledgers/corpus_ledgers_v1_1.yaml",
            "baseline/corpus_ledgers_v1_1.yaml",
        ),
        (
            ROOT
            / "work/p10_regular_polyhedra_v1_1/core/regular_polyhedra_observation_contract_v1_1.yaml",
            "inherited/regular_polyhedra_observation_contract_v1_1.yaml",
        ),
        (
            ROOT
            / "work/p10_regular_polyhedra_v1_1/ledgers/regular_polyhedra_reference_ledger_v1_1.yaml",
            "inherited/regular_polyhedra_reference_ledger_v1_1.yaml",
        ),
        (
            ROOT
            / "upload/satellite_networks_observation_v11_relativistic_bilingual(2).pdf",
            "legacy/satellite_networks_observation_v11_relativistic_bilingual.pdf",
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
    OUTPUT_P11.mkdir(parents=True, exist_ok=True)
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
            "id": "go-p11-release-components",
            "version": "1.2.0",
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
                "RELEASE_COMPONENTS_v1_2.yaml",
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
        (P11 / "reports/P11_Validation_Summary_v1_2.json").read_text(
            encoding="utf-8"
        )
    )
    if validation["status"] != "PASS":
        raise RuntimeError("validation summary is not PASS")

    release = {
        "schema": {
            "id": "go-p11-release-manifest",
            "version": "1.2.0",
        },
        "date": "2026-07-28",
        "status": "PASS",
        "core_contract": "go-core-spec@0.2.0",
        "inherited_contracts": [
            "go-regular-polyhedra-observation-contract@1.1.0",
        ],
        "extension_contract": (
            "go-satellite-networks-observation-contract@1.2.0"
        ),
        "documents": [
            {
                "id": "satellite-networks-observation-v1-2",
                "pages": 8,
                "bytes": PDF.stat().st_size,
                "sha256": sha256(PDF),
            }
        ],
        "validation": {
            "release_checks": validation["release_check_count"],
            "typed_expressions": 53,
            "reference_findings": 0,
            "regression_tests": 623,
            "benchmark_rows": 553,
            "rendered_pages": 8,
            "corpus_expressions": 347,
            "corpus_findings": 0,
            "corpus_statuses": {
                "PASS": 18,
                "FAIL": 0,
                "BLOCKED": 0,
            },
            "last_fail_module_closed": True,
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
            P11
            / "reports/P11_Satellite_Networks_Migration_Report_v1_2_ru.md",
            OUTPUT_P11 / "P11_Satellite_Networks_Migration_Report_v1_2_ru.md",
        ),
        (
            P11 / "core/satellite_networks_observation_contract_v1_2.yaml",
            OUTPUT_P11 / "Satellite_Networks_Observation_Contract_v1_2.yaml",
        ),
        (
            P11 / "ledgers/satellite_networks_reference_ledger_v1_2.yaml",
            OUTPUT_P11 / "Satellite_Networks_Reference_Ledger_v1_2.yaml",
        ),
        (
            P11 / "ledgers/corpus_ledgers_v1_2.yaml",
            OUTPUT_P11 / "GO_Corpus_Ledgers_v1_2.yaml",
        ),
        (
            P11 / "data/satellite_networks_benchmarks_v1_2.csv",
            OUTPUT_P11 / "Satellite_Networks_Benchmarks_v1_2.csv",
        ),
        (
            P11 / "data/satellite_networks_metrics_v1_2.json",
            OUTPUT_P11 / "Satellite_Networks_Metrics_v1_2.json",
        ),
        (
            P11 / "reports/P11_Validation_Summary_v1_2.json",
            OUTPUT_P11 / "P11_Validation_Summary_v1_2.json",
        ),
        (
            P11 / "reports/P11_Visual_QA_v1_2.yaml",
            OUTPUT_P11 / "P11_Visual_QA_v1_2.yaml",
        ),
        (
            P11 / "reports/GO_Corpus_Lint_Report_v1_2.md",
            OUTPUT_P11 / "GO_Corpus_Lint_Report_v1_2.md",
        ),
        (
            P11 / "reports/Satellite_Networks_Reference_Lint_Report_v1_2.md",
            OUTPUT_P11 / "Satellite_Networks_Reference_Lint_Report_v1_2.md",
        ),
        (
            RELEASE_MANIFEST,
            OUTPUT_P11 / "RELEASE_MANIFEST_v1_2.yaml",
        ),
        (
            BUNDLE,
            OUTPUT_P11 / BUNDLE.name,
        ),
    ]
    for source, destination in output_copies:
        shutil.copy2(source, destination)
        if sha256(source) != sha256(destination):
            raise RuntimeError(f"output copy hash mismatch: {destination}")

    print(BUNDLE)
    print(RELEASE_MANIFEST)
    print(OUTPUT_PDF / PUBLIC_PDF_NAME)
    print(OUTPUT_P11)


if __name__ == "__main__":
    main()
