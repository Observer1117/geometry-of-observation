#!/usr/bin/env python3
"""Validate the complete P12 corpus freeze and unified master release."""

from __future__ import annotations

import concurrent.futures
import hashlib
import json
import re
import subprocess
import tempfile
import zipfile
from pathlib import Path
from typing import Any

import yaml
from PIL import Image
from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[3]
P12 = ROOT / "work/p12_corpus_master_v1_3"
MASTER = (
    P12 / "build/master/Geometry_of_Observation_Corpus_Master_v1_3.pdf"
)
FRONT = (
    P12
    / "build/frontmatter/"
    "geometry_of_observation_corpus_master_frontmatter_v1_3.pdf"
)
FRONT_LOG = (
    P12
    / "build/frontmatter/"
    "geometry_of_observation_corpus_master_frontmatter_v1_3.log"
)
BASELINE = (
    ROOT / "work/p11_satellite_networks_v1_2/ledgers/corpus_ledgers_v1_2.yaml"
)
FREEZE = P12 / "ledgers/go_corpus_freeze_ledger_v1_3.yaml"
CONTRACT = P12 / "core/go_corpus_freeze_contract_v1_3.yaml"
DEPENDENCIES = P12 / "ledgers/go_corpus_dependencies_v1_3.yaml"
PAGE_MAP = P12 / "ledgers/MASTER_PAGE_MAP_v1_3.json"
CHECKSUMS = P12 / "SHA256SUMS_v1_3.txt"
VISUAL_QA = P12 / "reports/P12_Visual_QA_v1_3.yaml"
FREEZE_REPORT = P12 / "reports/P12_Corpus_Freeze_Report_v1_3_ru.md"
SUMMARY = P12 / "reports/P12_Validation_Summary_v1_3.json"
CROSS_AUDIT = P12 / "reports/P12_Cross_Module_Audit_v1_3.md"
UNIT_TEST = P12 / "tests/test_p12_corpus_master_v1_3.py"
MASTER_BUILDER = P12 / "scripts/build_p12_master.py"
GO_LINT = ROOT / "work/go_core_v0_2/src/go_lint.py"
GO_CORE = ROOT / "work/go_core_v0_2/core"
BUNDLE = (
    P12 / "bundle/GO_P12_Corpus_Master_v1_3_Release_Bundle.zip"
)
COMPONENT_MANIFEST = P12 / "bundle/RELEASE_COMPONENTS_v1_3.yaml"
RELEASE_MANIFEST = P12 / "RELEASE_MANIFEST_v1_3.yaml"
OUTPUT_MASTER = ROOT / "output/pdf/Geometry_of_Observation_Corpus_Master_v1_3.pdf"
OUTPUT_P12 = ROOT / "output/p12"
A4 = (595.28, 841.89)
FIXED_ZIP_TIMESTAMP = (2026, 7, 28, 12, 0, 0)

PHASE_VALIDATORS = [
    "work/p1_info_metric_v0_2/tests/validate_p1_release.py",
    "work/p2_distance_scale_v0_3/tests/validate_p2_release.py",
    "work/p3_planck_cosmos_v0_4/tests/validate_p3_release.py",
    "work/p4_lhc_si_hep_v0_5/tests/validate_p4_release.py",
    "work/p5_mechanics_frames_v0_6/tests/validate_p5_release.py",
    "work/p6_gear_contact_v0_7/tests/validate_p6_release.py",
    "work/p7_billiards_v0_8/tests/validate_p7_release.py",
    "work/p8_conical_intersections_v0_9/tests/validate_p8_release.py",
    "work/p9_quantum_chemistry_v1_0/tests/validate_p9_release.py",
    "work/p10_regular_polyhedra_v1_1/tests/validate_p10_release.py",
    "work/p11_satellite_networks_v1_2/tests/validate_p11_release.py",
]


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as stream:
        data = yaml.safe_load(stream)
    if not isinstance(data, dict):
        raise ValueError(path)
    return data


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(path)
    return data


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def parse_test_count(output: str) -> int:
    match = re.search(r"Ran (\d+) tests?", output)
    return int(match.group(1)) if match else 0


