#!/usr/bin/env python3
"""Validate the complete P7 billiards release candidate."""

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
P7 = ROOT / "work/p7_billiards_v0_8"

PDF = P7 / "build/billiards/billiards_observation_laboratory_v1_1.pdf"
TEX = P7 / "src/billiards_observation_laboratory_v1_1.tex"
TEXT = P7 / "checks/billiards/billiards_observation_laboratory_v1_1.txt"
LOG = P7 / "build/billiards/billiards_observation_laboratory_v1_1.log"
CONTRACT = P7 / "core/billiards_observation_contract_v0_8.yaml"
REFERENCE_LEDGER = P7 / "ledgers/billiards_reference_ledger_v0_8.yaml"
CORPUS_LEDGER = P7 / "ledgers/corpus_ledgers_v0_8.yaml"
REFERENCE_LINT = (
    P7 / "reports/Billiards_Reference_Lint_Report_v0_8.json"
)
CORPUS_LINT = P7 / "reports/GO_Corpus_Lint_Report_v0_8.json"
MIGRATION_REPORT = (
    P7 / "reports/P7_Billiards_Migration_Report_v0_8_ru.md"
)
VISUAL_QA = P7 / "reports/P7_Visual_QA_v0_8.yaml"
BENCHMARKS = P7 / "data/billiards_benchmarks_v0_8.csv"
METRICS = P7 / "data/billiards_metrics_v0_8.json"
TEST_FILE = P7 / "tests/test_billiards_v0_8.py"
GO_LINT = ROOT / "work/go_core_v0_2/src/go_lint.py"
GO_CORE = ROOT / "work/go_core_v0_2/core"
SUMMARY = P7 / "reports/P7_Validation_Summary_v0_8.json"


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
            "schema": {"id": "go-p7-validation-summary", "version": "0.8.0"},
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

    ledger_document = load_yaml(REFERENCE_LEDGER)["documents"][0]
    expected_hash = ledger_document["source"]["sha256"]
    actual_hash = sha256(PDF)
    record(
        "pdf_sha256",
        expected_hash == actual_hash,
        {"expected": expected_hash, "actual": actual_hash},
    )

    reader = PdfReader(PDF)
    metadata = reader.metadata or {}
    pdf_metadata_ok = (
        len(reader.pages) == 9
        and metadata.get("/Title")
        == "Billiards as a Typed Geometry of Observation Laboratory"
        and metadata.get("/Author") == "Stas, Independent Research Program"
    )
    record(
        "pdf_metadata",
        pdf_metadata_ok,
        {
            "pages": len(reader.pages),
            "title": metadata.get("/Title"),
            "author": metadata.get("/Author"),
        },
    )

    prohibited_hits: dict[str, dict[str, int]] = {}
    for token in ("TODO", "TBD", "\ufffd"):
        token_hits: dict[str, int] = {}
        for path in (TEX, TEXT, MIGRATION_REPORT):
            count = path.read_text(encoding="utf-8", errors="replace").count(
                token
            )
            if count:
                token_hits[path.name] = count
        if token_hits:
            prohibited_hits[token] = token_hits
    record("no_prohibited_tokens", not prohibited_hits, prohibited_hits)

    extracted = TEXT.read_text(encoding="utf-8", errors="replace")
    heading_count = sum(
        line.strip() == "References" for line in extracted.splitlines()
    )
    source_text = TEX.read_text(encoding="utf-8")
    source_heading_count = source_text.count(r"\section*{References}")
    record(
        "bibliography_heading_unique",
        heading_count == 1 and source_heading_count == 1,
        {
            "extracted_heading_count": heading_count,
            "source_heading_count": source_heading_count,
        },
    )

    fragments = [
        r"\section{Collision space, singularities, and invariant measure}",
        r"\section{Impact-position observation and identifiability}",
        r"\section{Finite symbolic channels and entropy semantics}",
        r"\section{Quantum billiards: operator, dimensions, and spectrum}",
        r"\dd\mu_\partial",
        r"E_n=\frac{\hbar^2}{2m}\lambda_n",
        r"q\times v=c_0j_z",
    ]
    absent_fragments = [item for item in fragments if item not in source_text]
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
        contract["schema"]["id"] == "go-billiards-observation-contract"
        and contract["schema"]["version"] == "0.8.0"
        and len(contract["reference_gates"]) == 10
        and contract["collision_section"]["collision_map"]["invertible"]
        == "almost_everywhere_outside_forward_backward_singular_sets"
        and contract["spectral_layer"]["physical_hamiltonian"]["energy_bridge"]
        == "E_n = hbar^2*lambda_n/(2*m)"
        and contract["disk_reference"][
            "conserved_reduced_angular_momentum_coordinate"
        ]
        == "j_z = R*p"
    )
    record(
        "contract_schema_and_gates",
        contract_ok,
        {
            "schema": contract["schema"],
            "reference_gate_count": len(contract["reference_gates"]),
        },
    )

    reference_summary = load_json(REFERENCE_LINT)["summary"]
    reference_ok = (
        reference_summary["canonical_documents"] == 1
        and reference_summary["reference_documents"] == 1
        and reference_summary["critical_adapters"] == 0
        and reference_summary["expressions_checked"] == 24
        and reference_summary["findings_total"] == 0
        and reference_summary["status_counts"] == {"PASS": 1}
    )
    record("reference_lint", reference_ok, reference_summary)

    corpus_summary = load_json(CORPUS_LINT)["summary"]
    corpus_ok = (
        corpus_summary["canonical_documents"] == 18
        and corpus_summary["reference_documents"] == 14
        and corpus_summary["critical_adapters"] == 4
        and corpus_summary["expressions_checked"] == 173
        and corpus_summary["findings_total"] == 12
        and corpus_summary["status_counts"] == {"FAIL": 4, "PASS": 14}
    )
    record("corpus_lint", corpus_ok, corpus_summary)

    corpus = load_yaml(CORPUS_LEDGER)
    corpus_ids = {item["id"] for item in corpus["documents"]}
    superseded_targets = {
        item.get("canonical_document")
        for item in corpus["duplicate_or_superseded_sources"]
        if item.get("status") == "superseded"
    }
    supersession_ok = (
        corpus["schema"]["canonical_documents"] == 18
        and "billiards-observation-v1" not in corpus_ids
        and "billiards-observation-v1-1" in corpus_ids
        and "billiards-observation-v1-1" in superseded_targets
    )
    record(
        "billiards_supersession",
        supersession_ok,
        {
            "document_count": len(corpus_ids),
            "legacy_present": "billiards-observation-v1" in corpus_ids,
            "reference_present": "billiards-observation-v1-1" in corpus_ids,
        },
    )

    visual = load_yaml(VISUAL_QA)
    visual_document = visual["document"]
    visual_ok = (
        visual_document["status"] == "PASS"
        and visual_document["pages"] == 9
        and visual_document["inspected_pages"] == list(range(1, 10))
        and not visual_document["findings"]
        and all(
            value is False
            for value in visual_document["checks"].values()
        )
    )
    record(
        "visual_qa",
        visual_ok,
        {
            "pages": visual_document["pages"],
            "inspected_pages": visual_document["inspected_pages"],
            "findings": visual_document["findings"],
        },
    )

    with BENCHMARKS.open("r", encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    quantity_names = {row["quantity"] for row in rows}
    benchmark_ok = (
        len(rows) == 18
        and "reduced_angular_momentum_coordinate" in quantity_names
        and "lambda_11" in quantity_names
        and "electron_energy_11" in quantity_names
    )
    record(
        "benchmark_table",
        benchmark_ok,
        {"rows": len(rows), "quantities": sorted(quantity_names)},
    )

    metrics = load_json(METRICS)
    metric_values = metrics["metrics"]
    metrics_ok = (
        metrics["row_count"] == 18
        and abs(metric_values["integral_mu_boundary_1"] - 1.0) < 1e-15
        and abs(metric_values["lambda_scaling_ratio_1"] - 1.0 / 9.0)
        < 1e-15
        and abs(
            metric_values["reduced_angular_momentum_coordinate_m"] - 0.92
        )
        < 1e-15
    )
    record(
        "benchmark_metrics",
        metrics_ok,
        {
            "row_count": metrics["row_count"],
            "normalization": metric_values["integral_mu_boundary_1"],
            "scale_ratio": metric_values["lambda_scaling_ratio_1"],
        },
    )

    tests_process = run(
        ["python3", "-m", "unittest", "-v", str(TEST_FILE)]
    )
    test_output = tests_process.stdout + tests_process.stderr
    match = re.search(r"Ran (\d+) tests?", test_output)
    test_count = int(match.group(1)) if match else 0
    tests_ok = tests_process.returncode == 0 and test_count == 95
    record(
        "regression_suite",
        tests_ok,
        {"tests": test_count, "returncode": tests_process.returncode},
    )

    reference_process = run(
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
        "strict_reference_gate",
        reference_process.returncode == 0
        and "findings=0" in reference_process.stdout,
        {
            "returncode": reference_process.returncode,
            "stdout": reference_process.stdout.strip(),
        },
    )

    corpus_process = run(
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
    corpus_strict_ok = (
        corpus_process.returncode != 0
        and "findings=12" in corpus_process.stdout
        and "'FAIL': 4" in corpus_process.stdout
    )
    record(
        "strict_corpus_expected_failure",
        corpus_strict_ok,
        {
            "returncode": corpus_process.returncode,
            "stdout": corpus_process.stdout.strip(),
            "reason": "four retained legacy critical adapters",
        },
    )

    overall = all(item["status"] == "PASS" for item in checks)
    result = {
        "schema": {"id": "go-p7-validation-summary", "version": "0.8.0"},
        "date": str(date.today()),
        "status": "PASS" if overall else "FAIL",
        "summary": {
            "release_checks": len(checks),
            "release_checks_passed": sum(
                item["status"] == "PASS" for item in checks
            ),
            "pages": len(reader.pages),
            "typed_expressions": reference_summary["expressions_checked"],
            "reference_findings": reference_summary["findings_total"],
            "regression_tests": test_count,
            "benchmark_rows": len(rows),
            "rendered_pages": visual_document["pages"],
            "corpus_statuses": {
                "PASS": corpus_summary["status_counts"].get("PASS", 0),
                "FAIL": corpus_summary["status_counts"].get("FAIL", 0),
                "BLOCKED": corpus_summary["status_counts"].get("BLOCKED", 0),
            },
            "pdf_sha256": actual_hash,
        },
        "checks": checks,
    }
    SUMMARY.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY.write_text(
        json.dumps(result, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    print(
        f"P7-VALIDATE status={result['status']} "
        f"checks={sum(item['status'] == 'PASS' for item in checks)}/"
        f"{len(checks)} tests={test_count}"
    )
    return 0 if overall else 1


if __name__ == "__main__":
    raise SystemExit(main())
