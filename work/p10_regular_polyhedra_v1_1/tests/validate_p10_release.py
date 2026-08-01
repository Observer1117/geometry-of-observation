#!/usr/bin/env python3
"""Validate the complete P10 regular-polyhedra release candidate."""

from __future__ import annotations

import csv
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

import yaml
from PIL import Image
from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[3]
P10 = ROOT / "work/p10_regular_polyhedra_v1_1"

PDF = (
    P10
    / "build/polyhedra/regular_polyhedra_observation_filters_v1_1.pdf"
)
TEX = P10 / "src/regular_polyhedra_observation_filters_v1_1.tex"
TEXT = (
    P10
    / "checks/polyhedra/regular_polyhedra_observation_filters_v1_1.txt"
)
LOG = (
    P10
    / "build/polyhedra/regular_polyhedra_observation_filters_v1_1.log"
)
CONTRACT = P10 / "core/regular_polyhedra_observation_contract_v1_1.yaml"
REFERENCE_LEDGER = (
    P10 / "ledgers/regular_polyhedra_reference_ledger_v1_1.yaml"
)
CORPUS_LEDGER = P10 / "ledgers/corpus_ledgers_v1_1.yaml"
REFERENCE_LINT = (
    P10 / "reports/Regular_Polyhedra_Reference_Lint_Report_v1_1.json"
)
CORPUS_LINT = P10 / "reports/GO_Corpus_Lint_Report_v1_1.json"
MIGRATION_REPORT = (
    P10 / "reports/P10_Regular_Polyhedra_Migration_Report_v1_1_ru.md"
)
VISUAL_QA = P10 / "reports/P10_Visual_QA_v1_1.yaml"
BENCHMARKS = P10 / "data/regular_polyhedra_benchmarks_v1_1.csv"
METRICS = P10 / "data/regular_polyhedra_metrics_v1_1.json"
TEST_FILE = P10 / "tests/test_regular_polyhedra_v1_1.py"
GO_LINT = ROOT / "work/go_core_v0_2/src/go_lint.py"
GO_CORE = ROOT / "work/go_core_v0_2/core"
SUMMARY = P10 / "reports/P10_Validation_Summary_v1_1.json"
RENDER_DIR = P10 / "render/polyhedra"


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as stream:
        value = yaml.safe_load(stream)
    if not isinstance(value, dict):
        raise TypeError(f"{path}: YAML root must be a mapping")
    return value


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as stream:
        value = json.load(stream)
    if not isinstance(value, dict):
        raise TypeError(f"{path}: JSON root must be an object")
    return value


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
        check=False,
        capture_output=True,
        text=True,
    )


