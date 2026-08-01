#!/usr/bin/env python3
"""Validate the complete P5 mechanics release candidate."""

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
P5 = ROOT / "work/p5_mechanics_frames_v0_6"

DOCUMENTS = {
    "frames-forces-dissipation-interface-v0-1": {
        "pdf": P5 / "build/interface/frame_force_dissipation_interface_v0_1.pdf",
        "tex": P5 / "src/frame_force_dissipation_interface_v0_1.tex",
        "text": P5
        / "checks_final/interface/frame_force_dissipation_interface_v0_1.txt",
        "log": P5 / "build/interface/frame_force_dissipation_interface_v0_1.log",
        "pages": 7,
        "title": "Frames, Forces, Constraints, and Dissipation under Observation Maps",
        "fragments": [
            r"\section{Frame graph and affine point maps}",
            r"P_{\rm diss}:=-\pair{Q_d}{\dot q}\ge0",
            r"\section{Lagrange--d'Alembert energy identity}",
        ],
    },
    "celestial-foucault-networks-v1-1": {
        "pdf": P5 / "build/foucault/celestial_foucault_networks_v1_1.pdf",
        "tex": P5 / "src/celestial_foucault_networks_v1_1.tex",
        "text": P5
        / "checks_final/foucault/celestial_foucault_networks_v1_1.txt",
        "log": P5 / "build/foucault/celestial_foucault_networks_v1_1.log",
        "pages": 6,
        "title": "Foucault Networks on Celestial Bodies as Typed Observation Geometry",
        "fragments": [
            r"\section{Frame-consistent celestial hierarchy}",
            r"\boxed{\dot\alpha=-\Omega_n}",
            r"\section{Non-identifiability}",
        ],
    },
    "bobsleigh-contact-v1-1": {
        "pdf": P5 / "build/bobsleigh/bobsleigh_contact_geometry_v1_1.pdf",
        "tex": P5 / "src/bobsleigh_contact_geometry_v1_1.tex",
        "text": P5
        / "checks_final/bobsleigh/bobsleigh_contact_geometry_v1_1.txt",
        "log": P5 / "build/bobsleigh/bobsleigh_contact_geometry_v1_1.log",
        "pages": 6,
        "title": "Bobsleigh Contact Geometry as a Typed Observation System",
        "fragments": [
            r"\section{Unilateral contact and force pullback}",
            r"P_{\rm fric}",
            r"\section{Guarded diagnostics}",
        ],
    },
    "roller-coaster-v1-1": {
        "pdf": P5 / "build/roller/roller_coaster_geometry_v1_1.pdf",
        "tex": P5 / "src/roller_coaster_geometry_v1_1.tex",
        "text": P5
        / "checks_final/roller/roller_coaster_geometry_v1_1.txt",
        "log": P5 / "build/roller/roller_coaster_geometry_v1_1.log",
        "pages": 6,
        "title": "Roller-Coaster Geometry as a Typed Observation Laboratory",
        "fragments": [
            r"\section{Rail offsets and their domain}",
            r"-\Omega^B\times f^B",
            r"\Delta L_{\rm or}\mapsto-\Delta L_{\rm or}",
        ],
    },
}

