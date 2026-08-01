#!/usr/bin/env python3
"""Validate the complete P11 satellite-networks release candidate."""

from __future__ import annotations

import csv
import hashlib
import json
import re
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any

import yaml
from PIL import Image
from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[3]
P11 = ROOT / "work/p11_satellite_networks_v1_2"

PDF = P11 / "build/satellite/satellite_networks_typed_frames_v1_2.pdf"
TEX = P11 / "src/satellite_networks_typed_frames_v1_2.tex"
TEXT = P11 / "checks/satellite/satellite_networks_typed_frames_v1_2.txt"
LOG = P11 / "build/satellite/satellite_networks_typed_frames_v1_2.log"
CONTRACT = P11 / "core/satellite_networks_observation_contract_v1_2.yaml"
REFERENCE_LEDGER = (
    P11 / "ledgers/satellite_networks_reference_ledger_v1_2.yaml"
)
CORPUS_LEDGER = P11 / "ledgers/corpus_ledgers_v1_2.yaml"
REFERENCE_LINT = (
    P11 / "reports/Satellite_Networks_Reference_Lint_Report_v1_2.json"
)
CORPUS_LINT = P11 / "reports/GO_Corpus_Lint_Report_v1_2.json"
MIGRATION_REPORT = (
    P11 / "reports/P11_Satellite_Networks_Migration_Report_v1_2_ru.md"
)
VISUAL_QA = P11 / "reports/P11_Visual_QA_v1_2.yaml"
BENCHMARKS = P11 / "data/satellite_networks_benchmarks_v1_2.csv"
METRICS = P11 / "data/satellite_networks_metrics_v1_2.json"
GENERATOR = P11 / "scripts/generate_satellite_network_benchmarks.py"
TEST_FILE = P11 / "tests/test_satellite_networks_v1_2.py"
GO_LINT = ROOT / "work/go_core_v0_2/src/go_lint.py"
GO_CORE = ROOT / "work/go_core_v0_2/core"
SUMMARY = P11 / "reports/P11_Validation_Summary_v1_2.json"
RENDER_DIR = P11 / "render/satellite"


