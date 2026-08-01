#!/usr/bin/env python3
"""Build the strict P11 reference ledger after the PDF is compiled."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import yaml
from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[3]
P11 = ROOT / "work/p11_satellite_networks_v1_2"
PDF = P11 / "build/satellite/satellite_networks_typed_frames_v1_2.pdf"
TEX = P11 / "src/satellite_networks_typed_frames_v1_2.tex"
TEXT = P11 / "checks/satellite/satellite_networks_typed_frames_v1_2.txt"
METRICS = P11 / "data/satellite_networks_metrics_v1_2.json"
OUTPUT = P11 / "ledgers/satellite_networks_reference_ledger_v1_2.yaml"

ZERO = [0, 0, 0, 0, 0, 0, 0]
LENGTH = [1, 0, 0, 0, 0, 0, 0]
AREA = [2, 0, 0, 0, 0, 0, 0]
VOLUME = [3, 0, 0, 0, 0, 0, 0]
INV_VOLUME = [-3, 0, 0, 0, 0, 0, 0]
TIME = [0, 0, 1, 0, 0, 0, 0]
FREQUENCY = [0, 0, -1, 0, 0, 0, 0]
FREQUENCY_SQUARED = [0, 0, -2, 0, 0, 0, 0]
VELOCITY = [1, 0, -1, 0, 0, 0, 0]
SPEED_SQUARED = [2, 0, -2, 0, 0, 0, 0]
ACCELERATION = [1, 0, -2, 0, 0, 0, 0]
MU_DIMENSION = [3, 0, -2, 0, 0, 0, 0]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def quantity(
    qid: str,
    symbol: str,
    semantic_kind: str,
    dimension: list[int],
    unit: str,
    *,
    frame: str = "none",
    unit_context: str = "SI",
    claim_status: str = "definition",
    log_base: int | str | None = None,
    normalized: bool | None = None,
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "id": qid,
        "symbol": symbol,
        "semantic_kind": semantic_kind,
        "dimension": dimension,
        "canonical_unit": unit,
        "unit_context": unit_context,
        "frame": frame,
        "claim_status": claim_status,
    }
    if log_base is not None:
        record["log_base"] = log_base
    if normalized is not None:
        record["normalized"] = normalized
    return record


def q(qid: str) -> dict[str, str]:
    return {"q": qid}


def const(
    value: float | int,
    *,
    dimension: list[int] = ZERO,
    semantic_kind: str = "scalar",
    unit_context: str = "neutral",
    frame: str = "none",
) -> dict[str, Any]:
    return {
        "const": value,
        "dimension": dimension,
        "semantic_kind": semantic_kind,
        "unit_context": unit_context,
        "frame": frame,
    }


def expression(
    expression_id: str,
    anchor: str,
    ast: dict[str, Any],
    dimension: list[int],
    semantic_kind: str,
    frame: str | None = None,
) -> dict[str, Any]:
    expected: dict[str, Any] = {
        "outcome": "pass",
        "rules": [],
        "dimension": dimension,
        "semantic_kind": semantic_kind,
    }
    if frame is not None:
        expected["frame"] = frame
    return {
        "id": expression_id,
        "anchor": anchor,
        "ast": ast,
        "expect": expected,
    }


def build_quantities() -> list[dict[str, Any]]:
    values = [
        quantity("sn.r_i", "r_i", "vector", LENGTH, "m", frame="inertial"),
        quantity("sn.r_j", "r_j", "vector", LENGTH, "m", frame="inertial"),
        quantity("sn.c_E", "c_E", "vector", LENGTH, "m", frame="inertial"),
        quantity("sn.o", "o", "vector", LENGTH, "m", frame="inertial"),
        quantity("sn.a_common", "a", "vector", LENGTH, "m", frame="inertial"),
        quantity("sn.p_i", "p_i", "vector", LENGTH, "m", frame="inertial"),
        quantity("sn.p_j", "p_j", "vector", LENGTH, "m", frame="inertial"),
        quantity("sn.d_segment", "d_ij", "vector", LENGTH, "m", frame="inertial"),
        quantity("sn.segment_point", "s_ij", "vector", LENGTH, "m", frame="inertial"),
        quantity("sn.y_i", "y_i", "vector", LENGTH, "m", frame="observer"),
        quantity("sn.y_j", "y_j", "vector", LENGTH, "m", frame="observer"),
        quantity("sn.c_frame", "c_f", "vector", LENGTH, "m", frame="observer"),
        quantity("sn.frame_relative_i", "z_i", "vector", LENGTH, "m", frame="observer"),
        quantity("sn.v_i", "v_i", "vector", VELOCITY, "m/s", frame="inertial"),
        quantity("sn.v_j", "v_j", "vector", VELOCITY, "m/s", frame="inertial"),
        quantity("sn.ydot_i", "ydot_i", "vector", VELOCITY, "m/s", frame="observer"),
        quantity("sn.ydot_j", "ydot_j", "vector", VELOCITY, "m/s", frame="observer"),
        quantity("sn.d_ij", "D_ij", "scalar", LENGTH, "m", frame="invariant"),
        quantity("sn.rho_i", "rho_i", "scalar", LENGTH, "m", frame="invariant"),
        quantity("sn.rho_j", "rho_j", "scalar", LENGTH, "m", frame="invariant"),
        quantity("sn.semimajor_axis", "a_orb", "scalar", LENGTH, "m", frame="invariant"),
        quantity("sn.R_occ", "R_occ", "scalar", LENGTH, "m", frame="invariant"),
        quantity("sn.R_link", "R_link", "scalar", LENGTH, "m", frame="invariant"),
        quantity("sn.R_star", "R_star", "scalar", LENGTH, "m", frame="invariant"),
        quantity("sn.clearance", "h_ij", "scalar", LENGTH, "m", frame="invariant"),
        quantity("sn.mu_E", "mu_E", "scalar", MU_DIMENSION, "m^3/s^2", frame="invariant"),
        quantity("sn.c", "c", "scalar", VELOCITY, "m/s", frame="invariant", claim_status="empirical"),
        quantity("sn.speed_i", "v_i_norm", "scalar", VELOCITY, "m/s", frame="invariant"),
        quantity("sn.speed_squared_i", "v_i_squared", "scalar", SPEED_SQUARED, "m^2/s^2", frame="invariant"),
        quantity("sn.potential_i", "Phi_i", "scalar", SPEED_SQUARED, "m^2/s^2", frame="model_dependent"),
        quantity("sn.acceleration_magnitude", "a_i", "scalar", ACCELERATION, "m/s^2", frame="invariant"),
        quantity("sn.omega_i", "omega_i", "scalar", FREQUENCY, "rad/s", frame="model_time"),
        quantity("sn.omega_j", "omega_j", "scalar", FREQUENCY, "rad/s", frame="model_time"),
        quantity("sn.omega_alias_shift", "Delta_omega", "scalar", FREQUENCY, "rad/s", frame="sampling"),
        quantity("sn.omega_alias", "omega_prime", "scalar", FREQUENCY, "rad/s", frame="sampling"),
        quantity("sn.mean_motion_squared", "n_squared", "scalar", FREQUENCY_SQUARED, "1/s^2", frame="model_time"),
        quantity("sn.time", "t", "scalar", TIME, "s", frame="coordinate_time"),
        quantity("sn.time_next", "t_next", "scalar", TIME, "s", frame="coordinate_time"),
        quantity("sn.sampling_interval", "Delta_t", "scalar", TIME, "s", frame="coordinate_time"),
        quantity("sn.horizon", "T", "scalar", TIME, "s", frame="coordinate_time"),
        quantity("sn.contact_duration", "W_ij", "scalar", TIME, "s", frame="coordinate_time"),
        quantity("sn.link_delay", "ell_ij", "scalar", TIME, "s", frame="coordinate_time"),
        quantity("sn.tau_i", "tau_i", "scalar", TIME, "s", frame="invariant"),
        quantity("sn.tau_j", "tau_j", "scalar", TIME, "s", frame="invariant"),
        quantity("sn.volume_element", "dV", "scalar", VOLUME, "m^3", frame="invariant"),
        quantity("sn.kernel_value", "K_ell", "scalar", INV_VOLUME, "1/m^3", frame="observer"),
        quantity("sn.density", "rho", "scalar", INV_VOLUME, "1/m^3", frame="observer"),
        quantity("sn.weight", "w_i", "probability", ZERO, "1", unit_context="neutral", frame="none"),
        quantity("sn.bin_probability", "p_m", "probability", ZERO, "1", unit_context="neutral", frame="none"),
        quantity("sn.los_indicator", "L_ij", "probability", ZERO, "1", unit_context="neutral", frame="none"),
        quantity("sn.range_indicator", "R_ij", "probability", ZERO, "1", unit_context="neutral", frame="none"),
        quantity("sn.adjacency_entry", "A_ij", "probability", ZERO, "1", unit_context="neutral", frame="none"),
        quantity("sn.contact_fraction", "f_ij", "probability", ZERO, "1", unit_context="neutral", frame="none"),
        quantity("sn.entropy_bit", "H_2", "information", ZERO, "bit", unit_context="neutral", frame="none", log_base=2),
        quantity("sn.entropy_max_bit", "H_max", "information", ZERO, "bit", unit_context="neutral", frame="none", log_base=2),
        quantity("sn.normalized_entropy", "H_norm", "information", ZERO, "1", unit_context="neutral", frame="none", log_base=2, normalized=True),
        quantity("sn.segment_parameter", "u_star", "scalar", ZERO, "1", unit_context="neutral", frame="none", normalized=True),
        quantity("sn.clock_rate", "d_tau_dt", "scalar", ZERO, "1", unit_context="neutral", frame="none", normalized=True),
        quantity("sn.graph_eigenvalue", "lambda_G", "scalar", ZERO, "1", unit_context="neutral", frame="none"),
        quantity("sn.count", "N", "count", ZERO, "count", unit_context="neutral", frame="none"),
        quantity("sn.squared_distance", "D_squared", "scalar", AREA, "m^2", frame="invariant"),
        quantity("sn.squared_distance_i0", "D_i0_squared", "scalar", AREA, "m^2", frame="invariant"),
        quantity("sn.squared_distance_j0", "D_j0_squared", "scalar", AREA, "m^2", frame="invariant"),
        quantity("sn.squared_distance_ij", "D_ij_squared", "scalar", AREA, "m^2", frame="invariant"),
        quantity("sn.Gram_entry", "B_ij", "scalar", AREA, "m^2", frame="invariant"),
    ]
    return values


def build_expressions() -> list[dict[str, Any]]:
    e: list[dict[str, Any]] = []
    add = e.append
    add(expression("relative_position_inertial", "equation (2.4)", {"op": "sub", "args": [q("sn.r_i"), q("sn.r_j")]}, LENGTH, "vector", "inertial"))
    add(expression("relative_position_observer", "equation (2.4)", {"op": "sub", "args": [q("sn.y_i"), q("sn.y_j")]}, LENGTH, "vector", "observer"))
    add(expression("distance_inertial", "equation (2.4)", {"op": "norm", "arg": {"op": "sub", "args": [q("sn.r_i"), q("sn.r_j")]}, "semantic_kind": "scalar"}, LENGTH, "scalar", "scalar"))
    add(expression("distance_observer", "equation (2.4)", {"op": "norm", "arg": {"op": "sub", "args": [q("sn.y_i"), q("sn.y_j")]}, "semantic_kind": "scalar"}, LENGTH, "scalar", "scalar"))
    add(expression("translation_cancellation", "proof of Theorem 2.1", {"op": "sub", "args": [{"op": "add", "args": [q("sn.r_i"), q("sn.a_common")]}, {"op": "add", "args": [q("sn.r_j"), q("sn.a_common")]}]}, LENGTH, "vector", "inertial"))
    add(expression("position_minus_origin", "equation (2.1)", {"op": "sub", "args": [q("sn.r_i"), q("sn.o")]}, LENGTH, "vector", "inertial"))
    add(expression("central_body_minus_origin", "equation (2.1)", {"op": "sub", "args": [q("sn.c_E"), q("sn.o")]}, LENGTH, "vector", "inertial"))
    add(expression("frame_relative_to_center", "Section 5", {"op": "sub", "args": [q("sn.y_i"), q("sn.c_frame")]}, LENGTH, "vector", "observer"))
    add(expression("relative_velocity_inertial", "equation (2.5)", {"op": "sub", "args": [q("sn.v_i"), q("sn.v_j")]}, VELOCITY, "vector", "inertial"))
    add(expression("relative_velocity_observer", "equation (2.5)", {"op": "sub", "args": [q("sn.ydot_i"), q("sn.ydot_j")]}, VELOCITY, "vector", "observer"))
    add(expression("speed_norm", "equation (7.2)", {"op": "norm", "arg": q("sn.v_i"), "semantic_kind": "scalar"}, VELOCITY, "scalar", "scalar"))
    add(expression("speed_squared", "equation (7.2)", {"op": "dot", "left": q("sn.v_i"), "right": q("sn.v_i")}, SPEED_SQUARED, "scalar", "scalar"))
    add(expression("gravitational_potential", "equation (7.2)", {"op": "div", "left": q("sn.mu_E"), "right": q("sn.rho_i"), "semantic_kind": "scalar", "frame": "none"}, SPEED_SQUARED, "scalar", "none"))
    add(expression("gravity_magnitude", "equation (1.2)", {"op": "div", "left": q("sn.mu_E"), "right": {"op": "pow", "arg": q("sn.rho_i"), "exponent": 2, "semantic_kind": "scalar"}, "semantic_kind": "scalar", "frame": "none"}, ACCELERATION, "scalar", "none"))
    add(expression("mean_motion_squared", "Section 1", {"op": "div", "left": q("sn.mu_E"), "right": {"op": "pow", "arg": q("sn.semimajor_axis"), "exponent": 3, "semantic_kind": "scalar"}, "semantic_kind": "scalar", "frame": "none"}, FREQUENCY_SQUARED, "scalar", "none"))
    add(expression("mean_motion", "Section 1", {"op": "sqrt", "arg": q("sn.mean_motion_squared"), "semantic_kind": "scalar"}, FREQUENCY, "scalar", "model_time"))
    add(expression("orbital_period", "Section 1", {"op": "div", "left": const(2.0 * 3.141592653589793), "right": q("sn.omega_i"), "semantic_kind": "scalar", "frame": "none"}, TIME, "scalar", "none"))
    add(expression("phase_angle", "equation (3.1)", {"op": "mul", "left": q("sn.omega_i"), "right": q("sn.time"), "semantic_kind": "angle", "frame": "scalar"}, ZERO, "angle", "scalar"))
    add(expression("frequency_ratio", "Section 3", {"op": "div", "left": q("sn.omega_i"), "right": q("sn.omega_j"), "semantic_kind": "scalar", "frame": "none"}, ZERO, "scalar", "none"))
    add(expression("alias_shift", "equation (4.3)", {"op": "div", "left": const(6.283185307179586), "right": q("sn.sampling_interval"), "semantic_kind": "scalar", "frame": "none"}, FREQUENCY, "scalar", "none"))
    add(expression("alias_frequency", "equation (4.3)", {"op": "add", "args": [q("sn.omega_i"), q("sn.omega_alias_shift")]}, FREQUENCY, "scalar", "model_time"))
    add(expression("proper_time_difference", "Section 7", {"op": "sub", "args": [q("sn.tau_i"), q("sn.tau_j")]}, TIME, "scalar", "invariant"))
    add(expression("proper_time_rate", "equation (7.2)", {"op": "div", "left": q("sn.tau_i"), "right": q("sn.time"), "semantic_kind": "scalar", "frame": "none"}, ZERO, "scalar", "none"))
    add(expression("potential_over_c_squared", "equation (7.2)", {"op": "div", "left": q("sn.potential_i"), "right": {"op": "pow", "arg": q("sn.c"), "exponent": 2, "semantic_kind": "scalar"}, "semantic_kind": "scalar", "frame": "none"}, ZERO, "scalar", "none"))
    add(expression("kinetic_clock_term", "equation (7.2)", {"op": "div", "left": q("sn.speed_squared_i"), "right": {"op": "mul", "left": const(2.0), "right": {"op": "pow", "arg": q("sn.c"), "exponent": 2, "semantic_kind": "scalar"}, "semantic_kind": "scalar", "frame": "none"}, "semantic_kind": "scalar", "frame": "none"}, ZERO, "scalar", "none"))
    add(expression("weak_clock_rate_sum", "equation (7.2)", {"op": "sub", "args": [{"op": "add", "args": [const(1.0), {"op": "div", "left": q("sn.potential_i"), "right": {"op": "pow", "arg": q("sn.c"), "exponent": 2, "semantic_kind": "scalar"}, "semantic_kind": "scalar", "frame": "none"}]}, {"op": "div", "left": q("sn.speed_squared_i"), "right": {"op": "mul", "left": const(2.0), "right": {"op": "pow", "arg": q("sn.c"), "exponent": 2, "semantic_kind": "scalar"}, "semantic_kind": "scalar", "frame": "none"}, "semantic_kind": "scalar", "frame": "none"}]}, ZERO, "scalar", "none"))
    add(expression("light_time_delay", "equation (4.4)", {"op": "div", "left": q("sn.d_ij"), "right": q("sn.c"), "semantic_kind": "scalar", "frame": "none"}, TIME, "scalar", "none"))
    add(expression("emission_time", "equation (4.4)", {"op": "sub", "args": [q("sn.time"), q("sn.link_delay")]}, TIME, "scalar", "coordinate_time"))
    add(expression("body_relative_i", "Section 5", {"op": "sub", "args": [q("sn.r_i"), q("sn.c_E")]}, LENGTH, "vector", "inertial"))
    add(expression("body_relative_j", "Section 5", {"op": "sub", "args": [q("sn.r_j"), q("sn.c_E")]}, LENGTH, "vector", "inertial"))
    add(expression("segment_direction", "equation (5.1)", {"op": "sub", "args": [q("sn.p_j"), q("sn.p_i")]}, LENGTH, "vector", "inertial"))
    add(expression("segment_dot_numerator", "equation (5.1)", {"op": "dot", "left": q("sn.p_i"), "right": q("sn.d_segment")}, AREA, "scalar", "scalar"))
    add(expression("segment_norm_squared", "equation (5.1)", {"op": "dot", "left": q("sn.d_segment"), "right": q("sn.d_segment")}, AREA, "scalar", "scalar"))
    add(expression("segment_parameter_ratio", "equation (5.1)", {"op": "div", "left": {"op": "dot", "left": q("sn.p_i"), "right": q("sn.d_segment")}, "right": {"op": "dot", "left": q("sn.d_segment"), "right": q("sn.d_segment")}, "semantic_kind": "scalar", "frame": "none"}, ZERO, "scalar", "none"))
    add(expression("scaled_segment_direction", "equation (5.2)", {"op": "mul", "left": q("sn.segment_parameter"), "right": q("sn.d_segment"), "semantic_kind": "vector", "frame": "inertial"}, LENGTH, "vector", "inertial"))
    add(expression("closest_segment_point", "equation (5.2)", {"op": "add", "args": [q("sn.p_i"), {"op": "mul", "left": q("sn.segment_parameter"), "right": q("sn.d_segment"), "semantic_kind": "vector", "frame": "inertial"}]}, LENGTH, "vector", "inertial"))
    add(expression("segment_clearance", "equation (5.2)", {"op": "norm", "arg": q("sn.segment_point"), "semantic_kind": "scalar"}, LENGTH, "scalar", "scalar"))
    add(expression("LOS_threshold", "equation (5.3)", {"op": "compare", "left": q("sn.clearance"), "right": q("sn.R_occ")}, ZERO, "probability", "none"))
    add(expression("range_threshold", "equation (5.4)", {"op": "compare", "left": q("sn.d_ij"), "right": q("sn.R_link")}, ZERO, "probability", "none"))
    add(expression("adjacency_product", "equation (5.4)", {"op": "mul", "left": q("sn.los_indicator"), "right": q("sn.range_indicator"), "semantic_kind": "probability", "frame": "none"}, ZERO, "probability", "none"))
    add(expression("squared_distance", "equation (2.6)", {"op": "pow", "arg": q("sn.d_ij"), "exponent": 2, "semantic_kind": "scalar"}, AREA, "scalar", "invariant"))
    add(expression("Gram_polarization_sum", "equation (2.6)", {"op": "mul", "left": const(0.5), "right": {"op": "sub", "args": [{"op": "add", "args": [q("sn.squared_distance_i0"), q("sn.squared_distance_j0")]}, q("sn.squared_distance_ij")]}, "semantic_kind": "scalar", "frame": "invariant"}, AREA, "scalar", "invariant"))
    add(expression("contact_fraction", "Section 5", {"op": "div", "left": q("sn.contact_duration"), "right": q("sn.horizon"), "semantic_kind": "probability", "frame": "none"}, ZERO, "probability", "none"))
    add(expression("range_latency", "equation (5.6)", {"op": "div", "left": q("sn.d_ij"), "right": q("sn.c"), "semantic_kind": "scalar", "frame": "none"}, TIME, "scalar", "none"))
    add(expression("journey_arrival_sum", "equation (5.6)", {"op": "add", "args": [q("sn.time"), q("sn.link_delay")]}, TIME, "scalar", "coordinate_time"))
    add(expression("journey_causality_test", "equation (5.6)", {"op": "compare", "left": q("sn.time_next"), "right": {"op": "add", "args": [q("sn.time"), q("sn.link_delay")]}}, ZERO, "probability", "none"))
    add(expression("density_contribution", "equation (6.1)", {"op": "mul", "left": q("sn.weight"), "right": q("sn.kernel_value"), "semantic_kind": "scalar", "frame": "observer"}, INV_VOLUME, "scalar", "observer"))
    add(expression("density_normalization", "Section 6", {"op": "integrate", "integrand": q("sn.density"), "measure": q("sn.volume_element")}, ZERO, "scalar", "observer"))
    add(expression("probability_log", "Section 6", {"op": "log", "arg": q("sn.bin_probability"), "base": 2, "semantic_kind": "information"}, ZERO, "information", "none"))
    add(expression("entropy_term", "Section 6", {"op": "mul", "left": q("sn.bin_probability"), "right": {"op": "log", "arg": q("sn.bin_probability"), "base": 2, "semantic_kind": "information"}, "semantic_kind": "information", "frame": "none"}, ZERO, "information", "none"))
    add(expression("normalized_entropy", "Section 6", {"op": "normalize", "value": q("sn.entropy_bit"), "reference": q("sn.entropy_max_bit"), "zero_policy": "undefined_when_partition_has_fewer_than_two_positive_capacity_bins", "semantic_kind": "information"}, ZERO, "information", "none"))
    add(expression("proper_time_integrand_to_time", "equation (7.1)", {"op": "div", "left": q("sn.d_ij"), "right": q("sn.c"), "semantic_kind": "scalar", "frame": "none"}, TIME, "scalar", "none"))
    add(expression("circular_clock_zero_radius", "equation (7.4)", {"op": "mul", "left": const(1.5), "right": q("sn.R_star"), "semantic_kind": "scalar", "frame": "invariant"}, LENGTH, "scalar", "invariant"))
    return e


def main() -> None:
    for required in (PDF, TEX, TEXT, METRICS):
        if not required.is_file():
            raise FileNotFoundError(required)
    metrics = json.loads(METRICS.read_text(encoding="utf-8"))
    document = {
        "id": "satellite-networks-observation-v1-2",
        "title": "Satellite Networks under Typed Frames and Temporal Observation Channels",
        "version": "1.2.0",
        "source": {
            "pdf": str(PDF.relative_to(ROOT)),
            "tex": str(TEX.relative_to(ROOT)),
            "text": str(TEXT.relative_to(ROOT)),
            "metrics_json": str(METRICS.relative_to(ROOT)),
            "pages": len(PdfReader(PDF).pages),
            "sha256": sha256(PDF),
        },
        "ledger_level": "reference",
        "migration_status": "strict_reference_migrated",
        "unit_contexts": ["SI", "GR_geometrized", "neutral"],
        "groups": [
            "time_dependent_common_SE3_frames",
            "constant_spatial_SE3_postcomposition",
            "Euclidean_E3_configuration_congruence",
            "vertex_relabelings",
            "Poincare_event_transformations",
            "spacetime_coordinate_diffeomorphisms",
            "transported_partition_rigid_isometries",
        ],
        "maps": [
            {
                "id": "rigid_frame_change",
                "domain": "labeled_inertial_configuration",
                "codomain": "labeled_coframed_configuration",
                "kind": "frame_transform",
                "invertibility": "required",
                "information_loss": False,
            },
            {
                "id": "distance_matrix",
                "domain": "labeled_configuration",
                "codomain": "labeled_symmetric_distance_matrix",
                "kind": "deterministic_observation",
                "invertibility": "not_required",
                "information_loss": "possible",
            },
            {
                "id": "bearing_only",
                "domain": "nonzero_observer_relative_positions",
                "codomain": "unit_direction_records",
                "kind": "deterministic_observation",
                "invertibility": "not_required",
                "information_loss": "possible",
            },
            {
                "id": "retarded_signal",
                "domain": "source_and_observer_worldlines",
                "codomain": "reception_time_measurement_record",
                "kind": "deterministic_observation",
                "invertibility": "not_required",
                "information_loss": "possible",
            },
            {
                "id": "spherical_LOS_graph",
                "domain": "labeled_configuration_body_and_thresholds",
                "codomain": "symmetric_snapshot_graph",
                "kind": "deterministic_observation",
                "invertibility": "not_required",
                "information_loss": "possible",
            },
            {
                "id": "uniform_sampler",
                "domain": "continuous_time_record",
                "codomain": "finite_sample_sequence",
                "kind": "discretizer",
                "invertibility": "not_required",
                "information_loss": "possible",
            },
            {
                "id": "temporal_earliest_arrival",
                "domain": "ordered_contact_events_source_and_start_time",
                "codomain": "vertex_arrival_times",
                "kind": "estimator",
                "invertibility": "not_applicable",
                "information_loss": "not_a_map_property",
            },
            {
                "id": "centered_Gram_reconstruction",
                "domain": "labeled_Euclidean_distance_matrix",
                "codomain": "centered_Gram_matrix_and_rank",
                "kind": "estimator",
                "invertibility": "not_applicable",
                "information_loss": "not_a_map_property",
            },
        ],
        "symbols": [
            {"scope": "hidden_state", "key": "X_t", "meaning": "labeled_satellite_network_state"},
            {"scope": "frame", "key": "R_t", "meaning": "orientation_from_frame_to_inertial"},
            {"scope": "frame", "key": "o_t", "meaning": "frame_origin_in_inertial_coordinates"},
            {"scope": "geometry", "key": "D_t", "meaning": "labeled_pairwise_distance_matrix"},
            {"scope": "phase", "key": "L_omega", "meaning": "integer_resonance_lattice"},
            {"scope": "phase", "key": "Gamma_theta_omega", "meaning": "exact_phase_orbit_closure"},
            {"scope": "graph", "key": "A_t", "meaning": "snapshot_link_adjacency"},
            {"scope": "relativity", "key": "tau_gamma", "meaning": "proper_time_on_fixed_worldline_segment"},
        ],
        "quantities": build_quantities(),
        "expressions": build_expressions(),
        "invariants": [
            {
                "id": "labeled_distance_matrix_at_common_time",
                "claimed_invariant": True,
                "group": "time_dependent_common_SE3_frames",
                "anchor": "Theorem 2.1",
            },
            {
                "id": "co_transformed_spherical_segment_clearance",
                "claimed_invariant": True,
                "group": "time_dependent_common_SE3_frames",
                "anchor": "Section 5",
            },
            {
                "id": "snapshot_LOS_graph_with_transformed_body",
                "claimed_invariant": True,
                "group": "time_dependent_common_SE3_frames",
                "anchor": "equation (5.4)",
            },
            {
                "id": "graph_Laplacian_spectrum",
                "claimed_invariant": True,
                "group": "vertex_relabelings",
                "anchor": "Section 5",
            },
            {
                "id": "proper_time_fixed_worldline_endpoints",
                "claimed_invariant": True,
                "group": "spacetime_coordinate_diffeomorphisms",
                "anchor": "equation (7.1)",
            },
            {
                "id": "flat_spacetime_event_interval",
                "claimed_invariant": True,
                "group": "Poincare_event_transformations",
                "anchor": "Section 7",
            },
            {
                "id": "partition_entropy_under_co_transport",
                "claimed_invariant": True,
                "group": "transported_partition_rigid_isometries",
                "anchor": "Section 6",
            },
        ],
        "claim_register": [
            {
                "id": "distance_matrix_invariance",
                "status": "theorem",
                "hypotheses": [
                    "common_coordinate_time",
                    "diagonal_C1_I_SE3_action",
                    "co_transformed_labeled_nodes",
                ],
            },
            {
                "id": "distance_matrix_identification_modulo_E3",
                "status": "theorem",
                "hypotheses": [
                    "labeled_finite_configuration",
                    "positive_semidefinite_centered_Gram_matrix",
                    "rank_at_most_three",
                ],
            },
            {
                "id": "phase_closure_character_lattice",
                "status": "theorem",
                "hypotheses": [
                    "exact_constant_frequency_vector",
                    "continuous_time_linear_flow_on_compact_torus",
                ],
            },
            {
                "id": "closure_equivariance",
                "status": "proposition",
                "hypotheses": [
                    "constant_spatial_rigid_isometry",
                    "continuous_observation_map",
                ],
            },
            {
                "id": "time_dependent_frame_changes_closure",
                "status": "proposition",
                "hypotheses": [
                    "time_dependent_translation_allowed",
                    "stationary_original_trace_counterexample",
                ],
            },
            {
                "id": "uniform_sampling_alias",
                "status": "proposition",
                "hypotheses": [
                    "uniform_sampling_interval_positive",
                    "integer_alias_shift",
                ],
            },
            {
                "id": "spatial_locus_clock_nonidentifiability",
                "status": "proposition",
                "hypotheses": [
                    "unparameterized_spatial_locus",
                    "distinct_speed_histories_allowed",
                    "weak_field_or_Minkowski_clock_model",
                ],
            },
            {
                "id": "proper_time_coordinate_scalar",
                "status": "theorem",
                "hypotheses": [
                    "fixed_timelike_worldline_segment",
                    "fixed_endpoint_events",
                    "Lorentzian_metric_with_minus_plus_plus_plus_signature",
                ],
            },
            {
                "id": "benchmark_controls",
                "status": "empirical",
                "hypotheses": [
                    f"{metrics['benchmark_rows']}_deterministic_rows",
                    "declared_two_body_synthetic_network",
                ],
            },
        ],
        "protocol_fields_present": [
            "hidden_space",
            "system_descriptor",
            "reduction",
            "deterministic_observation",
            "stochastic_channel_or_explicit_noiseless_model",
            "observed_space",
            "reference_frame",
            "quantizer_or_partition",
            "spatial_resolution",
            "temporal_resolution",
            "observation_horizon",
            "estimator_or_declared_direct_readout",
            "uncertainty_or_exactness_statement",
            "unit_context",
            "defect_normalizations",
        ],
        "next_action": "retain_as_final_satellite_frame_temporal_graph_reference_and_run_full_corpus_release",
    }
    ledger = {
        "schema": {
            "id": "go-satellite-networks-reference-ledger",
            "version": "1.2.0",
            "date": "2026-07-28",
            "base_contract": "go-core-spec@0.2.0",
            "inherited_contracts": [
                "go-regular-polyhedra-observation-contract@1.1.0"
            ],
            "extension_contract": "go-satellite-networks-observation-contract@1.2.0",
        },
        "documents": [document],
        "duplicate_or_superseded_sources": [],
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", encoding="utf-8") as stream:
        yaml.safe_dump(
            ledger,
            stream,
            sort_keys=False,
            allow_unicode=True,
            width=100,
        )
    print(
        f"wrote {len(document['expressions'])} expressions to "
        f"{OUTPUT.relative_to(ROOT)}"
    )


if __name__ == "__main__":
    main()