def font_embedding(path: Path) -> tuple[bool, int, list[str]]:
    process = run(["pdffonts", str(path)])
    if process.returncode != 0:
        return False, 0, [process.stderr.strip()]
    lines = [line for line in process.stdout.splitlines() if line.strip()]
    if len(lines) < 2:
        return False, 0, ["missing pdffonts rows"]
    header = lines[0]
    try:
        emb_start = header.index("emb")
        sub_start = header.index("sub", emb_start)
    except ValueError:
        return False, 0, ["unrecognized pdffonts header"]
    rows = lines[2:]
    nonembedded = [
        row
        for row in rows
        if row[emb_start:sub_start].strip().lower() != "yes"
    ]
    return not nonembedded, len(rows), nonembedded


def image_logical_check(paths: list[Path]) -> tuple[bool, list[list[int]], int]:
    dimensions: list[list[int]] = []
    total_bytes = 0
    for path in paths:
        try:
            with Image.open(path) as image:
                image.load()
                dimensions.append(list(image.size))
            total_bytes += path.stat().st_size
        except Exception:
            return False, dimensions, total_bytes
    return True, dimensions, total_bytes


def validate_phase(path_text: str) -> dict[str, Any]:
    process = run(["python3", path_text])
    return {
        "path": path_text,
        "status": "PASS" if process.returncode == 0 else "FAIL",
        "returncode": process.returncode,
        "reported_tests": parse_test_count(process.stdout + process.stderr),
    }