def load_yaml(path: Path) -> dict[str, Any]:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"{path}: YAML root must be a mapping")
    return value


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
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
        GENERATOR,
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
                "id": "go-p11-validation-summary",
                "version": "1.2.0",
            },
            "date": "2026-07-28",
            "status": "FAIL",
            "checks": checks,
        }
        SUMMARY.parent.mkdir(parents=True, exist_ok=True)
        SUMMARY.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
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
        == "Satellite Networks under Typed Frames and Temporal Observation Channels"
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
        for path in (TEX, TEXT, CONTRACT, REFERENCE_LEDGER, MIGRATION_REPORT):
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
        len(extracted) > 22_000
        and "Distance-matrix invariance" in extracted
        and "Exact sampling alias" in extracted
        and "Claim boundary" in extracted
        and "References" in extracted
        and extracted.count("\f") == 8
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
        r"\section{Scope, hidden state, and the observation chain}",
        r"\section{Time-dependent rigid frames and exact spatial invariants}",
        r"\section{Phase closure, image closure, and frame covariance}",
        r"\section{Sampling, retarded observation, and non-identifiability}",
        r"\section{Line-of-sight and temporal network geometry}",
        r"\section{Density and entropy require transported partitions}",
        r"\section{Proper time and the synchronization boundary}",
        r"\section{Benchmark controls and claim firewall}",
        r"\Gcal_I=C^1(I,\SE(3))",
        r"B=-\frac12J(D\circ D)J",
        r"L_\omega=\{m\in\Z^k:m\cdot\omega=0\}",
        r"K_{F_g}=gK_F",
        r"e^{i(\omega+2\pi q/\Delta t)t_m}",
        r"A\longmapsto PAP^\mathsf T",
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
        row[0] for row in font_rows if len(row) < 7 or row[-5].lower() != "yes"
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
        == "go-satellite-networks-observation-contract"
        and contract["schema"]["version"] == "1.2.0"
        and contract["schema"]["base_contract"] == "go-core-spec@0.2.0"
        and contract["schema"]["inherited_contracts"]
        == ["go-regular-polyhedra-observation-contract@1.1.0"]
        and len(contract["reference_gates"]) == 21
    )
    record(
        "contract_schema_and_gates",
        contract_ok,
        {
            "schema": contract["schema"],
            "reference_gate_count": len(contract["reference_gates"]),
        },
    )

    frame_ok = (
        contract["frame_layer"]["action_group"]["definition"]
        == "C1_maps_from_I_to_SE3"
        and contract["frame_layer"]["action_group"]["common_time_required"]
        is True
        and contract["frame_layer"]["coordinate_map"]["invertible"] is True
        and contract["frame_layer"]["coordinate_map"]["information_loss"]
        is False
        and contract["frame_layer"]["velocity_law"]["Omega_cross"]
        == "R_transpose_times_Rdot"
        and "component_power_spectrum_under_time_dependent_rotation"
        in contract["frame_layer"]["noninvariants"]
    )
    record("contract_frame_firewall", frame_ok, frame_ok)

    distance_ok = (
        contract["distance_matrix_layer"]["invariance"]
        == "exact_at_each_common_time"
        and contract["distance_matrix_layer"]["realization_test"]["identification"]
        == "labeled_configuration_up_to_E3"
        and contract["distance_matrix_layer"]["information_loss"][
            "reflection_and_chirality"
        ]
        is True
        and contract["distance_matrix_layer"]["information_loss"]["labels"]
        is False
    )
    record("contract_distance_firewall", distance_ok, distance_ok)

    closure_ok = (
        contract["phase_closure_layer"]["exact_phase_closure"]["object"]
        == "coset_subtorus_Gamma_theta0_omega"
        and contract["phase_closure_layer"]["constant_isometry"]["status"]
        == "equivariance_not_pointwise_invariance"
        and contract["phase_closure_layer"]["time_dependent_frame"][
            "closure_congruence_guaranteed"
        ]
        is False
        and contract["phase_closure_layer"]["finite_horizon"][
            "rational_independence_certifiable_from_finite_noisy_data"
        ]
        is False
    )
    record("contract_closure_firewall", closure_ok, closure_ok)

    signal_ok = (
        contract["sampling_and_signal_layer"]["exact_alias"][
            "identical_uniform_samples_for_integer_q"
        ]
        is True
        and contract["sampling_and_signal_layer"]["light_time"][
            "satellite_specific_emission_times"
        ]
        is True
        and contract["sampling_and_signal_layer"]["bearing_channel"][
            "loses_range"
        ]
        is True
    )
    record("contract_sampling_and_signal_firewall", signal_ok, signal_ok)

    graph_ok = (
        contract["line_of_sight_graph"]["tangency_policy"] == "blocked"
        and contract["line_of_sight_graph"]["adjacency"]["symmetric"] is True
        and contract["line_of_sight_graph"]["distinction"][
            "operational_collision_risk_claimed"
        ]
        is False
        and contract["temporal_graph_layer"]["active_edge_event"]["fields"]
        == ["time", "endpoints", "nonnegative_delay"]
        and "aggregated_static_connectivity_does_not_imply_temporal_reachability"
        in contract["temporal_graph_layer"]["prohibitions"]
    )
    record("contract_graph_and_temporal_firewalls", graph_ok, graph_ok)

    entropy_clock_ok = (
        contract["density_entropy_layer"]["partition_entropy"]["logarithm_base"]
        == 2
        and contract["density_entropy_layer"]["partition_entropy"][
            "invariant_only_when_partition_is_co_transformed"
        ]
        is True
        and contract["relativistic_clock_layer"]["exact_proper_time"][
            "coordinate_change_status"
        ]
        == "scalar_invariant"
        and contract["relativistic_clock_layer"]["comparison_boundary"][
            "equal_coordinate_time_endpoint_comparison_protocol_dependent"
        ]
        is True
        and contract["relativistic_clock_layer"]["weak_field_model"][
            "retained_order"
        ]
        == "c_to_minus_2"
    )
    record("contract_entropy_and_clock_firewalls", entropy_clock_ok, entropy_clock_ok)

    protocol_ok = (
        len(contract["observation_maps"]) == 8
        and len(contract["protocol_minimum"]["required"]) == 16
        and len(contract["protocol_minimum"]["clock_conditional"]) == 6
        and contract["observation_maps"][0]["information_loss"] is False
        and contract["observation_maps"][5]["kind"] == "discretizer"
    )
    record("contract_observation_protocol", protocol_ok, protocol_ok)

    reference_summary = load_json(REFERENCE_LINT)["summary"]
    reference_ok = (
        reference_summary["canonical_documents"] == 1
        and reference_summary["reference_documents"] == 1
        and reference_summary["critical_adapters"] == 0
        and reference_summary["expressions_checked"] == 53
        and reference_summary["findings_total"] == 0
        and reference_summary["status_counts"] == {"PASS": 1}
    )
    record("reference_lint", reference_ok, reference_summary)

    corpus_report = load_json(CORPUS_LINT)
    corpus_summary = corpus_report["summary"]
    corpus_ok = (
        corpus_summary["canonical_documents"] == 18
        and corpus_summary["reference_documents"] == 18
        and corpus_summary["critical_adapters"] == 0
        and corpus_summary["expressions_checked"] == 347
        and corpus_summary["findings_total"] == 0
        and corpus_summary["status_counts"] == {"PASS": 18}
        and all(item["status"] == "PASS" for item in corpus_report["documents"])
    )
    record("corpus_lint", corpus_ok, corpus_summary)

    corpus = load_yaml(CORPUS_LEDGER)
    ids = [item["id"] for item in corpus["documents"]]
    legacy_records = [
        item
        for item in corpus["duplicate_or_superseded_sources"]
        if "satellite_networks_observation" in item.get("path", "")
    ]
    supersession_ok = (
        len(ids) == 18
        and len(set(ids)) == 18
        and "satellite-networks-v1-1" not in ids
        and "satellite-networks-observation-v1-2" in ids
        and len(legacy_records) == 1
        and legacy_records[0].get("status") == "superseded"
        and legacy_records[0].get("sha256")
        == "0ceb2a8452911791f5597a3d9cb848203e8d664c6940b29740249c9f29a51ec2"
        and legacy_records[0].get("canonical_document")
        == "satellite-networks-observation-v1-2"
    )
    record(
        "legacy_supersession",
        supersession_ok,
        {"legacy_records": legacy_records},
    )

    with BENCHMARKS.open("r", encoding="utf-8", newline="") as stream:
        benchmark_rows = list(csv.DictReader(stream))
    category_counts = Counter(row["category"] for row in benchmark_rows)
    expected_category_counts = {
        "EDM": 16,
        "clock": 8,
        "entropy": 3,
        "frame_clearance": 120,
        "frame_distance": 120,
        "graph_frame": 8,
        "graph_relabel": 48,
        "light_time": 1,
        "sampling_alias": 128,
        "temporal_graph": 5,
        "two_body": 96,
    }
    benchmark_ok = (
        len(benchmark_rows) == 553
        and dict(sorted(category_counts.items())) == expected_category_counts
        and all(row["status"] == "PASS" for row in benchmark_rows)
    )
    record(
        "benchmark_table",
        benchmark_ok,
        {
            "rows": len(benchmark_rows),
            "categories": dict(sorted(category_counts.items())),
        },
    )

    metrics = load_json(METRICS)
    residuals = metrics["max_abs_error_by_category"]
    residuals_ok = (
        metrics["benchmark_rows"] == 553
        and metrics["failed_rows"] == 0
        and metrics["category_counts"] == expected_category_counts
        and residuals["EDM"] < 4e-16
        and residuals["frame_distance"] < 3e-7
        and residuals["frame_clearance"] < 2e-7
        # The frozen metrics record 4.440892098500626e-15 on the public
        # reference build. Use a 5e-15 portability ceiling so the validator
        # accepts its own canonical benchmark across IEEE-754 implementations.
        and residuals["graph_relabel"] < 5e-15
        and residuals["sampling_alias"] < 2e-13
        and residuals["light_time"] < 6e-14
        and all(value == 1 for value in metrics["snapshot_component_counts"])
        and metrics["clock_offsets_microseconds_per_day"]["LEO_7000km"] < 0
        and metrics["clock_offsets_microseconds_per_day"]["GPS_like"] > 0
    )
    record("numerical_residuals", residuals_ok, metrics)

    benchmark_hash_before = sha256(BENCHMARKS)
    metrics_hash_before = sha256(METRICS)
    generator_process = run(["python3", str(GENERATOR)])
    replay_ok = (
        generator_process.returncode == 0
        and sha256(BENCHMARKS) == benchmark_hash_before
        and sha256(METRICS) == metrics_hash_before
    )
    record(
        "benchmark_reproducibility",
        replay_ok,
        {
            "returncode": generator_process.returncode,
            "benchmark_sha256_before": benchmark_hash_before,
            "benchmark_sha256_after": sha256(BENCHMARKS),
            "metrics_sha256_before": metrics_hash_before,
            "metrics_sha256_after": sha256(METRICS),
        },
    )

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
    tests_ok = tests_process.returncode == 0 and test_count == 623
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
        and "expressions=53" in reference_replay.stdout
        and "findings=0" in reference_replay.stdout
        and "statuses={'PASS': 1}" in reference_replay.stdout,
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
        "corpus_strict_replay",
        corpus_replay.returncode == 0
        and "documents=18" in corpus_replay.stdout
        and "expressions=347" in corpus_replay.stdout
        and "findings=0" in corpus_replay.stdout
        and "statuses={'PASS': 18}" in corpus_replay.stdout,
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
            item["status"] == "PASS" for item in visual["inspection"]["pages"]
        )
        and all(value == "PASS" for value in visual["global_checks"].values())
    )
    record("visual_qa", visual_ok, visual)

    rendered_pages = sorted(RENDER_DIR.glob("page-*.png"))
    render_details: list[dict[str, Any]] = []
    render_ok = len(rendered_pages) == 8
    for path in rendered_pages:
        try:
            with Image.open(path) as image:
                image.load()
                dimensions = list(image.size)
            page_ok = (
                dimensions == [1241, 1754] and path.stat().st_size > 50_000
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
        "Исходные дефекты и скрытые подмены",
        "Полный закон системы отсчёта",
        "Phase closure, image closure и frame covariance",
        "Sampling и retarded observation",
        "LOS и temporal graph",
        "Density, entropy и часы",
        "18 PASS / 0 FAIL / 0 BLOCKED",
        "Следующий рациональный этап — P12",
    ]
    missing_report_fragments = [
        fragment for fragment in report_fragments if fragment not in report_text
    ]
    record(
        "migration_report_coverage",
        not missing_report_fragments,
        {"missing": missing_report_fragments},
    )

    primary_identifiers = [
        "IERS Conventions (2010)",
        "CCSDS 502.0-B-3",
        "10.2514/6.2006-6753",
        "IS-GPS-200N",
        "10.12942/lrr-2003-1",
        "10.1145/335305.335364",
        "1968654",
    ]
    missing_identifiers = [
        identifier for identifier in primary_identifiers if identifier not in source
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
            "id": "go-p11-validation-summary",
            "version": "1.2.0",
        },
        "date": "2026-07-28",
        "status": status,
        "release_check_count": len(checks),
        "typed_expressions": 53,
        "regression_tests": 623,
        "benchmark_rows": 553,
        "rendered_pages": 8,
        "corpus_expressions": 347,
        "corpus_statuses": {
            "PASS": 18,
            "FAIL": 0,
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
        f"P11-VALIDATION status={status} checks={len(checks)} "
        "tests=623 expressions=53 pages=8"
    )
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
