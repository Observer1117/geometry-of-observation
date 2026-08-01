#!/usr/bin/env python3
"""Validate the complete P8 conical-intersections release candidate."""

from __future__ import annotations

import csv
import hashlib
import json
import re
import subprocess
from datetime import date
from pathlib import Path
from typing import Any

import yaml
from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[3]
P8 = ROOT / "work/p8_conical_intersections_v0_9"

PDF = P8 / "build/ci/conical_intersections_spectral_observation_v1_1.pdf"
TEX = P8 / "src/conical_intersections_spectral_observation_v1_1.tex"
TEXT = P8 / "checks/ci/conical_intersections_spectral_observation_v1_1.txt"
LOG = P8 / "build/ci/conical_intersections_spectral_observation_v1_1.log"
CONTRACT = (
    P8 / "core/conical_intersections_observation_contract_v0_9.yaml"
)
REFERENCE_LEDGER = (
    P8 / "ledgers/conical_intersections_reference_ledger_v0_9.yaml"
)
CORPUS_LEDGER = P8 / "ledgers/corpus_ledgers_v0_9.yaml"
REFERENCE_LINT = (
    P8 / "reports/Conical_Intersections_Reference_Lint_Report_v0_9.json"
)
CORPUS_LINT = P8 / "reports/GO_Corpus_Lint_Report_v0_9.json"
MIGRATION_REPORT = (
    P8 / "reports/P8_Conical_Intersections_Migration_Report_v0_9_ru.md"
)
VISUAL_QA = P8 / "reports/P8_Visual_QA_v0_9.yaml"
BENCHMARKS = P8 / "data/conical_intersections_benchmarks_v0_9.csv"
METRICS = P8 / "data/conical_intersections_metrics_v0_9.json"
TEST_FILE = P8 / "tests/test_conical_intersections_v0_9.py"
GO_LINT = ROOT / "work/go_core_v0_2/src/go_lint.py"
GO_CORE = ROOT / "work/go_core_v0_2/core"
SUMMARY = P8 / "reports/P8_Validation_Summary_v0_9.json"
RENDER_DIR = P8 / "render/ci"


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
                "id": "go-p8-validation-summary",
                "version": "0.9.0",
            },
            "date": str(date.today()),
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
        len(reader.pages) == 8
        and metadata.get("/Title")
        == "Conical Intersections as Typed Spectral Singularities under Observation Maps"
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
    pdf_security_ok = (
        not reader.is_encrypted
        and reader.get_fields() in (None, {})
        and abs(width - 595.28) < 0.2
        and abs(height - 841.89) < 0.2
    )
    record(
        "pdf_security_and_page_size",
        pdf_security_ok,
        {
            "encrypted": reader.is_encrypted,
            "form_fields": len(reader.get_fields() or {}),
            "page_size_points": [width, height],
        },
    )

    prohibited_hits: dict[str, dict[str, int]] = {}
    for token in ("TODO", "TBD", "\ufffd"):
        hits: dict[str, int] = {}
        for path in (TEX, TEXT, MIGRATION_REPORT):
            count = path.read_text(
                encoding="utf-8", errors="replace"
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

    required_fragments = [
        r"\section{Projectors, eigenlines, and gauge}",
        r"\section{Berry holonomy without a global eigenvector}",
        r"\section{Derivative coupling and quantum metric}",
        r"\section{Born--Oppenheimer reduction and dynamics firewall}",
        r"\section{Observation chain and finite-resolution identifiability}",
        r"P_{\rm cl}=P_++P_-=I_2",
        r"d_{+-}^{(q)}=J^\mathsf T d_{+-}^{(E)}",
        r"P_{\rm D}=\exp",
        r"\sigma_\Delta^2",
        r"H_\delta(x,y)=x\sigma_z+y\sigma_x+\delta\sigma_y",
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
        if len(row) < 6 or row[-4].lower() != "yes"
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
        == "go-conical-intersections-observation-contract"
        and contract["schema"]["version"] == "0.9.0"
        and len(contract["reference_gates"]) == 12
        and contract["real_two_state_normal_form"]["seam"][
            "codimension_two_hypothesis"
        ]
        == "rank(D_q(x,y)) = 2"
        and contract["nonadiabatic_geometry"]["physical_pullback"][
            "dimensions"
        ]["d_q"]
        == "inverse_length"
    )
    record(
        "contract_schema_and_gates",
        contract_ok,
        {
            "schema": contract["schema"],
            "reference_gate_count": len(contract["reference_gates"]),
        },
    )

    firewall_ok = (
        contract["spectral_cluster"]["internal_splitting"][
            "behavior_at_seam"
        ]["rank_one_projectors"]
        == "no_unique_extension"
        and contract["spectral_cluster"]["internal_splitting"][
            "behavior_at_seam"
        ]["cluster_projector"]
        == "remains_defined"
        and contract["spectral_discriminant"]["caustic_language"][
            "formal_status"
        ]
        == "analogy"
        and "static_gap_does_not_determine_transition_probability"
        in contract["born_oppenheimer_dynamics"]["prohibition"]
        and contract["finite_resolution"]["rule_semantics"]
        == "unresolved_near_degeneracy_not_exact_CI_certificate"
    )
    record("contract_layer_firewalls", firewall_ok, firewall_ok)

    reference_summary = load_json(REFERENCE_LINT)["summary"]
    reference_ok = (
        reference_summary["canonical_documents"] == 1
        and reference_summary["reference_documents"] == 1
        and reference_summary["critical_adapters"] == 0
        and reference_summary["expressions_checked"] == 36
        and reference_summary["findings_total"] == 0
        and reference_summary["status_counts"] == {"PASS": 1}
    )
    record("reference_lint", reference_ok, reference_summary)

    corpus_report = load_json(CORPUS_LINT)
    corpus_summary = corpus_report["summary"]
    corpus_ok = (
        corpus_summary["canonical_documents"] == 18
        and corpus_summary["reference_documents"] == 15
        and corpus_summary["critical_adapters"] == 3
        and corpus_summary["expressions_checked"] == 208
        and corpus_summary["findings_total"] == 8
        and corpus_summary["status_counts"] == {"FAIL": 3, "PASS": 15}
    )
    record("corpus_lint", corpus_ok, corpus_summary)

    failing_ids = sorted(
        item["id"]
        for item in corpus_report["documents"]
        if item["status"] != "PASS"
    )
    expected_failing_ids = sorted(
        [
            "quantum-chemistry-observation-v1",
            "regular-polyhedra-v1",
            "satellite-networks-v1-1",
        ]
    )
    record(
        "expected_remaining_failures",
        failing_ids == expected_failing_ids,
        {"actual": failing_ids, "expected": expected_failing_ids},
    )

    corpus = load_yaml(CORPUS_LEDGER)
    ids = [item["id"] for item in corpus["documents"]]
    legacy_records = [
        item
        for item in corpus["duplicate_or_superseded_sources"]
        if "conical_intersections" in item.get("path", "")
    ]
    supersession_ok = (
        len(ids) == 18
        and len(set(ids)) == 18
        and "conical-intersections-v1" not in ids
        and "conical-intersections-observation-v1-1" in ids
        and len(legacy_records) == 2
        and all(
            item.get("status") == "superseded"
            and item.get("canonical_document")
            == "conical-intersections-observation-v1-1"
            for item in legacy_records
        )
    )
    record(
        "legacy_supersession",
        supersession_ok,
        {"legacy_records": legacy_records},
    )

    with BENCHMARKS.open("r", encoding="utf-8", newline="") as stream:
        benchmark_rows = list(csv.DictReader(stream))
    family_counts: dict[str, int] = {}
    for row in benchmark_rows:
        family_counts[row["family"]] = family_counts.get(row["family"], 0) + 1
    expected_family_counts = {
        "derivative_coupling": 6,
        "finite_resolution": 4,
        "gapped_berry": 6,
        "landau_zener": 6,
        "real_holonomy": 7,
        "spectrum": 6,
    }
    benchmark_ok = (
        len(benchmark_rows) == 35
        and family_counts == expected_family_counts
    )
    record(
        "benchmark_table",
        benchmark_ok,
        {"rows": len(benchmark_rows), "families": family_counts},
    )

    metrics = load_json(METRICS)
    residuals_ok = (
        metrics["benchmark_rows"] == 35
        and metrics["max_projector_idempotence_residual"] < 1e-14
        and metrics["max_projector_orthogonality_residual"] < 1e-14
        and metrics["max_quantum_metric_identity_residual"] < 1e-12
        and metrics["max_random_gauge_holonomy_residual"] < 1e-12
        and metrics["max_gapped_berry_discretization_error"] < 3e-7
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
    tests_ok = tests_process.returncode == 0 and test_count == 150
    record(
        "regression_suite",
        tests_ok,
        {
            "returncode": tests_process.returncode,
            "tests": test_count,
            "tail": tests_output[-400:],
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
        and "statuses={'FAIL': 3, 'PASS': 15}"
        in corpus_replay.stdout,
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
        and visual["document"]["pages"] == 8
        and len(visual["inspection"]["pages"]) == 8
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
    render_ok = len(rendered_pages) == 8 and all(
        path.stat().st_size > 100_000 for path in rendered_pages
    )
    record(
        "rendered_pages",
        render_ok,
        {
            "count": len(rendered_pages),
            "files": [path.name for path in rendered_pages],
        },
    )

    report_text = MIGRATION_REPORT.read_text(
        encoding="utf-8", errors="replace"
    )
    report_fragments = [
        "Глобальный собственный вектор",
        "Смешение ядерных и энергетических координат",
        "Gauge-covariant derivative coupling",
        "Статическая геометрия и динамика",
        "Конечное спектральное разрешение",
        "15 PASS / 3 FAIL / 0 BLOCKED",
        "Следующий прямой кандидат — `Quantum Chemistry",
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

    primary_dois = [
        "10.1002/andp.19273892002",
        "10.1098/rspa.1958.0022",
        "10.1039/DF9633500077",
        "10.1063/1.437734",
        "10.1098/rspa.1984.0023",
        "10.1098/rspa.1932.0165",
    ]
    missing_dois = [doi for doi in primary_dois if doi not in source]
    record(
        "primary_reference_identifiers",
        not missing_dois,
        {"missing": missing_dois},
    )

    status = (
        "PASS"
        if checks and all(item["status"] == "PASS" for item in checks)
        else "FAIL"
    )
    result = {
        "schema": {
            "id": "go-p8-validation-summary",
            "version": "0.9.0",
        },
        "date": "2026-07-28",
        "status": status,
        "release_check_count": len(checks),
        "typed_expressions": 36,
        "regression_tests": 150,
        "benchmark_rows": 35,
        "rendered_pages": 8,
        "corpus_statuses": {
            "PASS": 15,
            "FAIL": 3,
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
        f"P8-VALIDATION status={status} "
        f"checks={len(checks)} tests=150 expressions=36 pages=8"
    )
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
