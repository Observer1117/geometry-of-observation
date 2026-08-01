#!/usr/bin/env python3
"""Validate the complete P3 Planck-to-cosmos release candidate."""

from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import Any

import yaml
from PIL import Image
from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[3]
P3 = ROOT / "work/p3_planck_cosmos_v0_4"
PDF = P3 / "build/planck/planck_cosmos_observation_rulers_v1_1.pdf"
TEX = P3 / "src/planck_cosmos_observation_rulers_v1_1.tex"
TEXT = P3 / "checks/planck/planck_cosmos_observation_rulers_v1_1.txt"
LOG = P3 / "build/planck/planck_cosmos_observation_rulers_v1_1.log"
INPUT = P3 / "data/planck_cosmos_inputs_v0_4.yaml"
CSV_PATH = P3 / "data/planck_cosmos_landmarks_v0_4.csv"
METRICS = P3 / "data/planck_cosmos_metrics_v0_4.json"
CONTRACT = P3 / "core/planck_cosmos_scale_contract_v0_4.yaml"
LEDGER = P3 / "ledgers/planck_cosmos_reference_ledger_v0_4.yaml"
CORPUS_LEDGER = P3 / "ledgers/corpus_ledgers_v0_4.yaml"
REFERENCE_LINT = P3 / "reports/Planck_Cosmos_Lint_Report_v0_4.json"
CORPUS_LINT = P3 / "reports/GO_Corpus_Lint_Report_v0_4.json"
SUMMARY = P3 / "reports/P3_Validation_Summary_v0_4.json"
CONTACT_SHEET = P3 / "checks/planck/contact.png"
PAGE_IMAGES = sorted((P3 / "checks/planck").glob("page-*.png"))


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
        INPUT,
        CSV_PATH,
        METRICS,
        CONTRACT,
        LEDGER,
        CORPUS_LEDGER,
        REFERENCE_LINT,
        CORPUS_LINT,
        CONTACT_SHEET,
    ]
    missing = [str(path.relative_to(ROOT)) for path in required_files if not path.is_file()]
    record("required_files", not missing, {"missing": missing})

    if missing:
        report = {
            "schema": {"id": "go-p3-validation-summary", "version": "0.4.0"},
            "date": str(date.today()),
            "status": "FAIL",
            "checks": checks,
        }
        SUMMARY.parent.mkdir(parents=True, exist_ok=True)
        SUMMARY.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        return 1

    ledger = load_yaml(LEDGER)
    document = ledger["documents"][0]
    expected_hash = document["source"]["sha256"]
    actual_hash = sha256(PDF)
    record(
        "pdf_sha256",
        actual_hash == expected_hash,
        {"expected": expected_hash, "actual": actual_hash},
    )

    reader = PdfReader(PDF)
    metadata = reader.metadata or {}
    page_count = len(reader.pages)
    title = metadata.get("/Title")
    record(
        "pdf_metadata",
        page_count == 12 and title == "Planck-to-Cosmos Observation Rulers",
        {"pages": page_count, "title": title},
    )

    source_text = TEX.read_text(encoding="utf-8")
    extracted_text = TEXT.read_text(encoding="utf-8")
    prohibited = ("TODO", "TBD", "\ufffd")
    prohibited_hits = {
        token: {
            "tex": source_text.count(token),
            "text": extracted_text.count(token),
        }
        for token in prohibited
        if token in source_text or token in extracted_text
    }
    record("no_prohibited_tokens", not prohibited_hits, prohibited_hits)

    required_fragments = [
        r"\section{Typed scale data and the two-passport rule}",
        r"\section{The logarithmic scale chart}",
        r"\section{Descriptor coordinates versus resolution coordinates}",
        r"\subsection{Planck identities}",
        r"\section{Cosmological landmarks are typed model outputs}",
        r"\section{Normative reporting contract}",
        r"\section{Claim audit}",
        r"\chi_L=-\chi_M",
        r"\chi_L=\chi_M+\log_b2",
    ]
    absent_fragments = [fragment for fragment in required_fragments if fragment not in source_text]
    record("required_source_fragments", not absent_fragments, {"absent": absent_fragments})

    log_text = LOG.read_text(encoding="utf-8", errors="replace")
    forbidden_log_patterns = [
        "Overfull",
        "LaTeX Warning",
        "undefined references",
        "multiply defined",
        "Fatal error",
    ]
    log_hits = [pattern for pattern in forbidden_log_patterns if pattern in log_text]
    record("latex_log", not log_hits, {"forbidden_patterns": log_hits})

    font_process = run(["pdffonts", str(PDF)])
    font_rows = [
        line.split()
        for line in font_process.stdout.splitlines()[2:]
        if line.strip()
    ]
    nonembedded = [
        row[0]
        for row in font_rows
        if len(row) >= 6 and row[-4].lower() != "yes"
    ]
    record(
        "embedded_fonts",
        font_process.returncode == 0 and bool(font_rows) and not nonembedded,
        {
            "font_count": len(font_rows),
            "nonembedded": nonembedded,
            "returncode": font_process.returncode,
        },
    )

    image_details: list[dict[str, Any]] = []
    image_paths = PAGE_IMAGES + [CONTACT_SHEET]
    image_error = False
    for image_path in image_paths:
        try:
            with Image.open(image_path) as image:
                image.verify()
            with Image.open(image_path) as image:
                width, height = image.size
            image_details.append(
                {
                    "file": image_path.name,
                    "width": width,
                    "height": height,
                }
            )
            image_error = image_error or width <= 0 or height <= 0
        except Exception as exc:  # pragma: no cover - diagnostic path
            image_error = True
            image_details.append({"file": image_path.name, "error": str(exc)})
    record(
        "rendered_pages",
        len(PAGE_IMAGES) == 12 and len(image_paths) == 13 and not image_error,
        {"page_images": len(PAGE_IMAGES), "images": image_details},
    )

    with CSV_PATH.open("r", encoding="utf-8", newline="") as stream:
        catalogue_rows = list(csv.DictReader(stream))
    axes = sorted({row["axis"] for row in catalogue_rows})
    record(
        "catalogue",
        len(catalogue_rows) == 24 and axes == ["length", "mass", "time"],
        {"rows": len(catalogue_rows), "axes": axes},
    )

    metrics = load_json(METRICS)
    contract = load_yaml(CONTRACT)
    record(
        "schema_versions",
        metrics["schema"]["version"] == "0.4.0"
        and contract["schema"]["version"] == "0.4.0"
        and ledger["schema"]["version"] == "0.4.0",
        {
            "metrics": metrics["schema"]["version"],
            "contract": contract["schema"]["version"],
            "ledger": ledger["schema"]["version"],
        },
    )

    reference_report = load_json(REFERENCE_LINT)
    reference_summary = reference_report["summary"]
    record(
        "reference_lint",
        reference_summary["findings_total"] == 0
        and reference_summary["status_counts"] == {"PASS": 1}
        and reference_summary["expressions_checked"] == 19,
        reference_summary,
    )

    corpus_report = load_json(CORPUS_LINT)
    corpus_summary = corpus_report["summary"]
    expected_statuses = {"BLOCKED": 1, "FAIL": 9, "PASS": 7}
    record(
        "corpus_lint",
        corpus_summary["canonical_documents"] == 17
        and corpus_summary["expressions_checked"] == 86
        and corpus_summary["status_counts"] == expected_statuses,
        {
            "canonical_documents": corpus_summary["canonical_documents"],
            "expressions_checked": corpus_summary["expressions_checked"],
            "status_counts": corpus_summary["status_counts"],
        },
    )

    test_process = run(
        [
            sys.executable,
            "-m",
            "unittest",
            "-v",
            "work.p3_planck_cosmos_v0_4.tests.test_planck_cosmos_v0_4",
        ]
    )
    test_output = test_process.stdout + test_process.stderr
    record(
        "regression_tests",
        test_process.returncode == 0
        and "Ran 29 tests" in test_output
        and "\nOK" in test_output,
        {
            "returncode": test_process.returncode,
            "ran": 29 if "Ran 29 tests" in test_output else None,
            "result": "OK" if "\nOK" in test_output else "not OK",
        },
    )

    failed = [check["id"] for check in checks if check["status"] == "FAIL"]
    report = {
        "schema": {"id": "go-p3-validation-summary", "version": "0.4.0"},
        "date": str(date.today()),
        "release": "GO P3 Planck-to-Cosmos v0.4",
        "status": "PASS" if not failed else "FAIL",
        "summary": {
            "checks_total": len(checks),
            "checks_passed": len(checks) - len(failed),
            "checks_failed": len(failed),
            "pdf_pages": page_count,
            "typed_expressions": reference_summary["expressions_checked"],
            "regression_tests": 29,
            "catalogue_rows": len(catalogue_rows),
            "reference_findings": reference_summary["findings_total"],
            "corpus_status_counts": corpus_summary["status_counts"],
        },
        "artifacts": {
            "pdf": str(PDF.relative_to(ROOT)),
            "pdf_sha256": actual_hash,
            "source": str(TEX.relative_to(ROOT)),
            "contract": str(CONTRACT.relative_to(ROOT)),
            "reference_ledger": str(LEDGER.relative_to(ROOT)),
            "catalogue": str(CSV_PATH.relative_to(ROOT)),
        },
        "checks": checks,
    }
    SUMMARY.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(
        f"{report['status']}: {len(checks) - len(failed)}/{len(checks)} checks, "
        f"{page_count} pages, 29 tests, {len(catalogue_rows)} catalogue rows"
    )
    if failed:
        print("Failed checks: " + ", ".join(failed))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
