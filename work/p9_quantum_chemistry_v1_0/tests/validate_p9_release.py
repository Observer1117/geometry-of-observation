#!/usr/bin/env python3
"""Validate the complete P9 quantum-chemistry release candidate."""

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
P9 = ROOT / "work/p9_quantum_chemistry_v1_0"

PDF = P9 / "build/qchem/quantum_chemistry_observation_geometry_v1_1.pdf"
TEX = P9 / "src/quantum_chemistry_observation_geometry_v1_1.tex"
TEXT = P9 / "checks/qchem/quantum_chemistry_observation_geometry_v1_1.txt"
LOG = P9 / "build/qchem/quantum_chemistry_observation_geometry_v1_1.log"
CONTRACT = P9 / "core/quantum_chemistry_observation_contract_v1_0.yaml"
REFERENCE_LEDGER = (
    P9 / "ledgers/quantum_chemistry_reference_ledger_v1_0.yaml"
)
CORPUS_LEDGER = P9 / "ledgers/corpus_ledgers_v1_0.yaml"
REFERENCE_LINT = (
    P9 / "reports/Quantum_Chemistry_Reference_Lint_Report_v1_0.json"
)
CORPUS_LINT = P9 / "reports/GO_Corpus_Lint_Report_v1_0.json"
MIGRATION_REPORT = (
    P9 / "reports/P9_Quantum_Chemistry_Migration_Report_v1_0_ru.md"
)
VISUAL_QA = P9 / "reports/P9_Visual_QA_v1_0.yaml"
BENCHMARKS = P9 / "data/quantum_chemistry_benchmarks_v1_0.csv"
METRICS = P9 / "data/quantum_chemistry_metrics_v1_0.json"
TEST_FILE = P9 / "tests/test_quantum_chemistry_v1_0.py"
GO_LINT = ROOT / "work/go_core_v0_2/src/go_lint.py"
GO_CORE = ROOT / "work/go_core_v0_2/core"
SUMMARY = P9 / "reports/P9_Validation_Summary_v1_0.json"
RENDER_DIR = P9 / "render/qchem"


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
                "id": "go-p9-validation-summary",
                "version": "1.0.0",
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
        len(reader.pages) == 9
        and metadata.get("/Title")
        == "Quantum Chemistry as a Typed Inference Stack under Observation Maps"
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
        len(extracted) > 25_000
        and "Protocol minimum" in extracted
        and "References" in extracted
        and extracted.count("\f") == 9
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
        r"\section{Exact molecule and Born--Oppenheimer reduction}",
        r"\section{Reduced density data and information loss}",
        r"\section{Finite bases, Hartree--Fock, and orbital gauge}",
        r"\section{Density-functional theory firewall}",
        r"\section{Nuclear geometry and the normal-mode theorem}",
        r"\section{Active spaces, valence, and bond interpretations}",
        r"\section{Ideal spectra and finite-resolution data}",
        r"\section{Approximation and identifiability ledger}",
        r"\gamma^{(1)}",
        r"C^\dagger SC=I",
        r"\lambda_k=\omega_k^2",
        r"\mathcal D_\epsilon",
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
        == "go-quantum-chemistry-observation-contract"
        and contract["schema"]["version"] == "1.0.0"
        and contract["schema"]["inherited_contracts"]
        == ["go-conical-intersections-observation-contract@0.9.0"]
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

    state_reduction_ok = (
        contract["state_layer"]["full_molecular_state"]["arguments"]
        == [
            "all_electronic_space_spin_coordinates",
            "all_nuclear_coordinates",
        ]
        and contract["Born_Oppenheimer_reduction"]["one_surface_model"][
            "status"
        ]
        == "approximation"
        and "PES_is_not_a_marginal_of_the_exact_wavefunction"
        in contract["Born_Oppenheimer_reduction"]["prohibitions"]
        and contract["Born_Oppenheimer_reduction"]["conical_intersections"][
            "inherited_contract"
        ]
        == "go-conical-intersections-observation-contract@0.9.0"
    )
    record("contract_state_and_reduction_firewalls", state_reduction_ok, state_reduction_ok)

    rdm_orbital_ok = (
        contract["reduced_density_layer"]["one_RDM"]["properties"][-1]
        == "fermionic_occupations_between_zero_and_one_for_spin_orbitals"
        and contract["reduced_density_layer"]["information_loss_control"][
            "same_one_RDM"
        ]
        == "one_half_identity_4"
        and contract["orbital_gauge"]["group"] == "U(N_occ)"
        and "representation_choice_is_not_measurement"
        in contract["orbital_gauge"]["prohibitions"]
        and "ground_state_density_theorem_is_not_arbitrary_state_tomography"
        in contract["DFT_layer"]["prohibitions"]
    )
    record("contract_RDM_DFT_and_orbital_firewalls", rdm_orbital_ok, rdm_orbital_ok)

    modes_spectrum_ok = (
        contract["normal_modes"]["mass_weighted_Hessian"]["dimension"]
        == "inverse_time_squared"
        and contract["normal_modes"]["eigenproblem"]["relation"]
        == "lambda_k = omega_k^2"
        and contract["normal_modes"]["rigid_zero_modes"]
        == {
            "isolated_nonlinear_molecule": 6,
            "isolated_linear_molecule": 5,
        }
        and contract["spectroscopy"]["line_profile"]["normalization"]
        == "integral_L_domega = 1"
        and contract["observation_channel"]["observed_data"]
        == "Y = D_epsilon(C_inst(S_A)) + eta"
    )
    record(
        "contract_modes_and_spectroscopy_firewalls",
        modes_spectrum_ok,
        modes_spectrum_ok,
    )

    reference_summary = load_json(REFERENCE_LINT)["summary"]
    reference_ok = (
        reference_summary["canonical_documents"] == 1
        and reference_summary["reference_documents"] == 1
        and reference_summary["critical_adapters"] == 0
        and reference_summary["expressions_checked"] == 47
        and reference_summary["findings_total"] == 0
        and reference_summary["status_counts"] == {"PASS": 1}
    )
    record("reference_lint", reference_ok, reference_summary)

    corpus_report = load_json(CORPUS_LINT)
    corpus_summary = corpus_report["summary"]
    corpus_ok = (
        corpus_summary["canonical_documents"] == 18
        and corpus_summary["reference_documents"] == 16
        and corpus_summary["critical_adapters"] == 2
        and corpus_summary["expressions_checked"] == 253
        and corpus_summary["findings_total"] == 5
        and corpus_summary["status_counts"] == {"FAIL": 2, "PASS": 16}
    )
    record("corpus_lint", corpus_ok, corpus_summary)

    failing_ids = sorted(
        item["id"]
        for item in corpus_report["documents"]
        if item["status"] != "PASS"
    )
    expected_failing_ids = [
        "regular-polyhedra-v1",
        "satellite-networks-v1-1",
    ]
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
        if "quantum_chemistry" in item.get("path", "")
    ]
    supersession_ok = (
        len(ids) == 18
        and len(set(ids)) == 18
        and "quantum-chemistry-observation-v1" not in ids
        and "quantum-chemistry-observation-v1-1" in ids
        and len(legacy_records) == 1
        and legacy_records[0].get("status") == "superseded"
        and legacy_records[0].get("sha256")
        == "a99ed4bfdfbc416ef10b4d4ed10c1f667515a0005c8c934d9b58e21fa3648d1e"
        and legacy_records[0].get("canonical_document")
        == "quantum-chemistry-observation-v1-1"
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
        "Rayleigh_Ritz": 12,
        "active_space": 4,
        "correlation": 24,
        "generalized_eigenproblem": 24,
        "normal_modes": 48,
        "one_RDM": 39,
        "orbital_gauge": 36,
        "spectroscopy": 15,
    }
    benchmark_ok = (
        len(benchmark_rows) == 202
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
        metrics["benchmark_rows"] == 202
        and metrics["failed_rows"] == 0
        and metrics["max_absolute_error"] < 1e-12
        and metrics["constants"]["h_exact_J_s"] == 6.62607015e-34
        and metrics["constants"]["c_exact_m_s"] == 299792458.0
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
    tests_ok = tests_process.returncode == 0 and test_count == 413
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
        and "expressions=47" in reference_replay.stdout
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
        and "expressions=253" in corpus_replay.stdout
        and "findings=5" in corpus_replay.stdout
        and "statuses={'FAIL': 2, 'PASS': 16}" in corpus_replay.stdout,
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
        and visual["document"]["pages"] == 9
        and len(visual["inspection"]["pages"]) == 9
        and all(
            item["status"] == "PASS"
            for item in visual["inspection"]["pages"]
        )
        and all(
            value == "PASS" for value in visual["global_checks"].values()
        )
    )
    record("visual_qa", visual_ok, visual)

    rendered_pages = sorted(RENDER_DIR.glob("gs-page-*.png"))
    render_details: list[dict[str, Any]] = []
    render_ok = len(rendered_pages) == 9
    for path in rendered_pages:
        try:
            with Image.open(path) as image:
                image.load()
                dimensions = list(image.size)
            page_ok = dimensions == [1191, 1684] and path.stat().st_size > 40_000
        except Exception as error:  # pragma: no cover - diagnostic path
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
        "Полное молекулярное состояние",
        "Reduced density matrices",
        "orbital gauge",
        "DFT firewall",
        "Legacy-ошибка размерности",
        "Спектр и observation channel",
        "16 PASS / 2 FAIL /",
        "Следующий рациональный кандидат — `Regular Polyhedra`",
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
        "10.1103/PhysRev.34.1293",
        "10.1103/RevModPhys.23.69",
        "10.1103/PhysRev.97.1474",
        "10.1103/RevModPhys.35.668",
        "10.1103/PhysRev.136.B864",
        "10.1103/PhysRev.140.A1133",
        "10.1073/pnas.76.12.6062",
        "10.1063/1.437734",
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
            "id": "go-p9-validation-summary",
            "version": "1.0.0",
        },
        "date": "2026-07-28",
        "status": status,
        "release_check_count": len(checks),
        "typed_expressions": 47,
        "regression_tests": 413,
        "benchmark_rows": 202,
        "rendered_pages": 9,
        "corpus_expressions": 253,
        "corpus_statuses": {
            "PASS": 16,
            "FAIL": 2,
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
        f"P9-VALIDATION status={status} "
        f"checks={len(checks)} tests=413 expressions=47 pages=9"
    )
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
