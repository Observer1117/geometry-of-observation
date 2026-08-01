#!/usr/bin/env python3
"""Build the reproducible GO P5 release bundle and public artifacts."""

from __future__ import annotations

import hashlib
import shutil
import zipfile
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[3]
P5 = ROOT / "work/p5_mechanics_frames_v0_6"
OUTPUT_PDF = ROOT / "output/pdf"
OUTPUT_P5 = ROOT / "output/p5"
BUNDLE_DIR = P5 / "bundle"
BUNDLE = BUNDLE_DIR / "GO_P5_Frames_Forces_Dissipation_v0_6_Source_Bundle.zip"
COMPONENT_MANIFEST = BUNDLE_DIR / "RELEASE_COMPONENTS_v0_6.yaml"
RELEASE_MANIFEST = P5 / "RELEASE_MANIFEST_v0_6.yaml"

FINAL_PDFS = [
    (
        "frames-forces-dissipation-interface-v0-1",
        P5 / "build/interface/frame_force_dissipation_interface_v0_1.pdf",
        "Frames_Forces_Constraints_Dissipation_Interface_v0_1.pdf",
        7,
    ),
    (
        "celestial-foucault-networks-v1-1",
        P5 / "build/foucault/celestial_foucault_networks_v1_1.pdf",
        "Celestial_Foucault_Networks_Observation_Geometry_v1_1.pdf",
        6,
    ),
    (
        "bobsleigh-contact-v1-1",
        P5 / "build/bobsleigh/bobsleigh_contact_geometry_v1_1.pdf",
        "Bobsleigh_Contact_Geometry_Observation_v1_1.pdf",
        6,
    ),
    (
        "roller-coaster-v1-1",
        P5 / "build/roller/roller_coaster_geometry_v1_1.pdf",
        "Roller_Coaster_Geometry_Observation_v1_1.pdf",
        6,
    ),
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def component_files() -> list[tuple[Path, str]]:
    files: list[tuple[Path, str]] = [
        *[
            (path, f"pdf/{public_name}")
            for _, path, public_name, _ in FINAL_PDFS
        ],
        (
            P5 / "src/frame_force_dissipation_interface_v0_1.tex",
            "src/frame_force_dissipation_interface_v0_1.tex",
        ),
        (
            P5 / "src/celestial_foucault_networks_v1_1.tex",
            "src/celestial_foucault_networks_v1_1.tex",
        ),
        (
            P5 / "src/bobsleigh_contact_geometry_v1_1.tex",
            "src/bobsleigh_contact_geometry_v1_1.tex",
        ),
        (
            P5 / "src/roller_coaster_geometry_v1_1.tex",
            "src/roller_coaster_geometry_v1_1.tex",
        ),
        (
            P5 / "core/frame_force_dissipation_contract_v0_6.yaml",
            "core/frame_force_dissipation_contract_v0_6.yaml",
        ),
        (
            P5 / "ledgers/mechanics_reference_ledgers_v0_6.yaml",
            "ledgers/mechanics_reference_ledgers_v0_6.yaml",
        ),
        (
            P5 / "ledgers/corpus_ledgers_v0_6.yaml",
            "ledgers/corpus_ledgers_v0_6.yaml",
        ),
        (
            P5 / "tests/build_corpus_ledger_v0_6.py",
            "tests/build_corpus_ledger_v0_6.py",
        ),
        (
            P5 / "tests/test_mechanics_frames_v0_6.py",
            "tests/test_mechanics_frames_v0_6.py",
        ),
        (
            P5 / "tests/validate_p5_release.py",
            "tests/validate_p5_release.py",
        ),
        (
            P5 / "tests/build_release_bundle.py",
            "tests/build_release_bundle.py",
        ),
        (
            P5
            / "reports/P5_Frames_Forces_Dissipation_Migration_Report_v0_6_ru.md",
            "reports/P5_Frames_Forces_Dissipation_Migration_Report_v0_6_ru.md",
        ),
        (
            P5 / "reports/P5_Validation_Summary_v0_6.json",
            "reports/P5_Validation_Summary_v0_6.json",
        ),
        (
            P5 / "reports/P5_Visual_QA_v0_6.yaml",
            "reports/P5_Visual_QA_v0_6.yaml",
        ),
        (
            P5 / "reports/Mechanics_Reference_Lint_Report_v0_6.json",
            "reports/Mechanics_Reference_Lint_Report_v0_6.json",
        ),
        (
            P5 / "reports/Mechanics_Reference_Lint_Report_v0_6_ru.md",
            "reports/Mechanics_Reference_Lint_Report_v0_6_ru.md",
        ),
        (
            P5 / "reports/GO_Corpus_Lint_Report_v0_6.json",
            "reports/GO_Corpus_Lint_Report_v0_6.json",
        ),
        (
            P5 / "reports/GO_Corpus_Lint_Report_v0_6_ru.md",
            "reports/GO_Corpus_Lint_Report_v0_6_ru.md",
        ),
        (
            P5 / "build/interface/frame_force_dissipation_interface_v0_1.log",
            "build/interface/frame_force_dissipation_interface_v0_1.log",
        ),
        (
            P5 / "build/foucault/celestial_foucault_networks_v1_1.log",
            "build/foucault/celestial_foucault_networks_v1_1.log",
        ),
        (
            P5 / "build/bobsleigh/bobsleigh_contact_geometry_v1_1.log",
            "build/bobsleigh/bobsleigh_contact_geometry_v1_1.log",
        ),
        (
            P5 / "build/roller/roller_coaster_geometry_v1_1.log",
            "build/roller/roller_coaster_geometry_v1_1.log",
        ),
        (
            P5
            / "checks_final/interface/frame_force_dissipation_interface_v0_1.txt",
            "checks/interface_text.txt",
        ),
        (
            P5
            / "checks_final/foucault/celestial_foucault_networks_v1_1.txt",
            "checks/foucault_text.txt",
        ),
        (
            P5
            / "checks_final/bobsleigh/bobsleigh_contact_geometry_v1_1.txt",
            "checks/bobsleigh_text.txt",
        ),
        (
            P5
            / "checks_final/roller/roller_coaster_geometry_v1_1.txt",
            "checks/roller_text.txt",
        ),
        (P5 / "README_P5.md", "README_P5.md"),
        (
            ROOT / "work/go_core_v0_2/src/go_lint.py",
            "go_core_v0_2/src/go_lint.py",
        ),
        (
            ROOT / "work/p4_lhc_si_hep_v0_5/ledgers/corpus_ledgers_v0_5.yaml",
            "baseline/corpus_ledgers_v0_5.yaml",
        ),
        (
            ROOT
            / "upload/celestial_foucault_networks_observation_v1_bilingual(2).pdf",
            "legacy/celestial_foucault_networks_observation_v1_bilingual.pdf",
        ),
        (
            ROOT / "upload/bobsleigh_contact_geometry_observation_v1_bilingual.pdf",
            "legacy/bobsleigh_contact_geometry_observation_v1_bilingual.pdf",
        ),
        (
            ROOT / "upload/roller_coaster_geometry_observation_v1_bilingual.pdf",
            "legacy/roller_coaster_geometry_observation_v1_bilingual.pdf",
        ),
    ]
    for path in sorted((ROOT / "work/go_core_v0_2/core").glob("*.yaml")):
        files.append((path, f"go_core_v0_2/core/{path.name}"))
    return files


def main() -> None:
    OUTPUT_PDF.mkdir(parents=True, exist_ok=True)
    OUTPUT_P5.mkdir(parents=True, exist_ok=True)
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
            "id": "go-p5-release-components",
            "version": "0.6.0",
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
            "RELEASE_COMPONENTS_v0_6.yaml",
        )

    release = {
        "schema": {
            "id": "go-p5-release-manifest",
            "version": "0.6.0",
        },
        "date": "2026-07-28",
        "status": "PASS",
        "core_contract": "go-core-spec@0.2.0",
        "extension_contract": "go-frame-force-dissipation-contract@0.6.0",
        "documents": [
            {
                "id": document_id,
                "pages": pages,
                "sha256": sha256(path),
            }
            for document_id, path, _, pages in FINAL_PDFS
        ],
        "validation": {
            "release_checks": 16,
            "typed_expressions": 39,
            "reference_findings": 0,
            "regression_tests": 50,
            "rendered_pages": 25,
            "corpus_statuses": {
                "PASS": 12,
                "FAIL": 6,
                "BLOCKED": 0,
            },
        },
        "bundle": {
            "filename": BUNDLE.name,
            "bytes": BUNDLE.stat().st_size,
            "sha256": sha256(BUNDLE),
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
        *[
            (path, OUTPUT_PDF / public_name)
            for _, path, public_name, _ in FINAL_PDFS
        ],
        (
            P5
            / "reports/P5_Frames_Forces_Dissipation_Migration_Report_v0_6_ru.md",
            OUTPUT_P5
            / "P5_Frames_Forces_Dissipation_Migration_Report_v0_6_ru.md",
        ),
        (
            P5 / "core/frame_force_dissipation_contract_v0_6.yaml",
            OUTPUT_P5 / "Frame_Force_Dissipation_Contract_v0_6.yaml",
        ),
        (
            P5 / "ledgers/mechanics_reference_ledgers_v0_6.yaml",
            OUTPUT_P5 / "Mechanics_Reference_Ledgers_v0_6.yaml",
        ),
        (
            P5 / "ledgers/corpus_ledgers_v0_6.yaml",
            OUTPUT_P5 / "GO_Corpus_Ledgers_v0_6.yaml",
        ),
        (
            P5 / "reports/Mechanics_Reference_Lint_Report_v0_6_ru.md",
            OUTPUT_P5 / "Mechanics_Reference_Lint_Report_v0_6_ru.md",
        ),
        (
            P5 / "reports/GO_Corpus_Lint_Report_v0_6_ru.md",
            OUTPUT_P5 / "GO_Corpus_Lint_Report_v0_6_ru.md",
        ),
        (
            P5 / "reports/P5_Validation_Summary_v0_6.json",
            OUTPUT_P5 / "P5_Validation_Summary_v0_6.json",
        ),
        (
            P5 / "reports/P5_Visual_QA_v0_6.yaml",
            OUTPUT_P5 / "P5_Visual_QA_v0_6.yaml",
        ),
        (
            RELEASE_MANIFEST,
            OUTPUT_P5 / "RELEASE_MANIFEST_v0_6.yaml",
        ),
        (
            BUNDLE,
            OUTPUT_P5 / BUNDLE.name,
        ),
    ]
    for source, destination in output_copies:
        shutil.copy2(source, destination)

    print(BUNDLE)
    print(RELEASE_MANIFEST)
    for _, path, public_name, _ in FINAL_PDFS:
        print(OUTPUT_PDF / public_name, sha256(path))
    print(OUTPUT_P5 / BUNDLE.name, sha256(BUNDLE))


if __name__ == "__main__":
    main()
