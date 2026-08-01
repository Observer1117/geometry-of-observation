#!/usr/bin/env python3
"""Validate the complete P6 gear-contact release candidate."""

from __future__ import annotations

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
P6 = ROOT / "work/p6_gear_contact_v0_7"

PDF = P6 / "build/gear/gear_contact_geometry_v1_1.pdf"
TEX = P6 / "src/gear_contact_geometry_v1_1.tex"
TEXT = P6 / "checks/gear/gear_contact_geometry_v1_1.txt"
LOG = P6 / "build/gear/gear_contact_geometry_v1_1.log"
CONTRACT = P6 / "core/gear_contact_contract_v0_7.yaml"
REFERENCE_LEDGER = P6 / "ledgers/gear_contact_reference_ledger_v0_7.yaml"
CORPUS_LEDGER = P6 / "ledgers/corpus_ledgers_v0_7.yaml"
REFERENCE_LINT = P6 / "reports/Gear_Contact_Reference_Lint_Report_v0_7.json"
CORPUS_LINT = P6 / "reports/GO_Corpus_Lint_Report_v0_7.json"
MIGRATION_REPORT = P6 / "reports/P6_Gear_Contact_Migration_Report_v0_7_ru.md"
VISUAL_QA = P6 / "reports/P6_Visual_QA_v0_7.yaml"
TEST_FILE = P6 / "tests/test_gear_contact_v0_7.py"
GO_LINT = ROOT / "work/go_core_v0_2/src/go_lint.py"
GO_CORE = ROOT / "work/go_core_v0_2/core"
SUMMARY = P6 / "reports/P6_Validation_Summary_v0_7.json"


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
            "schema": {"id": "go-p6-validation-summary", "version": "0.7.0"},
            "date": str(date.today()),
            "status": "FAIL",
            "checks": checks,
        }
        SUMMARY.parent.mkdir(parents=True, exist_ok=True)
        SUMMARY.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
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
        == "Gear Contact Geometry as a Typed Finite Observation System"
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
            count = path.read_text(encoding="utf-8", errors="replace").count(token)
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
    record(
        "bibliography_heading_unique",
        heading_count == 1 and r"\section*{References}" not in source_text,
        {
            "extracted_heading_count": heading_count,
            "explicit_heading_in_source": r"\section*{References}" in source_text,
        },
    )

    fragments = [
        r"\section{Finite pitch-event dynamics}",
        r"\section{Contact force, sliding, and dissipation}",
        r"\section{Planetary frames as an explicit group action}",
        r"\section{Periodic non-circular kinematics}",
        r"\widetilde F(x+2\pi)=\widetilde F(x)+2\pi",
        r"P_{\rm fric}",
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
        contract["schema"]["id"] == "go-gear-contact-contract"
        and contract["schema"]["version"] == "0.7.0"
        and contract["orientation_convention"]["directed_ratio"]
        == "rho_2_from_1 = omega2/omega1 = sigma*N1/N2"
        and contract["contact_convention"]["sliding"]["nonnegative_loss"]
        == "P_fric_alpha = -dot(T_alpha,v_T_alpha) >= 0"
        and contract["planetary_frame_action"]["action"]
        == "G_alpha(omega) = omega - alpha*(1,1,1)"
        and contract["periodic_noncircular_model"]["return_lift"]["degree_one"]
        == "F_tilde(x+2*pi) = F_tilde(x)+2*pi"
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
        and reference_summary["expressions_checked"] == 20
        and reference_summary["findings_total"] == 0
        and reference_summary["status_counts"] == {"PASS": 1}
    )
    record("reference_lint", reference_ok, reference_summary)

    corpus_summary = load_json(CORPUS_LINT)["summary"]
    corpus_ok = (
        corpus_summary["canonical_documents"] == 18
        and corpus_summary["reference_documents"] == 13
        and corpus_summary["critical_adapters"] == 5
        and corpus_summary["expressions_checked"] == 151
        and corpus_summary["findings_total"] == 15
        and corpus_summary["status_counts"] == {"FAIL": 5, "PASS": 13}
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
        "gear-contact-v1" not in corpus_ids
        and "gear-contact-v1-1" in corpus_ids
        and "gear-contact-v1-1" in superseded_targets
    )
    record(
        "gear_supersession",
        supersession_ok,
        {
            "old_present": "gear-contact-v1" in corpus_ids,
            "new_present": "gear-contact-v1-1" in corpus_ids,
            "target_recorded": "gear-contact-v1-1" in superseded_targets,
        },
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
    reference_run_ok = (
        reference_process.returncode == 0
        and "documents=1" in reference_process.stdout
        and "expressions=20" in reference_process.stdout
        and "findings=0" in reference_process.stdout
    )
    record(
        "reference_strict_run",
        reference_run_ok,
        {
            "returncode": reference_process.returncode,
            "stdout": reference_process.stdout.strip(),
            "stderr": reference_process.stderr.strip(),
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
    corpus_run_ok = (
        corpus_process.returncode != 0
        and "documents=18" in corpus_process.stdout
        and "expressions=151" in corpus_process.stdout
        and "findings=15" in corpus_process.stdout
        and "'FAIL': 5" in corpus_process.stdout
        and "'PASS': 13" in corpus_process.stdout
    )
    record(
        "corpus_strict_expected_failure",
        corpus_run_ok,
        {
            "returncode": corpus_process.returncode,
            "stdout": corpus_process.stdout.strip(),
            "stderr": corpus_process.stderr.strip(),
            "interpretation": "five retained legacy adapters fail by design",
        },
    )

    tests_process = run(
        [
            "python3",
            "-m",
            "unittest",
            "-q",
            str(TEST_FILE.relative_to(ROOT)).replace("/", ".")[:-3],
        ]
    )
    tests_output = tests_process.stdout + tests_process.stderr
    match = re.search(r"Ran\s+(\d+)\s+tests", tests_output)
    tests_run = int(match.group(1)) if match else None
    tests_ok = (
        tests_process.returncode == 0
        and tests_run == 55
        and re.search(r"\bOK\b", tests_output) is not None
    )
    record(
        "regression_tests",
        tests_ok,
        {
            "returncode": tests_process.returncode,
            "tests_run": tests_run,
            "tail": tests_output.strip().splitlines()[-4:],
        },
    )

    visual = load_yaml(VISUAL_QA)
    visual_ok = (
        visual["document"]["status"] == "PASS"
        and visual["document"]["pages"] == 9
        and visual["document"]["inspected_pages"] == list(range(1, 10))
        and not visual["document"]["findings"]
        and all(
            value is False
            for value in visual["document"]["checks"].values()
        )
    )
    record(
        "visual_qa",
        visual_ok,
        {
            "status": visual["document"]["status"],
            "pages": visual["document"]["pages"],
            "findings": visual["document"]["findings"],
        },
    )

    status = "PASS" if all(item["status"] == "PASS" for item in checks) else "FAIL"
    result = {
        "schema": {
            "id": "go-p6-validation-summary",
            "version": "0.7.0",
        },
        "date": str(date.today()),
        "status": status,
        "summary": {
            "checks_passed": sum(item["status"] == "PASS" for item in checks),
            "checks_total": len(checks),
            "pdf_pages": 9,
            "typed_expressions": 20,
            "reference_findings": 0,
            "regression_tests": 55,
            "corpus_statuses": {"PASS": 13, "FAIL": 5, "BLOCKED": 0},
        },
        "checks": checks,
    }
    SUMMARY.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY.write_text(
        json.dumps(result, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    print(f"P6-VALIDATION status={status} checks={len(checks)}")
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
