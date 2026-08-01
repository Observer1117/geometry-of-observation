#!/usr/bin/env python3
"""Validate the complete P4 SI--HEP and LHC release candidate."""

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
P4 = ROOT / "work/p4_lhc_si_hep_v0_5"

PASSPORT_PDF = P4 / "build/passport/si_hep_quantity_passport_v0_5.pdf"
LHC_PDF = P4 / "build/lhc/lhc_beam_observation_geometry_v1_3.pdf"
PASSPORT_TEX = P4 / "src/si_hep_quantity_passport_v0_5.tex"
LHC_TEX = P4 / "src/lhc_beam_observation_geometry_v1_3.tex"
PASSPORT_TEXT = (
    P4 / "checks/passport_final/si_hep_quantity_passport_v0_5.txt"
)
LHC_TEXT = P4 / "checks/lhc/lhc_beam_observation_geometry_v1_3.txt"
PASSPORT_LOG = (
    P4 / "build/passport/si_hep_quantity_passport_v0_5.log"
)
LHC_LOG = P4 / "build/lhc/lhc_beam_observation_geometry_v1_3.log"
INPUT = P4 / "data/lhc_si_hep_inputs_v0_5.yaml"
CONVERSIONS = P4 / "data/si_hep_conversion_table_v0_5.csv"
METRICS = P4 / "data/lhc_si_hep_metrics_v0_5.json"
CONTRACT = P4 / "core/si_hep_quantity_passport_v0_5.yaml"
LEDGER = P4 / "ledgers/lhc_si_hep_reference_ledgers_v0_5.yaml"
CORPUS_LEDGER = P4 / "ledgers/corpus_ledgers_v0_5.yaml"
REFERENCE_LINT = P4 / "reports/LHC_SI_HEP_Lint_Report_v0_5.json"
CORPUS_LINT = P4 / "reports/GO_Corpus_Lint_Report_v0_5.json"
REPORT = P4 / "reports/P4_LHC_SI_HEP_Migration_Report_v0_5_ru.md"
SUMMARY = P4 / "reports/P4_Validation_Summary_v0_5.json"

