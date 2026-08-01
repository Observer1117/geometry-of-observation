#!/usr/bin/env python3
"""Build the deterministic P12 frozen-corpus release bundle."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import zipfile
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[3]
P12 = ROOT / "work/p12_corpus_master_v1_3"
OUTPUT_PDF = ROOT / "output/pdf"
OUTPUT_P12 = ROOT / "output/p12"
BUNDLE_DIR = P12 / "bundle"
BUNDLE = BUNDLE_DIR / "GO_P12_Corpus_Master_v1_3_Release_Bundle.zip"
COMPONENT_MANIFEST = BUNDLE_DIR / "RELEASE_COMPONENTS_v1_3.yaml"
RELEASE_MANIFEST = P12 / "RELEASE_MANIFEST_v1_3.yaml"
MASTER = P12 / "build/master/Geometry_of_Observation_Corpus_Master_v1_3.pdf"
FRONT = (
    P12
    / "build/frontmatter/"
    "geometry_of_observation_corpus_master_frontmatter_v1_3.pdf"
)
FREEZE = P12 / "ledgers/go_corpus_freeze_ledger_v1_3.yaml"
SUMMARY = P12 / "reports/P12_Validation_Summary_v1_3.json"
CHECKSUMS = P12 / "SHA256SUMS_v1_3.txt"
ZIP_TIMESTAMP = (2026, 7, 28, 12, 0, 0)

PHASE_BUNDLES = [
    (
        ROOT
        / "work/p1_info_metric_v0_2/bundle/"
        "GO_P1_Information_Metric_v0_2_Source_Bundle.zip"
    ),
    (
        ROOT
        / "work/p2_distance_scale_v0_3/bundle/"
        "GO_P2_Distance_Scale_Mandelbrot_v0_3_Source_Bundle.zip"
    ),
    (
        ROOT
        / "work/p3_planck_cosmos_v0_4/bundle/"
        "GO_P3_Planck_Cosmos_v0_4_Source_Bundle.zip"
    ),
    (
        ROOT
        / "work/p4_lhc_si_hep_v0_5/bundle/"
        "GO_P4_LHC_SI_HEP_v0_5_Source_Bundle.zip"
    ),
    (
        ROOT
        / "work/p5_mechanics_frames_v0_6/bundle/"
        "GO_P5_Frames_Forces_Dissipation_v0_6_Source_Bundle.zip"
    ),
    (
        ROOT
        / "work/p6_gear_contact_v0_7/bundle/"
        "GO_P6_Gear_Contact_v0_7_Source_Bundle.zip"
    ),
    (
        ROOT
        / "work/p7_billiards_v0_8/bundle/"
        "GO_P7_Billiards_v0_8_Source_Bundle.zip"
    ),
    (
        ROOT
        / "work/p8_conical_intersections_v0_9/bundle/"
        "GO_P8_Conical_Intersections_v0_9_Source_Bundle.zip"
    ),
    (
        ROOT
        / "work/p9_quantum_chemistry_v1_0/bundle/"
        "GO_P9_Quantum_Chemistry_v1_0_Source_Bundle.zip"
    ),
    (
        ROOT
        / "work/p10_regular_polyhedra_v1_1/bundle/"
        "GO_P10_Regular_Polyhedra_v1_1_Source_Bundle.zip"
    ),
    (
        ROOT
        / "work/p11_satellite_networks_v1_2/bundle/"
        "GO_P11_Satellite_Networks_v1_2_Source_Bundle.zip"
    ),
]

P12_STATIC_FILES = [
    P12 / "README.md",
    P12 / "CHANGELOG.md",
    P12 / "LICENSE.md",
    P12 / "core/go_corpus_freeze_contract_v1_3.yaml",
    P12 / "ledgers/go_corpus_dependencies_v1_3.yaml",
    P12 / "ledgers/go_corpus_freeze_ledger_v1_3.yaml",
    P12 / "ledgers/MASTER_PAGE_MAP_v1_3.json",
    P12 / "ledgers/MASTER_PAGE_MAP_v1_3.csv",
    P12 / "metadata/CITATION.cff",
    P12 / "metadata/.zenodo.json",
    P12 / "metadata/OSF_RELEASE_METADATA_v1_3.yaml",
    P12 / "reports/P12_Corpus_Freeze_Report_v1_3_ru.md",
    P12 / "reports/P12_Cross_Module_Audit_v1_3.md",
    P12 / "reports/P12_Validation_Summary_v1_3.json",
    P12 / "reports/P12_Visual_QA_v1_3.yaml",
    P12 / "scripts/build_p12_master.py",
    P12 / "src/geometry_of_observation_corpus_master_frontmatter_v1_3.tex",
    P12 / "tests/test_p12_corpus_master_v1_3.py",
    P12 / "tests/validate_p12_release.py",
    P12 / "tests/build_release_bundle.py",
    P12 / "generated/module_catalog_v1_3.tex",
    P12 / "generated/dependency_table_v1_3.tex",
    P12 / "generated/freeze_macros_v1_3.tex",
    P12
    / "build/frontmatter/"
    "geometry_of_observation_corpus_master_frontmatter_v1_3.log",
    FRONT,
    MASTER,
    CHECKSUMS,
]

VISUAL_EVIDENCE = [
    P12 / "render/frontmatter/contact_sheet.png",
    P12 / "render/master/contact_sheet_1.png",
    P12 / "render/master/contact_sheet_2.png",
    P12 / "render/master/contact_sheet_3.png",
    P12 / "render/master/contact_sheet_4.png",
    P12 / "render/master/contact_sheet_5.png",
    P12 / "render/master/contact_sheet_6.jpg",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as stream:
        data = yaml.safe_load(stream)
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected a YAML mapping")
    return data


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected a JSON object")
    return data


def repository_relative(path: Path) -> str:
    return str(path.relative_to(ROOT))


def checksum_targets() -> list[Path]:
    targets: list[Path] = []
    for line in CHECKSUMS.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        _, path_text = line.split("  ", 1)
        targets.append(ROOT / path_text)
    return targets


def component_files() -> list[tuple[Path, str, str]]:
    """Return source path, archive path, and component role."""
    entries: dict[str, tuple[Path, str, str]] = {}

    def add(path: Path, archive_path: str, role: str) -> None:
        normalized = archive_path.replace("\\", "/")
        existing = entries.get(normalized)
        candidate = (path, normalized, role)
        if existing is not None and existing[0] != path:
            raise RuntimeError(f"archive path collision: {normalized}")
        entries[normalized] = candidate

    for path in checksum_targets():
        add(path, repository_relative(path), "frozen_checksum_target")
    for path in P12_STATIC_FILES:
        add(path, repository_relative(path), "p12_release_file")
    for path in VISUAL_EVIDENCE:
        add(path, repository_relative(path), "visual_qa_evidence")
    for index, path in enumerate(PHASE_BUNDLES, start=1):
        add(
            path,
            f"inherited_phase_bundles/P{index:02d}/{path.name}",
            "inherited_phase_source_bundle",
        )
    return [entries[key] for key in sorted(entries)]


def write_zip_member(
    archive: zipfile.ZipFile,
    archive_path: str,
    content: bytes,
) -> None:
    info = zipfile.ZipInfo(archive_path, date_time=ZIP_TIMESTAMP)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.create_system = 3
    info.external_attr = 0o100644 << 16
    archive.writestr(
        info,
        content,
        compress_type=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    )


def validate_inputs(files: list[tuple[Path, str, str]]) -> None:
    missing = [
        repository_relative(path)
        for path, _, _ in files
        if not path.is_file()
    ]
    if missing:
        raise FileNotFoundError(
            "Missing P12 release components:\n" + "\n".join(missing)
        )
    summary = load_json(SUMMARY)
    if summary.get("status") != "PASS":
        raise RuntimeError("P12 validation summary is not PASS")
    freeze = load_yaml(FREEZE)
    totals = freeze["corpus_totals"]
    if (
        totals["modules"] != 18
        or totals["master_pages"] != 166
        or totals["expressions"] != 347
        or totals["findings"] != 0
    ):
        raise RuntimeError("freeze totals do not match the P12 release contract")
    for phase_bundle in PHASE_BUNDLES:
        with zipfile.ZipFile(phase_bundle, "r") as archive:
            bad_member = archive.testzip()
            if bad_member is not None:
                raise RuntimeError(
                    f"inherited phase bundle failed ZIP test: "
                    f"{phase_bundle.name}:{bad_member}"
                )


def write_component_manifest(
    files: list[tuple[Path, str, str]],
) -> dict[str, Any]:
    components = [
        {
            "archive_path": archive_path,
            "source_path": repository_relative(path),
            "role": role,
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
        }
        for path, archive_path, role in files
    ]
    payload = {
        "schema": {
            "id": "go-p12-release-components",
            "version": "1.3.0",
        },
        "date": "2026-07-28",
        "release": "geometry-of-observation-corpus-master-v1-3",
        "component_count": len(components),
        "component_bytes": sum(item["bytes"] for item in components),
        "components": components,
    }
    COMPONENT_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    with COMPONENT_MANIFEST.open("w", encoding="utf-8") as stream:
        yaml.safe_dump(
            payload,
            stream,
            sort_keys=False,
            allow_unicode=True,
            width=100,
        )
    return payload


def build_bundle(files: list[tuple[Path, str, str]]) -> None:
    temporary = BUNDLE.with_suffix(".tmp.zip")
    temporary.unlink(missing_ok=True)
    entries = [
        (archive_path, path.read_bytes())
        for path, archive_path, _ in files
    ]
    entries.append(
        ("RELEASE_COMPONENTS_v1_3.yaml", COMPONENT_MANIFEST.read_bytes())
    )
    with zipfile.ZipFile(
        temporary,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
        strict_timestamps=True,
    ) as archive:
        for archive_path, content in sorted(entries):
            write_zip_member(archive, archive_path, content)
    with temporary.open("rb") as stream:
        os.fsync(stream.fileno())
    with zipfile.ZipFile(temporary, "r") as archive:
        bad_member = archive.testzip()
        names = archive.namelist()
        timestamps = {info.date_time for info in archive.infolist()}
        if bad_member is not None:
            raise RuntimeError(f"archive integrity failure: {bad_member}")
        if names != sorted(names):
            raise RuntimeError("archive members are not sorted")
        if timestamps != {ZIP_TIMESTAMP}:
            raise RuntimeError(f"archive timestamp mismatch: {timestamps}")
        internal = yaml.safe_load(
            archive.read("RELEASE_COMPONENTS_v1_3.yaml")
        )
        if (
            not isinstance(internal, dict)
            or internal.get("schema", {}).get("id")
            != "go-p12-release-components"
        ):
            raise RuntimeError("invalid internal component manifest")
    os.replace(temporary, BUNDLE)


def write_release_manifest(component_manifest: dict[str, Any]) -> None:
    summary = load_json(SUMMARY)
    freeze = load_yaml(FREEZE)
    totals = freeze["corpus_totals"]
    release = {
        "schema": {
            "id": "go-p12-master-release-manifest",
            "version": "1.3.0",
        },
        "date": "2026-07-28",
        "status": "PASS",
        "release_identity": {
            "id": "geometry-of-observation-corpus-master-v1-3",
            "title": freeze["release_identity"]["title"],
            "version": "1.3.0",
            "author": "Stassis Stashkevichyus",
            "orcid": "https://orcid.org/0009-0000-2294-705X",
            "license": "CC-BY-NC-ND-4.0",
            "doi": None,
        },
        "core_contract": "go-core-spec@0.2.0",
        "baseline": freeze["baseline"],
        "master": {
            "filename": MASTER.name,
            "pages": totals["master_pages"],
            "front_matter_pages": totals["front_matter_pages"],
            "component_pages": totals["component_pages"],
            "bytes": MASTER.stat().st_size,
            "sha256": sha256(MASTER),
        },
        "corpus": {
            "modules": totals["modules"],
            "maps": totals["maps"],
            "symbols": totals["symbols"],
            "quantities": totals["quantities"],
            "typed_expressions": totals["expressions"],
            "invariants": totals["invariants"],
            "claims": totals["claims"],
            "findings": totals["findings"],
            "statuses": totals["corpus_statuses"],
        },
        "dependency_graph": {
            "nodes": summary["dependency_nodes"],
            "edges": summary["dependency_edges"],
            "acyclic": True,
            "contextual_relations_excluded": 3,
        },
        "validation": {
            "status": summary["status"],
            "release_checks": summary["release_check_count"],
            "p12_regression_tests": summary["regression_tests"],
            "phase_validators": summary["phase_validators"],
            "component_page_equivalence_checks": totals["component_pages"],
            "independently_rendered_master_pages": totals["master_pages"],
            "short_identifier_overlaps": summary[
                "short_identifier_overlaps"
            ],
            "qualified_collisions": summary["qualified_collisions"],
        },
        "bundle": {
            "filename": BUNDLE.name,
            "component_count": component_manifest["component_count"],
            "member_count": component_manifest["component_count"] + 1,
            "bytes": BUNDLE.stat().st_size,
            "sha256": sha256(BUNDLE),
            "zip_integrity": "PASS",
            "deterministic_member_order": True,
            "fixed_timestamp": "2026-07-28T12:00:00",
            "inherited_phase_bundles": len(PHASE_BUNDLES),
        },
        "publication_metadata": {
            "citation_file_format": "1.2.0",
            "zenodo_record_type": "preprint",
            "osf_metadata_present": True,
            "doi_assigned": False,
        },
        "claim_firewall": {
            "peer_review_completed": False,
            "cross_domain_physical_equivalence_claimed": False,
            "release_object_role": "provenance_and_reproducibility_master",
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


def copy_outputs() -> None:
    OUTPUT_PDF.mkdir(parents=True, exist_ok=True)
    OUTPUT_P12.mkdir(parents=True, exist_ok=True)
    copies = [
        (MASTER, OUTPUT_PDF / MASTER.name),
        (
            P12 / "reports/P12_Corpus_Freeze_Report_v1_3_ru.md",
            OUTPUT_P12 / "P12_Corpus_Freeze_Report_v1_3_ru.md",
        ),
        (
            P12 / "core/go_corpus_freeze_contract_v1_3.yaml",
            OUTPUT_P12 / "GO_Corpus_Freeze_Contract_v1_3.yaml",
        ),
        (
            P12 / "ledgers/go_corpus_freeze_ledger_v1_3.yaml",
            OUTPUT_P12 / "GO_Corpus_Freeze_Ledger_v1_3.yaml",
        ),
        (
            P12 / "ledgers/go_corpus_dependencies_v1_3.yaml",
            OUTPUT_P12 / "GO_Corpus_Dependencies_v1_3.yaml",
        ),
        (
            P12 / "ledgers/MASTER_PAGE_MAP_v1_3.json",
            OUTPUT_P12 / "MASTER_PAGE_MAP_v1_3.json",
        ),
        (
            P12 / "ledgers/MASTER_PAGE_MAP_v1_3.csv",
            OUTPUT_P12 / "MASTER_PAGE_MAP_v1_3.csv",
        ),
        (
            P12 / "reports/P12_Validation_Summary_v1_3.json",
            OUTPUT_P12 / "P12_Validation_Summary_v1_3.json",
        ),
        (
            P12 / "reports/P12_Cross_Module_Audit_v1_3.md",
            OUTPUT_P12 / "P12_Cross_Module_Audit_v1_3.md",
        ),
        (
            P12 / "reports/P12_Visual_QA_v1_3.yaml",
            OUTPUT_P12 / "P12_Visual_QA_v1_3.yaml",
        ),
        (CHECKSUMS, OUTPUT_P12 / CHECKSUMS.name),
        (COMPONENT_MANIFEST, OUTPUT_P12 / COMPONENT_MANIFEST.name),
        (RELEASE_MANIFEST, OUTPUT_P12 / RELEASE_MANIFEST.name),
        (BUNDLE, OUTPUT_P12 / BUNDLE.name),
    ]
    for source, destination in copies:
        shutil.copy2(source, destination)
        if sha256(source) != sha256(destination):
            raise RuntimeError(f"output copy hash mismatch: {destination}")


def main() -> None:
    BUNDLE_DIR.mkdir(parents=True, exist_ok=True)
    files = component_files()
    validate_inputs(files)
    component_manifest = write_component_manifest(files)
    build_bundle(files)
    write_release_manifest(component_manifest)
    copy_outputs()
    print(
        json.dumps(
            {
                "status": "PASS",
                "bundle": repository_relative(BUNDLE),
                "bundle_bytes": BUNDLE.stat().st_size,
                "bundle_sha256": sha256(BUNDLE),
                "members": component_manifest["component_count"] + 1,
                "master_sha256": sha256(MASTER),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