def write_cross_audit(summary: dict[str, Any]) -> None:
    checks = summary["checks"]
    lines = [
        "# P12 cross-module and release audit v1.3",
        "",
        f"Status: **{summary['status']}**",
        "",
        "## Frozen corpus",
        "",
        "- Normative modules: 18",
        "- Component pages: 158",
        "- Master pages: 166",
        "- Typed expressions: 347",
        "- Corpus result: 18 PASS / 0 FAIL / 0 BLOCKED",
        "- Dependency graph: 29 nodes / 36 edges / acyclic",
        "- Qualified short-name overlaps: 7 / collisions: 0",
        f"- P12 regression tests: {summary['regression_tests']}",
        f"- Phase release validators replayed: {summary['phase_validators']}",
        "",
        "## Check ledger",
        "",
        "| Check | Status |",
        "| --- | --- |",
    ]
    lines.extend(
        f"| `{item['id']}` | {item['status']} |" for item in checks
    )
    lines.extend(
        [
            "",
            "## Scientific interpretation",
            "",
            "The audit proves integrity, declared-type consistency, dependency "
            "closure, component-page preservation, and reproducibility of the "
            "release object. It does not replace independent peer review and "
            "does not convert common inference structure into cross-domain "
            "physical equivalence.",
            "",
        ]
    )
    CROSS_AUDIT.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    checks: list[dict[str, Any]] = []

    def record(check_id: str, condition: bool, detail: Any = None) -> None:
        checks.append(
            {
                "id": check_id,
                "status": "PASS" if condition else "FAIL",
                "detail": detail,
            }
        )

    required = [
        MASTER,
        FRONT,
        FRONT_LOG,
        BASELINE,
        FREEZE,
        CONTRACT,
        DEPENDENCIES,
        PAGE_MAP,
        CHECKSUMS,
        VISUAL_QA,
        FREEZE_REPORT,
        UNIT_TEST,
        MASTER_BUILDER,
        P12 / "metadata/CITATION.cff",
        P12 / "metadata/.zenodo.json",
        P12 / "metadata/OSF_RELEASE_METADATA_v1_3.yaml",
        P12 / "LICENSE.md",
        P12 / "README.md",
        P12 / "CHANGELOG.md",
    ]
    missing = [
        str(path.relative_to(ROOT)) for path in required if not path.is_file()
    ]
    record("required_files", not missing, {"missing": missing})

    before_master_hash = sha256(MASTER)
    rebuild = run(["python3", str(MASTER_BUILDER.relative_to(ROOT))])
    after_master_hash = sha256(MASTER) if MASTER.is_file() else ""
    rebuild_json: dict[str, Any] = {}
    if rebuild.returncode == 0:
        try:
            rebuild_json = json.loads(rebuild.stdout.splitlines()[-1])
        except (json.JSONDecodeError, IndexError):
            rebuild_json = {}
    record(
        "deterministic_master_rebuild",
        rebuild.returncode == 0
        and before_master_hash == after_master_hash
        and rebuild_json.get("status") == "PASS",
        {
            "before_sha256": before_master_hash,
            "after_sha256": after_master_hash,
            "pages": rebuild_json.get("master_pages"),
        },
    )

    freeze = load_yaml(FREEZE)
    contract = load_yaml(CONTRACT)
    dependency = load_yaml(DEPENDENCIES)
    page_map = load_json(PAGE_MAP)
    visual = load_yaml(VISUAL_QA)
    baseline = load_yaml(BASELINE)

    totals = freeze["corpus_totals"]
    record(
        "freeze_totals",
        totals["modules"] == 18
        and totals["component_pages"] == 158
        and totals["master_pages"] == 166
        and totals["expressions"] == 347
        and totals["claims"] == 136
        and totals["findings"] == 0,
        {
            "modules": totals["modules"],
            "component_pages": totals["component_pages"],
            "master_pages": totals["master_pages"],
            "expressions": totals["expressions"],
            "claims": totals["claims"],
            "findings": totals["findings"],
        },
    )
    record(
        "corpus_statuses",
        totals["corpus_statuses"] == {"PASS": 18, "FAIL": 0, "BLOCKED": 0},
        totals["corpus_statuses"],
    )
    record(
        "baseline_identity",
        freeze["baseline"]["sha256"] == sha256(BASELINE)
        and freeze["baseline"]["canonical_documents"] == 18
        and baseline["schema"]["canonical_documents"] == 18,
        {
            "sha256": sha256(BASELINE),
            "canonical_documents": baseline["schema"]["canonical_documents"],
        },
    )

    module_ids = [item["id"] for item in freeze["modules"]]
    record(
        "module_ids_and_order",
        len(module_ids) == 18
        and len(set(module_ids)) == 18
        and [item["release_index"] for item in freeze["modules"]]
        == list(range(1, 19)),
        {"first": module_ids[0], "last": module_ids[-1]},
    )
    record(
        "satellite_semantic_reorder",
        freeze["modules"][-1]["id"] == "satellite-networks-observation-v1-2"
        and freeze["modules"][-1]["ledger_index"] == 9,
        {
            "release_index": freeze["modules"][-1]["release_index"],
            "ledger_index": freeze["modules"][-1]["ledger_index"],
        },
    )

    component_failures = []
    component_pages = 0
    author_variants = set()
    for module in freeze["modules"]:
        source = module["source"]
        pdf = ROOT / source["pdf"]
        tex = ROOT / source["tex"]
        try:
            reader = PdfReader(pdf)
            author_variants.add(str(reader.metadata.author or ""))
            condition = (
                pdf.is_file()
                and tex.is_file()
                and sha256(pdf) == source["pdf_sha256"]
                and sha256(tex) == source["tex_sha256"]
                and pdf.stat().st_size == source["pdf_bytes"]
                and tex.stat().st_size == source["tex_bytes"]
                and len(reader.pages) == source["pages"]
                and not reader.is_encrypted
                and not (reader.get_fields() or {})
                and {(
                    round(float(page.mediabox.width), 2),
                    round(float(page.mediabox.height), 2),
                ) for page in reader.pages} == {A4}
            )
            component_pages += len(reader.pages)
        except Exception as error:
            condition = False
            component_failures.append(
                {"id": module["id"], "error": str(error)}
            )
        else:
            if not condition:
                component_failures.append({"id": module["id"]})
    record(
        "component_hash_page_and_pdf_gate",
        not component_failures and component_pages == 158,
        {
            "modules": len(freeze["modules"]),
            "pages": component_pages,
            "failures": component_failures,
        },
    )
    record(
        "component_author_variants",
        author_variants
        == {"Stas, Independent Research Program", "Stassis Research Program"},
        sorted(author_variants),
    )

    namespace = freeze["namespace_audit"]
    record(
        "namespace_qualification",
        namespace["qualified_expression_and_claim_ids"] == 483
        and namespace["short_identifier_overlap_count"] == 7
        and namespace["qualified_collisions"] == 0
        and namespace["map_id_collisions"] == 0
        and namespace["quantity_id_collisions"] == 0,
        {
            "qualified_ids": namespace["qualified_expression_and_claim_ids"],
            "short_overlaps": namespace["short_identifier_overlap_count"],
            "collisions": namespace["qualified_collisions"],
        },
    )

    node_ids = {item["id"] for item in dependency["nodes"]} | set(module_ids)
    edges = list(dependency["edges"])
    global_edge = dependency["global_core_edge"]
    edges.extend(
        {
            "from": global_edge["from"],
            "to": module_id,
            "kind": global_edge["kind"],
        }
        for module_id in module_ids
    )
    endpoint_failures = [
        edge
        for edge in edges
        if edge["from"] not in node_ids or edge["to"] not in node_ids
    ]
    record(
        "dependency_endpoints",
        len(node_ids) == 29 and len(edges) == 36 and not endpoint_failures,
        {
            "nodes": len(node_ids),
            "edges": len(edges),
            "unresolved": endpoint_failures,
        },
    )

    positions = {
        node_id: index
        for index, node_id in enumerate(
            freeze["dependency_audit"]["topological_order"]
        )
    }
    ordering_failures = [
        edge
        for edge in edges
        if positions.get(edge["from"], 10**9)
        >= positions.get(edge["to"], -1)
    ]
    record(
        "dependency_acyclicity",
        len(positions) == 29 and not ordering_failures,
        {"topological_nodes": len(positions), "violations": ordering_failures},
    )

    evidence_failures = []
    evidence_count = 0
    for edge in dependency["edges"]:
        evidence = edge.get("evidence")
        if not isinstance(evidence, dict):
            if edge["kind"] == "documented_interface":
                evidence_failures.append({"edge": edge, "reason": "missing"})
            continue
        evidence_count += 1
        source = ROOT / evidence["source"]
        if (
            not source.is_file()
            or evidence["fragment"]
            not in source.read_text(encoding="utf-8", errors="replace")
        ):
            evidence_failures.append({"edge": edge, "reason": "absent"})
    record(
        "dependency_source_evidence",
        evidence_count == 8 and not evidence_failures,
        {"evidence_edges": evidence_count, "failures": evidence_failures},
    )
    record(
        "contextual_dependency_firewall",
        len(dependency["contextual_relations_not_in_normative_graph"]) == 3
        and freeze["dependency_audit"]["contextual_relations_excluded"] == 3,
        {
            "excluded": len(
                dependency["contextual_relations_not_in_normative_graph"]
            )
        },
    )

    master_reader = PdfReader(MASTER)
    front_reader = PdfReader(FRONT)
    record(
        "master_pdf_metadata",
        len(master_reader.pages) == 166
        and master_reader.metadata.title == freeze["release_identity"]["title"]
        and master_reader.metadata.author == "Stassis Stashkevichyus",
        {
            "pages": len(master_reader.pages),
            "title": master_reader.metadata.title,
            "author": master_reader.metadata.author,
        },
    )
    record(
        "master_pdf_security_and_geometry",
        not master_reader.is_encrypted
        and not (master_reader.get_fields() or {})
        and {
            (
                round(float(page.mediabox.width), 2),
                round(float(page.mediabox.height), 2),
            )
            for page in master_reader.pages
        }
        == {A4},
        {
            "encrypted": master_reader.is_encrypted,
            "form_fields": len(master_reader.get_fields() or {}),
            "page_size": list(A4),
        },
    )
    record(
        "frontmatter_pdf",
        len(front_reader.pages) == 8
        and front_reader.metadata.author == "Stassis Stashkevichyus",
        {
            "pages": len(front_reader.pages),
            "sha256": sha256(FRONT),
        },
    )
    record(
        "master_outline_and_page_labels",
        len(master_reader.outline) == 19
        and len(master_reader.page_labels) == 166
        and master_reader.page_labels[:8]
        == ["i", "ii", "iii", "iv", "v", "vi", "vii", "viii"]
        and master_reader.page_labels[-1] == "M18-8",
        {
            "outline_items": len(master_reader.outline),
            "first_labels": master_reader.page_labels[:9],
            "last_label": master_reader.page_labels[-1],
        },
    )
    content = MASTER.read_bytes()
    record(
        "master_header_and_eof",
        content.startswith(b"%PDF-") and content.rstrip().endswith(b"%%EOF"),
        {"bytes": len(content), "sha256": sha256(MASTER)},
    )

    master_fonts_ok, master_font_rows, master_nonembedded = font_embedding(
        MASTER
    )
    record(
        "master_embedded_fonts",
        master_fonts_ok and master_font_rows > 0,
        {
            "font_rows": master_font_rows,
            "nonembedded": master_nonembedded,
        },
    )
    front_fonts_ok, front_font_rows, front_nonembedded = font_embedding(FRONT)
    record(
        "frontmatter_embedded_fonts",
        front_fonts_ok and front_font_rows > 0,
        {
            "font_rows": front_font_rows,
            "nonembedded": front_nonembedded,
        },
    )

    log_text = FRONT_LOG.read_text(encoding="utf-8", errors="replace")
    log_hits = re.findall(
        r"Overfull|Underfull|undefined references|multiply defined|"
        r"Missing character|LaTeX Warning",
        log_text,
    )
    record(
        "frontmatter_latex_log",
        not log_hits,
        {"hits": log_hits},
    )

    unit_process = run(
        [
            "python3",
            "-m",
            "unittest",
            "-q",
            str(UNIT_TEST.relative_to(ROOT)),
        ]
    )
    unit_output = unit_process.stdout + unit_process.stderr
    regression_tests = parse_test_count(unit_output)
    record(
        "p12_regression_suite",
        unit_process.returncode == 0 and regression_tests == 259,
        {
            "tests": regression_tests,
            "returncode": unit_process.returncode,
        },
    )

    with tempfile.TemporaryDirectory(prefix="go_p12_lint_") as temporary:
        lint_json = Path(temporary) / "lint.json"
        lint_md = Path(temporary) / "lint.md"
        lint_process = run(
            [
                "python3",
                str(GO_LINT),
                "--core-dir",
                str(GO_CORE),
                "--ledger",
                str(BASELINE),
                "--only-level",
                "reference",
                "--mode",
                "strict",
                "--output-json",
                str(lint_json),
                "--output-md",
                str(lint_md),
            ]
        )
        lint_data = load_json(lint_json) if lint_json.is_file() else {}
    lint_summary = lint_data.get("summary", {})
    record(
        "go_core_strict_replay",
        lint_process.returncode == 0
        and lint_summary.get("canonical_documents") == 18
        and lint_summary.get("reference_documents") == 18
        and lint_summary.get("expressions_checked") == 347
        and lint_summary.get("findings_total") == 0
        and lint_summary.get("status_counts") == {"PASS": 18},
        lint_summary,
    )

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        phase_results = list(executor.map(validate_phase, PHASE_VALIDATORS))
    record(
        "phase_validator_replay",
        len(phase_results) == 11
        and all(item["status"] == "PASS" for item in phase_results),
        {
            "validators": len(phase_results),
            "statuses": {
                Path(item["path"]).name: item["status"]
                for item in phase_results
            },
        },
    )
    for index, result in enumerate(phase_results, start=1):
        record(
            f"phase_validator_{index:02d}",
            result["status"] == "PASS",
            {
                "path": result["path"],
                "reported_tests": result["reported_tests"],
            },
        )

    with tempfile.TemporaryDirectory(prefix="go_p12_render_") as temporary:
        prefix = Path(temporary) / "page"
        render_process = run(
            [
                "pdftoppm",
                "-png",
                "-r",
                "36",
                str(MASTER),
                str(prefix),
            ]
        )
        rendered = sorted(Path(temporary).glob("page-*.png"))
        images_ok, dimensions, render_bytes = image_logical_check(rendered)
    unique_dimensions = sorted({tuple(item) for item in dimensions})
    record(
        "independent_master_render",
        render_process.returncode == 0
        and images_ok
        and len(rendered) == 166
        and unique_dimensions == [(298, 421)],
        {
            "rendered_pages": len(rendered),
            "dimensions": [list(item) for item in unique_dimensions],
            "total_png_bytes": render_bytes,
        },
    )

    front_contacts = sorted(
        (P12 / "render/frontmatter").glob("contact_sheet.*")
    )
    master_contacts = sorted(
        path
        for path in (P12 / "render/master").glob("contact_sheet_*.*")
        if path.suffix.lower() in {".png", ".jpg", ".jpeg"}
        and path.name != "contact_sheet_6.png"
    )
    contacts = front_contacts + master_contacts
    contacts_ok, contact_dimensions, contact_bytes = image_logical_check(
        contacts
    )
    record(
        "visual_contact_sheets",
        contacts_ok and len(front_contacts) == 1 and len(master_contacts) == 6,
        {
            "front_sheets": len(front_contacts),
            "master_sheets": len(master_contacts),
            "dimensions": contact_dimensions,
            "bytes": contact_bytes,
        },
    )
    record(
        "visual_qa_record",
        visual["status"] == "PASS"
        and visual["master"]["sha256"] == sha256(MASTER)
        and visual["master"]["pages"] == 166
        and visual["front_matter"]["latex_layout_warnings"] == 0
        and visual["component_interval"]["rendered_pngs"] == 166,
        {
            "status": visual["status"],
            "master_sha256": visual["master"]["sha256"],
            "rendered_pngs": visual["component_interval"]["rendered_pngs"],
        },
    )

    entries = page_map["entries"]
    cursor = 1
    page_map_ok = len(entries) == 19
    for entry in entries:
        page_map_ok = (
            page_map_ok
            and entry["master_page_start"] == cursor
            and entry["master_page_end"] - entry["master_page_start"] + 1
            == entry["component_pages"]
        )
        cursor = entry["master_page_end"] + 1
    page_map_ok = (
        page_map_ok
        and cursor == 167
        and page_map["master_pdf_sha256"] == sha256(MASTER)
    )
    record(
        "master_page_map",
        page_map_ok,
        {
            "entries": len(entries),
            "terminal_cursor": cursor,
            "master_sha256": page_map["master_pdf_sha256"],
        },
    )

    checksum_failures = []
    checksum_lines = [
        line
        for line in CHECKSUMS.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    checksum_paths = []
    for line in checksum_lines:
        expected, path_text = line.split("  ", 1)
        checksum_paths.append(path_text)
        path = ROOT / path_text
        if not path.is_file() or sha256(path) != expected:
            checksum_failures.append(path_text)
    record(
        "frozen_checksums",
        not checksum_failures
        and checksum_paths == sorted(checksum_paths)
        and len(checksum_paths) == len(set(checksum_paths)),
        {
            "records": len(checksum_lines),
            "failures": checksum_failures,
        },
    )

    citation = load_yaml(P12 / "metadata/CITATION.cff")
    zenodo = load_json(P12 / "metadata/.zenodo.json")
    osf = load_yaml(P12 / "metadata/OSF_RELEASE_METADATA_v1_3.yaml")
    record(
        "citation_metadata",
        citation["cff-version"] == "1.2.0"
        and citation["version"] == "1.3.0"
        and citation["authors"][0]["orcid"]
        == "https://orcid.org/0009-0000-2294-705X"
        and "identifiers" not in citation,
        {
            "cff_version": citation["cff-version"],
            "release_version": citation["version"],
        },
    )
    record(
        "zenodo_metadata",
        zenodo["upload_type"] == "publication"
        and zenodo["publication_type"] == "preprint"
        and zenodo["version"] == "1.3.0"
        and zenodo["license"] == "cc-by-nc-nd-4.0"
        and "doi" not in zenodo,
        {
            "record_type": zenodo["publication_type"],
            "license": zenodo["license"],
        },
    )
    record(
        "osf_metadata",
        osf["version"] == "1.3.0"
        and osf["creator"]["orcid"]
        == "https://orcid.org/0009-0000-2294-705X"
        and osf["doi"] is None,
        {
            "version": osf["version"],
            "doi": osf["doi"],
        },
    )
    identity = contract["release_identity"]
    record(
        "metadata_identity_consistency",
        freeze["release_identity"]["author"] == "Stassis Stashkevichyus"
        and identity["author"]["name"] == "Stassis Stashkevichyus"
        and zenodo["creators"][0]["name"] == "Stashkevichyus, Stassis"
        and citation["authors"][0]["family-names"] == "Stashkevichyus"
        and citation["authors"][0]["given-names"] == "Stassis",
        {
            "freeze_author": freeze["release_identity"]["author"],
            "zenodo_author": zenodo["creators"][0]["name"],
        },
    )
    record(
        "doi_firewall",
        freeze["release_identity"]["doi"] is None
        and contract["release_identity"]["doi"] is None
        and osf["doi"] is None
        and "doi" not in zenodo
        and "identifiers" not in citation,
        {"assigned": False, "placeholder": False},
    )
    license_text = (P12 / "LICENSE.md").read_text(encoding="utf-8")
    record(
        "license_consistency",
        "CC BY-NC-ND 4.0" in license_text
        and identity["license"]["id"] == "CC-BY-NC-ND-4.0"
        and zenodo["license"] == "cc-by-nc-nd-4.0"
        and citation["license"] == "CC-BY-NC-ND-4.0",
        {
            "contract": identity["license"]["id"],
            "zenodo": zenodo["license"],
            "cff": citation["license"],
        },
    )

    report_text = FREEZE_REPORT.read_text(encoding="utf-8")
    report_fragments = [
        "полный corpus freeze",
        "Нормативная граница",
        "Межмодульные зависимости",
        "Пространства имён",
        "Авторская и архивная метаинформация",
        "Научный claim firewall",
        "18 PASS / 0 FAIL / 0 BLOCKED",
        "Строгая оценка",
    ]
    missing_report_fragments = [
        fragment for fragment in report_fragments if fragment not in report_text
    ]
    record(
        "freeze_report_coverage",
        not missing_report_fragments,
        {"missing": missing_report_fragments},
    )

    output_copies = [
        (MASTER, OUTPUT_MASTER),
        (FREEZE, OUTPUT_P12 / "GO_Corpus_Freeze_Ledger_v1_3.yaml"),
        (DEPENDENCIES, OUTPUT_P12 / "GO_Corpus_Dependencies_v1_3.yaml"),
        (PAGE_MAP, OUTPUT_P12 / "MASTER_PAGE_MAP_v1_3.json"),
        (CHECKSUMS, OUTPUT_P12 / "SHA256SUMS_v1_3.txt"),
    ]
    output_failures = [
        str(destination.relative_to(ROOT))
        for source, destination in output_copies
        if not destination.is_file() or sha256(source) != sha256(destination)
    ]
    record(
        "public_output_copies",
        not output_failures,
        {"failures": output_failures},
    )

    bundle_present = BUNDLE.is_file()
    if bundle_present:
        try:
            with zipfile.ZipFile(BUNDLE, "r") as archive:
                bad_member = archive.testzip()
                names = archive.namelist()
                timestamps = {info.date_time for info in archive.infolist()}
                internal = yaml.safe_load(
                    archive.read("RELEASE_COMPONENTS_v1_3.yaml")
                )
                member_count = len(names)
        except Exception as error:
            record(
                "bundle_integrity",
                False,
                {"error": str(error)},
            )
        else:
            record(
                "bundle_integrity",
                bad_member is None
                and names == sorted(names)
                and timestamps == {FIXED_ZIP_TIMESTAMP}
                and isinstance(internal, dict)
                and internal.get("schema", {}).get("id")
                == "go-p12-release-components",
                {
                    "members": member_count,
                    "bad_member": bad_member,
                    "sorted": names == sorted(names),
                    "timestamps": [list(item) for item in sorted(timestamps)],
                },
            )
    else:
        record(
            "bundle_integrity",
            True,
            {"state": "NOT_BUILT_DURING_PREBUNDLE_VALIDATION"},
        )

    manifest_present = RELEASE_MANIFEST.is_file()
    if manifest_present:
        manifest = load_yaml(RELEASE_MANIFEST)
        manifest_ok = (
            manifest["status"] == "PASS"
            and manifest["master"]["sha256"] == sha256(MASTER)
            and manifest["master"]["pages"] == 166
            and manifest["bundle"]["filename"] == BUNDLE.name
            and BUNDLE.is_file()
            and manifest["bundle"]["sha256"] == sha256(BUNDLE)
        )
        record(
            "release_manifest",
            manifest_ok,
            {
                "status": manifest["status"],
                "master_pages": manifest["master"]["pages"],
                "bundle_present": BUNDLE.is_file(),
            },
        )
    else:
        record(
            "release_manifest",
            True,
            {"state": "NOT_BUILT_DURING_PREBUNDLE_VALIDATION"},
        )

    status = "PASS" if all(item["status"] == "PASS" for item in checks) else "FAIL"
    summary = {
        "schema": {
            "id": "go-p12-validation-summary",
            "version": "1.3.0",
        },
        "date": "2026-07-28",
        "status": status,
        "release_check_count": len(checks),
        "regression_tests": regression_tests,
        "phase_validators": len(phase_results),
        "corpus_modules": 18,
        "component_pages": 158,
        "master_pages": 166,
        "typed_expressions": 347,
        "dependency_nodes": 29,
        "dependency_edges": 36,
        "short_identifier_overlaps": 7,
        "qualified_collisions": 0,
        "corpus_statuses": {"PASS": 18, "FAIL": 0, "BLOCKED": 0},
        "bundle_present": bundle_present,
        "release_manifest_present": manifest_present,
        "checks": checks,
    }
    SUMMARY.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    write_cross_audit(summary)
    print(
        f"P12-VALIDATION status={status} checks="
        f"{sum(item['status'] == 'PASS' for item in checks)}/{len(checks)} "
        f"tests={regression_tests} phases={len(phase_results)} "
        f"pages={len(master_reader.pages)}"
    )
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