PASSPORT_CONTACT = P4 / "checks/passport_final/contact.png"
LHC_CONTACT = P4 / "checks/lhc/contact.png"
PASSPORT_IMAGES = sorted(
    (P4 / "checks/passport_final").glob("page-*.png")
)
LHC_IMAGES = sorted((P4 / "checks/lhc").glob("page-*.png"))


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
        PASSPORT_PDF,
        LHC_PDF,
        PASSPORT_TEX,
        LHC_TEX,
        PASSPORT_TEXT,
        LHC_TEXT,
        PASSPORT_LOG,
        LHC_LOG,
        INPUT,
        CONVERSIONS,
        METRICS,
        CONTRACT,
        LEDGER,
        CORPUS_LEDGER,
        REFERENCE_LINT,
        CORPUS_LINT,
        REPORT,
        PASSPORT_CONTACT,
        LHC_CONTACT,
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
                "id": "go-p4-validation-summary",
                "version": "0.5.0",
            },
            "date": str(date.today()),
            "status": "FAIL",
            "checks": checks,
        }
        SUMMARY.parent.mkdir(parents=True, exist_ok=True)
        SUMMARY.write_text(
            json.dumps(result, indent=2) + "\n",
            encoding="utf-8",
        )
        return 1

    ledger = load_yaml(LEDGER)
    documents = {document["id"]: document for document in ledger["documents"]}
    expected_hashes = {
        "si-hep-quantity-passport-v0-5":
            documents["si-hep-quantity-passport-v0-5"]["source"]["sha256"],
        "lhc-beam-observation-v1-3":
            documents["lhc-beam-observation-v1-3"]["source"]["sha256"],
    }
    actual_hashes = {
        "si-hep-quantity-passport-v0-5": sha256(PASSPORT_PDF),
        "lhc-beam-observation-v1-3": sha256(LHC_PDF),
    }
    record(
        "pdf_sha256",
        expected_hashes == actual_hashes,
        {"expected": expected_hashes, "actual": actual_hashes},
    )

    pdf_expectations = [
        (
            PASSPORT_PDF,
            8,
            "SI-HEP Quantity Passport for Relativistic Beam Observation",
        ),
        (
            LHC_PDF,
            9,
            "Relativistic Beam Paths as Observation Geometry",
        ),
    ]
    pdf_details: list[dict[str, Any]] = []
    metadata_ok = True
    total_pages = 0
    for path, expected_pages, expected_title in pdf_expectations:
        reader = PdfReader(path)
        metadata = reader.metadata or {}
        page_count = len(reader.pages)
        title = metadata.get("/Title")
        total_pages += page_count
        metadata_ok = metadata_ok and (
            page_count == expected_pages and title == expected_title
        )
        pdf_details.append(
            {
                "file": path.name,
                "pages": page_count,
                "title": title,
            }
        )
    record("pdf_metadata", metadata_ok, pdf_details)

    source_pairs = [
        (PASSPORT_TEX, PASSPORT_TEXT),
        (LHC_TEX, LHC_TEXT),
    ]
    prohibited = ("TODO", "TBD", "\ufffd")
    prohibited_hits: dict[str, Any] = {}
    for token in prohibited:
        hits = {
            path.name: path.read_text(
                encoding="utf-8",
                errors="replace",
            ).count(token)
            for pair in source_pairs
            for path in pair
            if token in path.read_text(
                encoding="utf-8",
                errors="replace",
            )
        }
        if hits:
            prohibited_hits[token] = hits
    record("no_prohibited_tokens", not prohibited_hits, prohibited_hits)

    passport_source = PASSPORT_TEX.read_text(encoding="utf-8")
    lhc_source = LHC_TEX.read_text(encoding="utf-8")
    required_passport_fragments = [
        r"\section{Mechanical naturalization theorem}",
        r"\section{Four-momentum and invariant-mass passports}",
        r"\section{Exact accelerator bridges}",
        r"\section{Electromagnetic normalization boundary}",
        r"e_0=e/(1\,\mathrm C)",
        r"p[\GeV/c]=0.299792458",
    ]
    required_lhc_fragments = [
        r"\section{SI--HEP representation boundary}",
        r"\section{Transformation classes}",
        r"\section{Non-identifiability}",
        r"\varepsilon_n=\beta_{\rm rel}\gamma_{\rm rel}\varepsilon",
        "Long Shutdown 3",
        r"\section{Reproducible Run 3 numerical audit}",
    ]
    absent = [
        f"passport:{fragment}"
        for fragment in required_passport_fragments
        if fragment not in passport_source
    ] + [
        f"lhc:{fragment}"
        for fragment in required_lhc_fragments
        if fragment not in lhc_source
    ]
    record("required_source_fragments", not absent, {"absent": absent})

    incorrect_unit_notation = [
        token
        for token in (
            r"1\,\mathrm{eV}=e\,\mathrm J",
            r"1\,\GeV=10^9e\ \mathrm J",
        )
        if token in passport_source
    ]
    record(
        "unit_notation_boundary",
        not incorrect_unit_notation,
        {"prohibited_hits": incorrect_unit_notation},
    )

    forbidden_log_patterns = [
        "Overfull",
        "Underfull",
        "LaTeX Warning",
        "undefined references",
        "multiply defined",
        "Fatal error",
    ]
    log_details: dict[str, list[str]] = {}
    for log_path in (PASSPORT_LOG, LHC_LOG):
        log_text = log_path.read_text(encoding="utf-8", errors="replace")
        hits = [
            pattern
            for pattern in forbidden_log_patterns
            if pattern in log_text
        ]
        if hits:
            log_details[log_path.name] = hits
    record("latex_logs", not log_details, log_details)

    font_details: list[dict[str, Any]] = []
    fonts_ok = True
    for pdf_path in (PASSPORT_PDF, LHC_PDF):
        process = run(["pdffonts", str(pdf_path)])
        rows = [
            line.split()
            for line in process.stdout.splitlines()[2:]
            if line.strip()
        ]
        nonembedded = [
            row[0]
            for row in rows
            if len(row) >= 6 and row[-4].lower() != "yes"
        ]
        file_ok = (
            process.returncode == 0
            and bool(rows)
            and not nonembedded
        )
        fonts_ok = fonts_ok and file_ok
        font_details.append(
            {
                "file": pdf_path.name,
                "font_count": len(rows),
                "nonembedded": nonembedded,
                "returncode": process.returncode,
            }
        )
    record("embedded_fonts", fonts_ok, font_details)

    image_paths = (
        PASSPORT_IMAGES
        + LHC_IMAGES
        + [PASSPORT_CONTACT, LHC_CONTACT]
    )
    image_details: list[dict[str, Any]] = []
    image_error = False
    for image_path in image_paths:
        try:
            with Image.open(image_path) as image:
                image.verify()
            with Image.open(image_path) as image:
                width, height = image.size
            image_error = image_error or width <= 0 or height <= 0
            image_details.append(
                {
                    "file": str(image_path.relative_to(P4)),
                    "width": width,
                    "height": height,
                }
            )
        except Exception as exc:  # pragma: no cover - diagnostic path
            image_error = True
            image_details.append(
                {
                    "file": str(image_path.relative_to(P4)),
                    "error": str(exc),
                }
            )
    record(
        "rendered_pages",
        len(PASSPORT_IMAGES) == 8
        and len(LHC_IMAGES) == 9
        and len(image_paths) == 19
        and not image_error,
        {
            "passport_pages": len(PASSPORT_IMAGES),
            "lhc_pages": len(LHC_IMAGES),
            "images": image_details,
        },
    )

    with CONVERSIONS.open("r", encoding="utf-8", newline="") as stream:
        conversion_rows = list(csv.DictReader(stream))
    conversion_quantities = {
        row["quantity"]
        for row in conversion_rows
    }
    expected_quantities = {
        "energy",
        "mass",
        "momentum",
        "length",
        "duration",
        "area",
        "action",
        "force",
    }
    record(
        "conversion_table",
        len(conversion_rows) == 8
        and conversion_quantities == expected_quantities,
        {
            "rows": len(conversion_rows),
            "quantities": sorted(conversion_quantities),
        },
    )

    inputs = load_yaml(INPUT)
    metrics = load_json(METRICS)
    contract = load_yaml(CONTRACT)
    versions = {
        "inputs": inputs["schema"]["version"],
        "metrics": metrics["schema"]["version"],
        "contract": contract["schema"]["version"],
        "ledger": ledger["schema"]["version"],
    }
    record(
        "schema_versions",
        set(versions.values()) == {"0.5.0"},
        versions,
    )

    exactness = metrics["exactness"]
    lhc_audit = metrics["lhc_run3_audit"]
    exactness_ok = (
        "rigidity_coefficient_for_declared_units"
        in exactness["definition_exact"]
        and "proton_mass_energy" in exactness["measured"]
        and "beam_energy" in exactness["operational_or_rounded"]
        and lhc_audit["status_at_document_date"] == "Long_Shutdown_3"
    )
    record(
        "exactness_and_epoch",
        exactness_ok,
        {
            "exact": exactness["definition_exact"],
            "measured": exactness["measured"],
            "operational_or_rounded":
                exactness["operational_or_rounded"],
            "status_at_document_date":
                lhc_audit["status_at_document_date"],
        },
    )

    reference_report = load_json(REFERENCE_LINT)
    reference_summary = reference_report["summary"]
    record(
        "reference_lint",
        reference_summary["findings_total"] == 0
        and reference_summary["status_counts"] == {"PASS": 2}
        and reference_summary["expressions_checked"] == 28,
        reference_summary,
    )

    corpus_report = load_json(CORPUS_LINT)
    corpus_summary = corpus_report["summary"]
    record(
        "corpus_lint",
        corpus_summary["canonical_documents"] == 17
        and corpus_summary["reference_documents"] == 8
        and corpus_summary["critical_adapters"] == 9
        and corpus_summary["expressions_checked"] == 100
        and corpus_summary["status_counts"] == {
            "FAIL": 9,
            "PASS": 8,
        },
        corpus_summary,
    )

    corpus = load_yaml(CORPUS_LEDGER)
    corpus_ids = {document["id"] for document in corpus["documents"]}
    superseded = corpus.get("duplicate_or_superseded_sources", [])
    superseded_lhc = [
        item
        for item in superseded
        if item.get("canonical_document")
        == "lhc-beam-observation-v1-3"
    ]
    record(
        "old_lhc_superseded",
        "lhc-beam-observation-v1-3" in corpus_ids
        and "lhc-beam-observation-v1-2" not in corpus_ids
        and len(superseded_lhc) == 1,
        {
            "new_present":
                "lhc-beam-observation-v1-3" in corpus_ids,
            "old_present":
                "lhc-beam-observation-v1-2" in corpus_ids,
            "superseded_records": len(superseded_lhc),
        },
    )

    test_process = run(
        [
            sys.executable,
            "-m",
            "unittest",
            "-v",
            "work.p4_lhc_si_hep_v0_5.tests.test_lhc_si_hep_v0_5",
        ]
    )
    test_output = test_process.stdout + test_process.stderr
    record(
        "regression_tests",
        test_process.returncode == 0
        and "Ran 41 tests" in test_output
        and "\nOK" in test_output,
        {
            "returncode": test_process.returncode,
            "ran": 41 if "Ran 41 tests" in test_output else None,
            "result": "OK" if "\nOK" in test_output else "not OK",
        },
    )

    failed = [
        check["id"]
        for check in checks
        if check["status"] == "FAIL"
    ]
    result = {
        "schema": {
            "id": "go-p4-validation-summary",
            "version": "0.5.0",
        },
        "date": str(date.today()),
        "release": "GO P4 SI-HEP Quantity Passport and LHC v0.5",
        "status": "PASS" if not failed else "FAIL",
        "summary": {
            "checks_total": len(checks),
            "checks_passed": len(checks) - len(failed),
            "checks_failed": len(failed),
            "pdf_documents": 2,
            "pdf_pages": total_pages,
            "typed_expressions":
                reference_summary["expressions_checked"],
            "reference_findings":
                reference_summary["findings_total"],
            "regression_tests": 41,
            "conversion_rows": len(conversion_rows),
            "corpus_status_counts":
                corpus_summary["status_counts"],
        },
        "artifacts": {
            "passport_pdf": str(PASSPORT_PDF.relative_to(ROOT)),
            "passport_sha256":
                actual_hashes["si-hep-quantity-passport-v0-5"],
            "lhc_pdf": str(LHC_PDF.relative_to(ROOT)),
            "lhc_sha256":
                actual_hashes["lhc-beam-observation-v1-3"],
            "contract": str(CONTRACT.relative_to(ROOT)),
            "reference_ledger": str(LEDGER.relative_to(ROOT)),
            "conversion_table": str(CONVERSIONS.relative_to(ROOT)),
        },
        "checks": checks,
    }
    SUMMARY.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY.write_text(
        json.dumps(result, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"{result['status']}: "
        f"{len(checks) - len(failed)}/{len(checks)} checks, "
        f"{total_pages} pages, 28 expressions, 41 tests"
    )
    if failed:
        print("Failed checks: " + ", ".join(failed))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