def main() -> int:
    checks: list[dict[str, Any]] = []

    def record(check_id: str, passed: bool, detail: Any) -> None:
        checks.append(
            {
                "id": check_id,
                "status": "PASS" if passed else "FAIL",
                "detail": detail,
            }
        )

    required_files = [
        PDF,
        TEX,
        TEXT,
        LOG,
        CONTRACT,
        REFERENCE_LEDGER,
        CORPUS_LEDGER,
        REFERENCE_LINT,
        CORPUS_LINT,
        MIGRATION_REPORT,
        VISUAL_QA,
        BENCHMARKS,
        METRICS,
        TEST_FILE,
        GO_LINT,
    ]
    missing = [
        str(path.relative_to(ROOT))
        for path in required_files
        if not path.is_file()
    ]
    record("required_files", not missing, {"missing": missing})
    if missing:
        result = {
            "schema": {
                "id": "go-p10-validation-summary",
                "version": "1.1.0",
            },
            "date": "2026-07-28",
            "status": "FAIL",
            "checks": checks,
        }
        SUMMARY.parent.mkdir(parents=True, exist_ok=True)
        SUMMARY.write_text(
            json.dumps(result, indent=2, default=str) + "\n",
            encoding="utf-8",
        )
        return 1

    document = load_yaml(REFERENCE_LEDGER)["documents"][0]
    expected_hash = document["source"]["sha256"]
    actual_hash = sha256(PDF)
    record(
        "pdf_sha256",
        expected_hash == actual_hash,
        {"expected": expected_hash, "actual": actual_hash},
    )

    reader = PdfReader(PDF)
    metadata = reader.metadata or {}
    metadata_ok = (
        len(reader.pages) == 7
        and metadata.get("/Title")
        == "Regular Polyhedra under Typed Observation Filters"
        and metadata.get("/Author") == "Stas, Independent Research Program"
    )
    record(
        "pdf_metadata",
        metadata_ok,
        {
            "pages": len(reader.pages),
            "title": metadata.get("/Title"),
            "author": metadata.get("/Author"),
        },
    )

    first_box = reader.pages[0].mediabox
    width = float(first_box.width)
    height = float(first_box.height)
    security_ok = (
        not reader.is_encrypted
        and reader.get_fields() in (None, {})
        and abs(width - 595.28) < 0.2
        and abs(height - 841.89) < 0.2
    )
    record(
        "pdf_security_and_page_size",
        security_ok,
        {
            "encrypted": reader.is_encrypted,
            "form_fields": len(reader.get_fields() or {}),
            "page_size_points": [width, height],
        },
    )

    prohibited_hits: dict[str, dict[str, int]] = {}
    for token in ("TODO", "TBD", "PENDING", "\ufffd"):
        hits: dict[str, int] = {}
        for path in (
            TEX,
            TEXT,
            CONTRACT,
            REFERENCE_LEDGER,
            MIGRATION_REPORT,
        ):
            count = path.read_text(
                encoding="utf-8",
                errors="replace",
            ).count(token)
            if count:
                hits[path.name] = count
        if hits:
            prohibited_hits[token] = hits
    record("no_prohibited_tokens", not prohibited_hits, prohibited_hits)

    extracted = TEXT.read_text(encoding="utf-8", errors="replace")
    source = TEX.read_text(encoding="utf-8")
    extracted_reference_headings = sum(
        line.strip() == "References" for line in extracted.splitlines()
    )
    source_reference_headings = source.count(r"\section*{References}")
    record(
        "bibliography_heading_unique",
        extracted_reference_headings == 1 and source_reference_headings == 1,
        {
            "extracted": extracted_reference_headings,
            "source": source_reference_headings,
        },
    )

    extracted_text_ok = (
        len(extracted) > 19_000
        and "Half-separation certificate" in extracted
        and "Protocol minimum" in extracted
        and "References" in extracted
        and extracted.count("\f") == 7
    )
    record(
        "extracted_text",
        extracted_text_ok,
        {
            "characters": len(extracted),
            "form_feeds": extracted.count("\f"),
        },
    )

    required_fragments = [
        r"\section{Scope and the category of objects}",
        r"\section{Flags, abstract regularity, and string C-groups}",
        r"\section{Abstract symmetry versus realization symmetry}",
        r"\section{Observation specifications and two preorders}",
        r"\section{Classical spherical count and its hypotheses}",
        r"\section{Skeleton non-identifiability and the Petrial control}",
        r"\section{Finite-resolution symmetry and identifiability}",
        r"\section{Convention-scoped taxonomy and claim firewall}",
        r"\Ocal_1\preceq_{\rm adm}\Ocal_2",
        r"Q_{\rm coarse}=\kappa\circ Q_{\rm fine}",
        r"(\rho_0\rho_2,\rho_1,\rho_2)",
        r"r_Y(g)\le2\epsilon",
    ]
    absent_fragments = [
        fragment for fragment in required_fragments if fragment not in source
    ]
    record(
        "required_source_fragments",
        not absent_fragments,
        {"absent": absent_fragments},
    )

    log_text = LOG.read_text(encoding="utf-8", errors="replace")
    forbidden_log_patterns = [
        "Overfull",
        "Underfull",
        "LaTeX Warning",
        "undefined references",
        "multiply defined",
        "Fatal error",
        "Missing character",
    ]
    log_hits = [
        pattern for pattern in forbidden_log_patterns if pattern in log_text
    ]
    record("latex_log", not log_hits, {"hits": log_hits})

    fonts_process = run(["pdffonts", str(PDF)])
    font_rows = [
        line.split()
        for line in fonts_process.stdout.splitlines()[2:]
        if line.strip()
    ]
    nonembedded = [
        row[0]
        for row in font_rows
        if len(row) < 7 or row[-5].lower() != "yes"
    ]
    fonts_ok = (
        fonts_process.returncode == 0 and bool(font_rows) and not nonembedded
    )
    record(
        "embedded_fonts",
        fonts_ok,
        {
            "font_count": len(font_rows),
            "nonembedded": nonembedded,
            "returncode": fonts_process.returncode,
        },
    )

    contract = load_yaml(CONTRACT)
    contract_ok = (
        contract["schema"]["id"]
        == "go-regular-polyhedra-observation-contract"
        and contract["schema"]["version"] == "1.1.0"
        and contract["schema"]["inherited_contracts"]
        == ["go-quantum-chemistry-observation-contract@1.0.0"]
        and len(contract["reference_gates"]) == 15
    )
    record(
        "contract_schema_and_gates",
        contract_ok,
        {
            "schema": contract["schema"],
            "reference_gate_count": len(contract["reference_gates"]),
        },
    )

    object_symmetry_ok = (
        contract["object_layer"]["abstract_polyhedron"]["structure"]
        == "ranked_poset"
        and contract["object_layer"]["groupoid"]["id"] == "RPol_3"
        and contract["symmetry_layer"]["abstract_group"]["definition"]
        == "Aut(P)"
        and contract["symmetry_layer"]["implication"][
            "abstract_regular_implies_given_realization_geometric_regular"
        ]
        is False
        and contract["symmetry_layer"]["counterexample"][
            "geometric_flag_orbits"
        ]
        == 6
        and contract["string_C_group_layer"][
            "finite_regular_flag_count"
        ]["formula"]
        == "order_Aut_P_equals_number_of_flags_equals_4E"
    )
    record(
        "contract_object_and_symmetry_firewalls",
        object_symmetry_ok,
        object_symmetry_ok,
    )

    preorder_ok = (
        contract["observation_specification"]["admissibility_preorder"][
            "formula"
        ]
        == "O1_le_adm_O2_iff_C1_is_full_subgroupoid_of_C2"
        and contract["observation_specification"]["information_preorder"][
            "kernel_law"
        ]
        == "kernel_Q_fine_subset_kernel_Q_coarse"
        and contract["observation_specification"]["independence"][
            "admission_does_not_imply_information_refinement"
        ]
        is True
        and contract["observation_specification"]["independence"][
            "historical_relaxations_form_total_chain"
        ]
        is False
    )
    record("contract_preorder_firewalls", preorder_ok, preorder_ok)

    petrial_counts_ok = (
        contract["duality_and_Petrial"]["Petrie_operation"][
            "generator_action"
        ]
        == ["rho_0_rho_2", "rho_1", "rho_2"]
        and contract["duality_and_Petrial"]["cube_control"][
            "cube_f_vector"
        ]
        == [8, 12, 6]
        and contract["duality_and_Petrial"]["cube_control"][
            "cube_Petrial_f_vector"
        ]
        == [8, 12, 4]
        and contract["count_firewall"]["Schulte_skeletal_R3"]
        == {
            "count": 48,
            "finite": 18,
            "infinite": 30,
            "convention": (
                "discrete_geometrically_regular_skeletal_polyhedra_in_R3"
            ),
        }
    )
    record(
        "contract_Petrial_and_count_firewalls",
        petrial_counts_ok,
        petrial_counts_ok,
    )

    resolution_entropy_ok = (
        contract["finite_resolution_layer"]["exact_symmetry_bound"][
            "formula"
        ]
        == "r_Y_g_at_most_2_epsilon"
        and contract["finite_resolution_layer"]["exact_symmetry_bound"][
            "converse"
        ]
        is False
        and contract["finite_resolution_layer"][
            "finite_library_identifiability"
        ]["certificate"]
        == "distance_Y_Mi_less_than_Delta_i_over_2"
        and contract["flag_orbit_diagnostic"]["entropy"]["base"] == 2
        and contract["flag_orbit_diagnostic"]["entropy"]["semantics"]
        == "combinatorial_Shannon_diagnostic"
    )
    record(
        "contract_resolution_and_entropy_firewalls",
        resolution_entropy_ok,
        resolution_entropy_ok,
    )

    reference_summary = load_json(REFERENCE_LINT)["summary"]
    reference_ok = (
        reference_summary["canonical_documents"] == 1
        and reference_summary["reference_documents"] == 1
        and reference_summary["critical_adapters"] == 0
        and reference_summary["expressions_checked"] == 42
        and reference_summary["findings_total"] == 0
        and reference_summary["status_counts"] == {"PASS": 1}
    )
    record("reference_lint", reference_ok, reference_summary)

    corpus_report = load_json(CORPUS_LINT)
    corpus_summary = corpus_report["summary"]
    corpus_ok = (
        corpus_summary["canonical_documents"] == 18
        and corpus_summary["reference_documents"] == 17
        and corpus_summary["critical_adapters"] == 1
        and corpus_summary["expressions_checked"] == 295
        and corpus_summary["findings_total"] == 3
        and corpus_summary["status_counts"] == {"FAIL": 1, "PASS": 17}
    )
    record("corpus_lint", corpus_ok, corpus_summary)

    failing_ids = [
        item["id"]
        for item in corpus_report["documents"]
        if item["status"] != "PASS"
    ]
    expected_failing_ids = ["satellite-networks-v1-1"]
    record(
        "expected_remaining_failure",
        failing_ids == expected_failing_ids,
        {"actual": failing_ids, "expected": expected_failing_ids},
    )

    corpus = load_yaml(CORPUS_LEDGER)
    ids = [item["id"] for item in corpus["documents"]]
    legacy_records = [
        item
        for item in corpus["duplicate_or_superseded_sources"]
        if "regular_polyhedra_observation" in item.get("path", "")
    ]
    supersession_ok = (
        len(ids) == 18
        and len(set(ids)) == 18
        and "regular-polyhedra-v1" not in ids
        and "regular-polyhedra-observation-v1-1" in ids
        and len(legacy_records) == 1
        and legacy_records[0].get("status") == "superseded"
        and legacy_records[0].get("sha256")
        == "890536d32b30a7b995f3e9b1935c13561331eb5476e519c0aa33511ffcf23d4e"
        and legacy_records[0].get("canonical_document")
        == "regular-polyhedra-observation-v1-1"
    )
    record(
        "legacy_supersession",
        supersession_ok,
        {"legacy_records": legacy_records},
    )

    with BENCHMARKS.open("r", encoding="utf-8", newline="") as stream:
        benchmark_rows = list(csv.DictReader(stream))
    category_counts: dict[str, int] = {}
    for row in benchmark_rows:
        category_counts[row["category"]] = (
            category_counts.get(row["category"], 0) + 1
        )
    expected_category_counts = {
        "Platonic_incidence": 40,
        "bounded_noise_symmetry": 48,
        "cube_Petrial": 11,
        "finite_library": 96,
        "flag_orbits": 7,
        "spherical_type": 100,
    }
    benchmark_ok = (
        len(benchmark_rows) == 302
        and category_counts == expected_category_counts
        and all(row["status"] == "PASS" for row in benchmark_rows)
    )
    record(
        "benchmark_table",
        benchmark_ok,
        {"rows": len(benchmark_rows), "categories": category_counts},
    )

    metrics = load_json(METRICS)
    residuals_ok = (
        metrics["benchmark_rows"] == 302
        and metrics["failed_rows"] == 0
        and metrics["max_absolute_error"] < 2e-15
        and metrics["controls"]["cube_group_order"] == 48
        and metrics["controls"]["cuboid_group_order"] == 8
        and metrics["controls"]["cube_Petrie_faces"] == 4
    )
    record("numerical_residuals", residuals_ok, metrics)

    tests_process = run(
        [
            "python3",
            "-m",
            "unittest",
            "-q",
            str(TEST_FILE.relative_to(ROOT)),
        ]
    )
    tests_output = tests_process.stdout + tests_process.stderr
    test_match = re.search(r"Ran (\d+) tests?", tests_output)
    test_count = int(test_match.group(1)) if test_match else None
    tests_ok = tests_process.returncode == 0 and test_count == 357
    record(
        "regression_suite",
        tests_ok,
        {
            "returncode": tests_process.returncode,
            "tests": test_count,
            "result": "OK" if tests_ok else "FAIL",
        },
    )

    reference_replay = run(
        [
            "python3",
            str(GO_LINT),
            "--core-dir",
            str(GO_CORE),
            "--ledger",
            str(REFERENCE_LEDGER),
            "--mode",
            "strict",
        ]
    )
    record(
        "reference_strict_replay",
        reference_replay.returncode == 0
        and "expressions=42" in reference_replay.stdout
        and "findings=0" in reference_replay.stdout
        and "PASS" in reference_replay.stdout,
        {
            "returncode": reference_replay.returncode,
            "stdout": reference_replay.stdout.strip(),
            "stderr": reference_replay.stderr.strip(),
        },
    )

    corpus_replay = run(
        [
            "python3",
            str(GO_LINT),
            "--core-dir",
            str(GO_CORE),
            "--ledger",
            str(CORPUS_LEDGER),
            "--mode",
            "strict",
        ]
    )
    record(
        "corpus_strict_expected_nonzero",
        corpus_replay.returncode == 1
        and "expressions=295" in corpus_replay.stdout
        and "findings=3" in corpus_replay.stdout
        and "statuses={'FAIL': 1, 'PASS': 17}" in corpus_replay.stdout,
        {
            "returncode": corpus_replay.returncode,
            "stdout": corpus_replay.stdout.strip(),
            "stderr": corpus_replay.stderr.strip(),
        },
    )

    visual = load_yaml(VISUAL_QA)
    visual_ok = (
        visual["status"] == "PASS"
        and visual["document"]["sha256"] == actual_hash
        and visual["document"]["pages"] == 7
        and len(visual["inspection"]["pages"]) == 7
        and all(
            item["status"] == "PASS"
            for item in visual["inspection"]["pages"]
        )
        and all(
            value == "PASS" for value in visual["global_checks"].values()
        )
    )
    record("visual_qa", visual_ok, visual)

    rendered_pages = sorted(RENDER_DIR.glob("page-*.png"))
    render_details: list[dict[str, Any]] = []
    render_ok = len(rendered_pages) == 7
    for path in rendered_pages:
        try:
            with Image.open(path) as image:
                image.load()
                dimensions = list(image.size)
            page_ok = (
                dimensions == [1191, 1684]
                and path.stat().st_size > 100_000
            )
        except Exception as error:  # pragma: no cover
            dimensions = []
            page_ok = False
            render_details.append(
                {"file": path.name, "status": "FAIL", "error": str(error)}
            )
        else:
            render_details.append(
                {
                    "file": path.name,
                    "status": "PASS" if page_ok else "FAIL",
                    "dimensions": dimensions,
                    "bytes": path.stat().st_size,
                }
            )
        render_ok = render_ok and page_ok
    record(
        "rendered_pages",
        render_ok,
        {"count": len(rendered_pages), "pages": render_details},
    )

    report_text = MIGRATION_REPORT.read_text(
        encoding="utf-8",
        errors="replace",
    )
    report_fragments = [
        "Почему legacy filter ladder был неопределён",
        "Абстрактная и геометрическая регулярность",
        "Точная неинъективность skeleton observation",
        "Конечное разрешение и идентифицируемость",
        "Convention-scoped counts",
        "17 PASS / 1 FAIL /",
        "Следующий рациональный кандидат — `Satellite Networks`",
    ]
    missing_report_fragments = [
        fragment
        for fragment in report_fragments
        if fragment not in report_text
    ]
    record(
        "migration_report_coverage",
        not missing_report_fragments,
        {"missing": missing_report_fragments},
    )

    primary_identifiers = [
        "10.1017/CBO9780511546686",
        "10.1007/PL00009304",
        "1711.02297",
        "10.1107/S2053273314000217",
        "10.1007/BF01836414",
        "10.1007/BF02188039",
        "10.1007/BF02189831",
    ]
    missing_identifiers = [
        identifier
        for identifier in primary_identifiers
        if identifier not in source
    ]
    record(
        "primary_reference_identifiers",
        not missing_identifiers,
        {"missing": missing_identifiers},
    )

    status = (
        "PASS"
        if checks and all(item["status"] == "PASS" for item in checks)
        else "FAIL"
    )
    result = {
        "schema": {
            "id": "go-p10-validation-summary",
            "version": "1.1.0",
        },
        "date": "2026-07-28",
        "status": status,
        "release_check_count": len(checks),
        "typed_expressions": 42,
        "regression_tests": 357,
        "benchmark_rows": 302,
        "rendered_pages": 7,
        "corpus_expressions": 295,
        "corpus_statuses": {
            "PASS": 17,
            "FAIL": 1,
            "BLOCKED": 0,
        },
        "checks": checks,
    }
    SUMMARY.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY.write_text(
        json.dumps(result, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    print(
        f"P10-VALIDATION status={status} "
        f"checks={len(checks)} tests=357 expressions=42 pages=7"
    )
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