CONTRACT = P5 / "core/frame_force_dissipation_contract_v0_6.yaml"
REFERENCE_LEDGER = P5 / "ledgers/mechanics_reference_ledgers_v0_6.yaml"
CORPUS_LEDGER = P5 / "ledgers/corpus_ledgers_v0_6.yaml"
REFERENCE_LINT = P5 / "reports/Mechanics_Reference_Lint_Report_v0_6.json"
CORPUS_LINT = P5 / "reports/GO_Corpus_Lint_Report_v0_6.json"
MIGRATION_REPORT = (
    P5 / "reports/P5_Frames_Forces_Dissipation_Migration_Report_v0_6_ru.md"
)
VISUAL_QA = P5 / "reports/P5_Visual_QA_v0_6.yaml"
SUMMARY = P5 / "reports/P5_Validation_Summary_v0_6.json"
GO_LINT = ROOT / "work/go_core_v0_2/src/go_lint.py"
GO_CORE = ROOT / "work/go_core_v0_2/core"


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
        path
        for document in DOCUMENTS.values()
        for path in (
            document["pdf"],
            document["tex"],
            document["text"],
            document["log"],
        )
    ] + [
        CONTRACT,
        REFERENCE_LEDGER,
        CORPUS_LEDGER,
        REFERENCE_LINT,
        CORPUS_LINT,
        MIGRATION_REPORT,
        VISUAL_QA,
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
            "schema": {"id": "go-p5-validation-summary", "version": "0.6.0"},
            "date": str(date.today()),
            "status": "FAIL",
            "checks": checks,
        }
        SUMMARY.parent.mkdir(parents=True, exist_ok=True)
        SUMMARY.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        return 1

    reference_ledger = load_yaml(REFERENCE_LEDGER)
    ledger_documents = {
        document["id"]: document for document in reference_ledger["documents"]
    }
    expected_hashes = {
        document_id: ledger_documents[document_id]["source"]["sha256"]
        for document_id in DOCUMENTS
    }
    actual_hashes = {
        document_id: sha256(document["pdf"])
        for document_id, document in DOCUMENTS.items()
    }
    record(
        "pdf_sha256",
        expected_hashes == actual_hashes,
        {"expected": expected_hashes, "actual": actual_hashes},
    )

    metadata_details: list[dict[str, Any]] = []
    metadata_ok = True
    total_pages = 0
    for document_id, document in DOCUMENTS.items():
        reader = PdfReader(document["pdf"])
        metadata = reader.metadata or {}
        pages = len(reader.pages)
        title = metadata.get("/Title")
        total_pages += pages
        metadata_ok = metadata_ok and (
            pages == document["pages"] and title == document["title"]
        )
        metadata_details.append(
            {
                "id": document_id,
                "pages": pages,
                "title": title,
            }
        )
    record("pdf_metadata", metadata_ok and total_pages == 25, metadata_details)

    prohibited_hits: dict[str, dict[str, int]] = {}
    for token in ("TODO", "TBD", "\ufffd"):
        token_hits: dict[str, int] = {}
        for document in DOCUMENTS.values():
            for path in (document["tex"], document["text"]):
                text = path.read_text(encoding="utf-8", errors="replace")
                count = text.count(token)
                if count:
                    token_hits[path.name] = count
        if token_hits:
            prohibited_hits[token] = token_hits
    record("no_prohibited_tokens", not prohibited_hits, prohibited_hits)

    reference_heading_counts: dict[str, int] = {}
    explicit_heading_hits: list[str] = []
    for document_id, document in DOCUMENTS.items():
        extracted = document["text"].read_text(
            encoding="utf-8", errors="replace"
        )
        count = sum(line.strip() == "References" for line in extracted.splitlines())
        reference_heading_counts[document_id] = count
        source = document["tex"].read_text(encoding="utf-8")
        if r"\section*{References}" in source:
            explicit_heading_hits.append(document_id)
    record(
        "bibliography_heading_unique",
        all(count == 1 for count in reference_heading_counts.values())
        and not explicit_heading_hits,
        {
            "extracted_counts": reference_heading_counts,
            "explicit_heading_hits": explicit_heading_hits,
        },
    )

    absent_fragments: list[str] = []
    for document_id, document in DOCUMENTS.items():
        source = document["tex"].read_text(encoding="utf-8")
        absent_fragments.extend(
            f"{document_id}:{fragment}"
            for fragment in document["fragments"]
            if fragment not in source
        )
    record(
        "required_source_fragments",
        not absent_fragments,
        {"absent": absent_fragments},
    )

    forbidden_log_patterns = [
        "Overfull",
        "Underfull",
        "LaTeX Warning",
        "undefined references",
        "multiply defined",
        "Fatal error",
        "Missing character",
    ]
    log_hits: dict[str, list[str]] = {}
    for document in DOCUMENTS.values():
        log_text = document["log"].read_text(
            encoding="utf-8", errors="replace"
        )
        hits = [
            pattern for pattern in forbidden_log_patterns if pattern in log_text
        ]
        if hits:
            log_hits[document["log"].name] = hits
    record("latex_logs", not log_hits, log_hits)

    font_details: list[dict[str, Any]] = []
    fonts_ok = True
    for document_id, document in DOCUMENTS.items():
        process = run(["pdffonts", str(document["pdf"])])
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
        file_ok = process.returncode == 0 and bool(rows) and not nonembedded
        fonts_ok = fonts_ok and file_ok
        font_details.append(
            {
                "id": document_id,
                "font_count": len(rows),
                "nonembedded": nonembedded,
                "returncode": process.returncode,
            }
        )
    record("embedded_fonts", fonts_ok, font_details)

    contract = load_yaml(CONTRACT)
    contract_ok = (
        contract["schema"]["id"] == "go-frame-force-dissipation-contract"
        and contract["schema"]["version"] == "0.6.0"
        and contract["dissipation_convention"]["generalized"][
            "nonnegative_loss"
        ]
        == "P_diss = -pairing(Q_d,qdot) >= 0"
        and contract["energy_balance"]["identity"]
        == "dE_L_dt = P_act - P_diss + P_con - partial_t_L"
        and contract["constraint_convention"]["unilateral"]["gap_side"]
        == "g_positive_means_separation"
    )
    record(
        "contract_schema_and_signs",
        contract_ok,
        {
            "schema": contract["schema"],
            "dissipation": contract["dissipation_convention"]["generalized"],
            "energy": contract["energy_balance"]["identity"],
        },
    )

    reference_lint = load_json(REFERENCE_LINT)["summary"]
    reference_lint_ok = (
        reference_lint["canonical_documents"] == 4
        and reference_lint["reference_documents"] == 4
        and reference_lint["expressions_checked"] == 39
        and reference_lint["findings_total"] == 0
        and reference_lint["status_counts"] == {"PASS": 4}
    )
    record("reference_lint", reference_lint_ok, reference_lint)

    corpus_lint = load_json(CORPUS_LINT)["summary"]
    corpus_lint_ok = (
        corpus_lint["canonical_documents"] == 18
        and corpus_lint["reference_documents"] == 12
        and corpus_lint["critical_adapters"] == 6
        and corpus_lint["expressions_checked"] == 132
        and corpus_lint["findings_total"] == 18
        and corpus_lint["status_counts"] == {"FAIL": 6, "PASS": 12}
    )
    record("corpus_lint", corpus_lint_ok, corpus_lint)

    corpus = load_yaml(CORPUS_LEDGER)
    corpus_ids = {document["id"] for document in corpus["documents"]}
    old_ids = {
        "celestial-foucault-networks-v1",
        "bobsleigh-contact-v1",
        "roller-coaster-v1",
    }
    new_ids = {
        "frames-forces-dissipation-interface-v0-1",
        "celestial-foucault-networks-v1-1",
        "bobsleigh-contact-v1-1",
        "roller-coaster-v1-1",
    }
    superseded_targets = {
        item.get("canonical_document")
        for item in corpus["duplicate_or_superseded_sources"]
        if item.get("status") == "superseded"
    }
    supersession_ok = (
        not (old_ids & corpus_ids)
        and new_ids <= corpus_ids
        and {
            "celestial-foucault-networks-v1-1",
            "bobsleigh-contact-v1-1",
            "roller-coaster-v1-1",
        }
        <= superseded_targets
    )
    record(
        "mechanics_supersession",
        supersession_ok,
        {
            "old_present": sorted(old_ids & corpus_ids),
            "new_present": sorted(new_ids & corpus_ids),
            "superseded_targets": sorted(
                target for target in superseded_targets if target
            ),
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
    record(
        "reference_strict_run",
        reference_process.returncode == 0
        and "documents=4" in reference_process.stdout
        and "findings=0" in reference_process.stdout,
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
    record(
        "corpus_strict_expected_failure",
        corpus_process.returncode != 0
        and "documents=18" in corpus_process.stdout
        and "FAIL" in corpus_process.stdout,
        {
            "returncode": corpus_process.returncode,
            "stdout": corpus_process.stdout.strip(),
            "stderr": corpus_process.stderr.strip(),
        },
    )

    tests_process = run(
        [
            "python3",
            "-m",
            "unittest",
            "-v",
            "work.p5_mechanics_frames_v0_6.tests.test_mechanics_frames_v0_6",
        ]
    )
    test_output = tests_process.stdout + "\n" + tests_process.stderr
    ran_match = re.search(r"Ran\s+(\d+)\s+tests?", test_output)
    tests_ran = int(ran_match.group(1)) if ran_match else 0
    record(
        "regression_tests",
        tests_process.returncode == 0 and tests_ran == 50 and "\nOK" in test_output,
        {
            "returncode": tests_process.returncode,
            "ran": tests_ran,
            "result": "OK" if "\nOK" in test_output else "NOT_OK",
        },
    )

    visual_qa = load_yaml(VISUAL_QA)
    visual_documents = visual_qa["documents"]
    visual_ok = (
        visual_qa["status"] == "PASS"
        and visual_qa["total_pages"] == 25
        and len(visual_documents) == 4
        and all(item["status"] == "PASS" for item in visual_documents)
        and all(
            len(item["inspected_pages"]) == item["pages"]
            for item in visual_documents
        )
        and not any(visual_qa["checks"].values())
    )
    record("visual_qa_record", visual_ok, visual_qa)

    failed = [check["id"] for check in checks if check["status"] != "PASS"]
    result = {
        "schema": {"id": "go-p5-validation-summary", "version": "0.6.0"},
        "date": str(date.today()),
        "release": "GO P5 Frames, Forces, Constraints, and Dissipation v0.6",
        "status": "PASS" if not failed else "FAIL",
        "summary": {
            "checks_total": len(checks),
            "checks_passed": len(checks) - len(failed),
            "checks_failed": len(failed),
            "pdf_documents": 4,
            "pdf_pages": total_pages,
            "typed_expressions": 39,
            "reference_findings": 0,
            "regression_tests": tests_ran,
            "corpus_status_counts": {"FAIL": 6, "PASS": 12},
        },
        "artifacts": {
            document_id: {
                "pdf": str(document["pdf"].relative_to(ROOT)),
                "sha256": actual_hashes[document_id],
            }
            for document_id, document in DOCUMENTS.items()
        }
        | {
            "contract": str(CONTRACT.relative_to(ROOT)),
            "reference_ledger": str(REFERENCE_LEDGER.relative_to(ROOT)),
            "corpus_ledger": str(CORPUS_LEDGER.relative_to(ROOT)),
        },
        "failed_checks": failed,
        "checks": checks,
    }
    SUMMARY.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY.write_text(
        json.dumps(result, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    print(
        f"P5-VALIDATE checks={len(checks)} passed={len(checks)-len(failed)} "
        f"failed={len(failed)} status={result['status']}"
    )
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
