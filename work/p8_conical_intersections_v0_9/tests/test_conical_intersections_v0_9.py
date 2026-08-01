#!/usr/bin/env python3
"""Regression tests for the P8 conical-intersections reference release."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import subprocess
import sys
import unittest
from pathlib import Path

import numpy as np
import yaml
from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[3]
P8 = ROOT / "work/p8_conical_intersections_v0_9"
sys.path.insert(0, str(P8 / "scripts"))

from generate_conical_intersections_benchmarks import (  # noqa: E402
    IDENTITY,
    SIGMA_X,
    SIGMA_Y,
    SIGMA_Z,
    energy_derivative_coupling,
    gap,
    gap_uncertainty,
    gapped_berry_phase,
    hamiltonian,
    landau_zener_probability,
    numeric_gapped_berry_phase,
    overlap_holonomy,
    physical_pullback,
    projector,
    quantum_metric,
    radius,
    random_gauge_holonomy,
    real_eigenvector,
    unresolved_near_degeneracy,
)


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
BENCHMARKS = P8 / "data/conical_intersections_benchmarks_v0_9.csv"
METRICS = P8 / "data/conical_intersections_metrics_v0_9.json"


def load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as stream:
        value = yaml.safe_load(stream)
    if not isinstance(value, dict):
        raise TypeError(f"{path}: YAML root is not a mapping")
    return value


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as stream:
        value = json.load(stream)
    if not isinstance(value, dict):
        raise TypeError(f"{path}: JSON root is not an object")
    return value


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


class SpectrumAndCoordinateTests(unittest.TestCase):
    def test_pauli_matrices_are_Hermitian(self) -> None:
        for matrix in (SIGMA_X, SIGMA_Y, SIGMA_Z):
            np.testing.assert_allclose(matrix, matrix.conj().T)

    def test_pauli_matrices_square_to_identity(self) -> None:
        for matrix in (SIGMA_X, SIGMA_Y, SIGMA_Z):
            np.testing.assert_allclose(matrix @ matrix, IDENTITY)

    def test_pauli_matrices_are_traceless(self) -> None:
        for matrix in (SIGMA_X, SIGMA_Y, SIGMA_Z):
            self.assertAlmostEqual(float(np.trace(matrix).real), 0.0)

    def test_real_normal_form_is_real_symmetric(self) -> None:
        matrix = hamiltonian(0.3, -0.8)
        np.testing.assert_allclose(matrix.imag, 0.0)
        np.testing.assert_allclose(matrix, matrix.T)

    def test_sigma_y_control_is_not_real(self) -> None:
        matrix = hamiltonian(0.3, -0.8, 0.2)
        self.assertGreater(float(np.linalg.norm(matrix.imag)), 0.0)
        np.testing.assert_allclose(matrix, matrix.conj().T)

    def test_trace_is_zero(self) -> None:
        self.assertAlmostEqual(
            complex(np.trace(hamiltonian(3.0, 4.0))).real,
            0.0,
        )

    def test_determinant_is_minus_radius_squared(self) -> None:
        x, y = 3.0, 4.0
        self.assertAlmostEqual(
            float(np.linalg.det(hamiltonian(x, y)).real),
            -(x * x + y * y),
        )

    def test_three_four_five_spectrum(self) -> None:
        values = np.linalg.eigvalsh(hamiltonian(3.0, 4.0))
        np.testing.assert_allclose(values, [-5.0, 5.0])
        self.assertAlmostEqual(gap(3.0, 4.0), 10.0)

    def test_gap_is_nonnegative(self) -> None:
        self.assertGreaterEqual(gap(-3.0, -4.0), 0.0)

    def test_gap_closes_only_at_origin(self) -> None:
        self.assertEqual(gap(0.0, 0.0), 0.0)
        self.assertGreater(gap(1e-30, 0.0), 0.0)

    def test_uniform_energy_scaling(self) -> None:
        x, y, scale = 0.7, -1.2, 4.3
        self.assertAlmostEqual(
            gap(scale * x, scale * y),
            scale * gap(x, y),
        )

    def test_gapped_control_minimum(self) -> None:
        self.assertAlmostEqual(gap(0.0, 0.0, 0.7), 1.4)

    def test_gapped_control_strictly_positive(self) -> None:
        for x, y in ((0.0, 0.0), (1.0, 0.0), (-2.0, 3.0)):
            self.assertGreater(gap(x, y, 0.2), 0.0)

    def test_contract_types_energy_coordinates(self) -> None:
        coordinate = load_yaml(CONTRACT)["coordinate_typing"]
        self.assertEqual(
            coordinate["energy_branching_map"]["dimensions"]["x"],
            "energy",
        )
        self.assertIn(
            "nuclear_length_coordinates_are_not_energy_coordinates",
            coordinate["prohibition"],
        )

    def test_linear_coordinate_dimension_expression_is_registered(self) -> None:
        expressions = load_yaml(REFERENCE_LEDGER)["documents"][0]["expressions"]
        identifiers = {item["id"] for item in expressions}
        self.assertIn("x_from_physical_coordinate", identifiers)
        self.assertIn("y_from_physical_coordinate", identifiers)


def _add_spectrum_case(name: str, x: float, y: float) -> None:
    def test(self: SpectrumAndCoordinateTests) -> None:
        values = np.linalg.eigvalsh(hamiltonian(x, y))
        r = radius(x, y)
        np.testing.assert_allclose(values, [-r, r], atol=1e-14)
        self.assertAlmostEqual(values[1] - values[0], gap(x, y))

    setattr(SpectrumAndCoordinateTests, f"test_spectrum_{name}", test)


for _name, _x, _y in (
    ("axis_x_positive", 2.5, 0.0),
    ("axis_x_negative", -2.5, 0.0),
    ("axis_y_positive", 0.0, 2.5),
    ("axis_y_negative", 0.0, -2.5),
    ("quadrant_one", 1.2, 3.4),
    ("quadrant_two", -1.2, 3.4),
    ("quadrant_three", -1.2, -3.4),
    ("quadrant_four", 1.2, -3.4),
    ("small_radius", 3e-9, -4e-9),
    ("large_radius", 3e9, -4e9),
    ("irrational_values", math.sqrt(2.0), math.pi),
    ("unequal_scales", 1e-7, 2e4),
):
    _add_spectrum_case(_name, _x, _y)


class ProjectorAndGaugeTests(unittest.TestCase):
    def test_projector_is_Hermitian(self) -> None:
        for sign in (-1, 1):
            value = projector(3.0, 4.0, sign)
            np.testing.assert_allclose(value, value.conj().T)

    def test_projector_is_idempotent(self) -> None:
        for sign in (-1, 1):
            value = projector(3.0, 4.0, sign)
            np.testing.assert_allclose(value @ value, value, atol=1e-15)

    def test_projector_has_trace_one(self) -> None:
        for sign in (-1, 1):
            self.assertAlmostEqual(
                float(np.trace(projector(3.0, 4.0, sign)).real),
                1.0,
            )

    def test_projectors_are_orthogonal(self) -> None:
        lower = projector(3.0, 4.0, -1)
        upper = projector(3.0, 4.0, 1)
        np.testing.assert_allclose(lower @ upper, 0.0, atol=1e-15)

    def test_projectors_sum_to_cluster_identity(self) -> None:
        np.testing.assert_allclose(
            projector(3.0, 4.0, -1) + projector(3.0, 4.0, 1),
            IDENTITY,
        )

    def test_projector_eigenvalue_equation(self) -> None:
        matrix = hamiltonian(3.0, 4.0)
        lower = projector(3.0, 4.0, -1)
        upper = projector(3.0, 4.0, 1)
        np.testing.assert_allclose(matrix @ lower, -5.0 * lower)
        np.testing.assert_allclose(matrix @ upper, 5.0 * upper)

    def test_projector_rejects_exact_seam(self) -> None:
        with self.assertRaises(ValueError):
            projector(0.0, 0.0, -1)

    def test_projector_rejects_invalid_sign(self) -> None:
        with self.assertRaises(ValueError):
            projector(1.0, 0.0, 0)

    def test_no_unique_lower_projector_limit(self) -> None:
        positive = projector(1e-12, 0.0, -1)
        negative = projector(-1e-12, 0.0, -1)
        self.assertGreater(float(np.linalg.norm(positive - negative)), 1.0)

    def test_cluster_projector_has_unique_limit(self) -> None:
        for phi in np.linspace(0.0, 2.0 * math.pi, 17):
            x, y = 1e-12 * math.cos(phi), 1e-12 * math.sin(phi)
            cluster = projector(x, y, -1) + projector(x, y, 1)
            np.testing.assert_allclose(cluster, IDENTITY, atol=1e-15)

    def test_local_eigenvector_normalization(self) -> None:
        for sign in (-1, 1):
            self.assertAlmostEqual(
                float(np.vdot(real_eigenvector(0.7, sign),
                              real_eigenvector(0.7, sign)).real),
                1.0,
            )

    def test_local_eigenvectors_are_orthogonal(self) -> None:
        self.assertAlmostEqual(
            abs(
                np.vdot(
                    real_eigenvector(0.7, -1),
                    real_eigenvector(0.7, 1),
                )
            ),
            0.0,
        )

    def test_real_section_changes_sign_after_turn(self) -> None:
        for sign in (-1, 1):
            np.testing.assert_allclose(
                real_eigenvector(2.0 * math.pi, sign),
                -real_eigenvector(0.0, sign),
                atol=1e-15,
            )

    def test_local_vector_projector_matches_formula(self) -> None:
        phi = 1.1
        x, y = math.cos(phi), math.sin(phi)
        vector = real_eigenvector(phi, -1)
        from_vector = np.outer(vector, vector.conj())
        np.testing.assert_allclose(
            from_vector,
            projector(x, y, -1),
            atol=1e-15,
        )

    def test_projector_is_phase_gauge_invariant(self) -> None:
        vector = real_eigenvector(0.8, -1)
        phase = np.exp(1.0j * 1.234)
        base = np.outer(vector, vector.conj())
        gauged = np.outer(phase * vector, (phase * vector).conj())
        np.testing.assert_allclose(base, gauged, atol=1e-15)

    def test_contract_separates_cluster_and_rank_one_projectors(self) -> None:
        cluster = load_yaml(CONTRACT)["spectral_cluster"]
        self.assertEqual(
            cluster["internal_splitting"]["behavior_at_seam"][
                "rank_one_projectors"
            ],
            "no_unique_extension",
        )
        self.assertEqual(
            cluster["internal_splitting"]["behavior_at_seam"][
                "cluster_projector"
            ],
            "remains_defined",
        )


def _add_projector_direction_case(name: str, phi: float) -> None:
    def test(self: ProjectorAndGaugeTests) -> None:
        x, y = math.cos(phi), math.sin(phi)
        lower = projector(x, y, -1)
        upper = projector(x, y, 1)
        np.testing.assert_allclose(lower @ lower, lower, atol=1e-15)
        np.testing.assert_allclose(upper @ upper, upper, atol=1e-15)
        np.testing.assert_allclose(lower + upper, IDENTITY, atol=1e-15)

    setattr(ProjectorAndGaugeTests, f"test_direction_{name}", test)


for _name, _phi in (
    ("zero", 0.0),
    ("pi_over_six", math.pi / 6.0),
    ("pi_over_three", math.pi / 3.0),
    ("pi_over_two", math.pi / 2.0),
    ("five_pi_over_six", 5.0 * math.pi / 6.0),
    ("pi", math.pi),
    ("three_pi_over_two", 3.0 * math.pi / 2.0),
    ("almost_two_pi", 2.0 * math.pi - 1e-6),
):
    _add_projector_direction_case(_name, _phi)


class HolonomyTests(unittest.TestCase):
    def test_odd_winding_has_minus_one_holonomy(self) -> None:
        self.assertAlmostEqual(overlap_holonomy(1).real, -1.0)

    def test_even_winding_has_plus_one_holonomy(self) -> None:
        self.assertAlmostEqual(overlap_holonomy(2).real, 1.0)

    def test_zero_winding_has_plus_one_holonomy(self) -> None:
        self.assertAlmostEqual(overlap_holonomy(0).real, 1.0)

    def test_negative_winding_has_same_Z2_parity(self) -> None:
        self.assertAlmostEqual(overlap_holonomy(-1).real, -1.0)

    def test_holonomy_has_unit_modulus(self) -> None:
        for winding in range(-4, 5):
            self.assertAlmostEqual(abs(overlap_holonomy(winding)), 1.0)

    def test_random_local_gauge_does_not_change_holonomy(self) -> None:
        for winding in range(-3, 4):
            self.assertAlmostEqual(
                abs(
                    random_gauge_holonomy(winding)
                    - overlap_holonomy(winding)
                ),
                0.0,
                places=13,
            )

    def test_sampling_guard(self) -> None:
        with self.assertRaises(ValueError):
            overlap_holonomy(8, samples=8)

    def test_gapped_phase_at_equal_radius_and_delta(self) -> None:
        expected = math.pi * (1.0 - 1.0 / math.sqrt(2.0))
        self.assertAlmostEqual(gapped_berry_phase(1.0, 1.0), expected)

    def test_gapped_numeric_matches_solid_angle_formula(self) -> None:
        self.assertAlmostEqual(
            numeric_gapped_berry_phase(1.0, 0.5, samples=8192),
            gapped_berry_phase(1.0, 0.5),
            places=6,
        )

    def test_gapped_phase_tends_toward_pi_for_small_delta(self) -> None:
        self.assertGreater(gapped_berry_phase(1.0, 1e-6), 0.999 * math.pi)

    def test_gapped_phase_tends_toward_zero_for_large_delta(self) -> None:
        self.assertLess(gapped_berry_phase(1.0, 1e6), 1e-10)

    def test_gapped_phase_rejects_nonpositive_parameters(self) -> None:
        with self.assertRaises(ValueError):
            gapped_berry_phase(0.0, 1.0)
        with self.assertRaises(ValueError):
            gapped_berry_phase(1.0, 0.0)

    def test_contract_calls_caustic_an_analogy(self) -> None:
        caustic = load_yaml(CONTRACT)["spectral_discriminant"][
            "caustic_language"
        ]
        self.assertEqual(caustic["formal_status"], "analogy")

    def test_contract_rejects_global_eigenvector_output(self) -> None:
        prohibitions = load_yaml(CONTRACT)["projector_and_gauge"][
            "prohibition"
        ]
        self.assertIn(
            "global_eigenvector_is_not_a_gauge_invariant_observation",
            prohibitions,
        )


def _add_holonomy_winding_case(winding: int) -> None:
    def test(self: HolonomyTests) -> None:
        expected = -1.0 if winding % 2 else 1.0
        observed = overlap_holonomy(winding, samples=256)
        self.assertAlmostEqual(observed.real, expected, places=13)
        self.assertAlmostEqual(observed.imag, 0.0, places=13)

    suffix = str(winding).replace("-", "minus_")
    setattr(HolonomyTests, f"test_winding_{suffix}", test)


for _winding in range(-4, 5):
    _add_holonomy_winding_case(_winding)


class NonadiabaticMetricTests(unittest.TestCase):
    def test_energy_coupling_at_axis(self) -> None:
        np.testing.assert_allclose(
            energy_derivative_coupling(1.0, 0.0),
            [0.0, -0.5],
        )

    def test_energy_coupling_norm(self) -> None:
        x, y = 3.0, 4.0
        self.assertAlmostEqual(
            float(np.linalg.norm(energy_derivative_coupling(x, y))),
            1.0 / (2.0 * radius(x, y)),
        )

    def test_energy_coupling_rejects_seam(self) -> None:
        with self.assertRaises(ValueError):
            energy_derivative_coupling(0.0, 0.0)

    def test_quantum_metric_is_symmetric(self) -> None:
        metric = quantum_metric(3.0, 4.0)
        np.testing.assert_allclose(metric, metric.T)

    def test_quantum_metric_is_positive_semidefinite(self) -> None:
        eigenvalues = np.linalg.eigvalsh(quantum_metric(3.0, 4.0))
        self.assertGreaterEqual(eigenvalues[0], -1e-16)
        self.assertGreater(eigenvalues[1], 0.0)

    def test_quantum_metric_has_radial_null_direction(self) -> None:
        x, y = 3.0, 4.0
        metric = quantum_metric(x, y)
        np.testing.assert_allclose(
            metric @ np.array([x, y]),
            0.0,
            atol=1e-16,
        )

    def test_quantum_metric_trace_identity(self) -> None:
        x, y = 3.0, 4.0
        self.assertAlmostEqual(
            float(np.trace(quantum_metric(x, y))),
            1.0 / (4.0 * radius(x, y) ** 2),
        )

    def test_metric_equals_coupling_outer_product(self) -> None:
        x, y = 3.0, 4.0
        coupling = energy_derivative_coupling(x, y)
        np.testing.assert_allclose(
            quantum_metric(x, y),
            np.outer(coupling, coupling),
        )

    def test_projector_finite_difference_metric(self) -> None:
        x, y, step = 0.8, -1.3, 1e-6
        dpx = (
            projector(x + step, y, -1)
            - projector(x - step, y, -1)
        ) / (2.0 * step)
        dpy = (
            projector(x, y + step, -1)
            - projector(x, y - step, -1)
        ) / (2.0 * step)
        numeric = np.array(
            [
                [
                    0.5 * np.trace(dpx @ dpx).real,
                    0.5 * np.trace(dpx @ dpy).real,
                ],
                [
                    0.5 * np.trace(dpy @ dpx).real,
                    0.5 * np.trace(dpy @ dpy).real,
                ],
            ]
        )
        np.testing.assert_allclose(
            numeric,
            quantum_metric(x, y),
            rtol=1e-9,
            atol=1e-11,
        )

    def test_identity_jacobian_pullback(self) -> None:
        metric = quantum_metric(3.0, 4.0)
        np.testing.assert_allclose(
            physical_pullback(metric, np.eye(2)),
            metric,
        )

    def test_rectangular_jacobian_pullback_shape(self) -> None:
        metric = quantum_metric(3.0, 4.0)
        jacobian = np.array([[1.0, 2.0, 0.0], [0.0, -1.0, 4.0]])
        pulled = physical_pullback(metric, jacobian)
        self.assertEqual(pulled.shape, (3, 3))
        np.testing.assert_allclose(pulled, pulled.T)

    def test_pullback_is_positive_semidefinite(self) -> None:
        metric = quantum_metric(3.0, 4.0)
        jacobian = np.array([[1.0, 2.0, 0.0], [0.0, -1.0, 4.0]])
        eigenvalues = np.linalg.eigvalsh(physical_pullback(metric, jacobian))
        self.assertGreaterEqual(eigenvalues[0], -1e-15)

    def test_pullback_rejects_wrong_metric_shape(self) -> None:
        with self.assertRaises(ValueError):
            physical_pullback(np.eye(3), np.eye(2))

    def test_pullback_rejects_wrong_jacobian_rows(self) -> None:
        with self.assertRaises(ValueError):
            physical_pullback(np.eye(2), np.eye(3))

    def test_contract_records_physical_pullback_dimensions(self) -> None:
        pullback = load_yaml(CONTRACT)["nonadiabatic_geometry"][
            "physical_pullback"
        ]
        self.assertEqual(pullback["dimensions"]["d_q"], "inverse_length")
        self.assertEqual(
            pullback["dimensions"]["g_q"],
            "inverse_length_squared",
        )


def _add_metric_radius_case(name: str, r: float) -> None:
    def test(self: NonadiabaticMetricTests) -> None:
        coupling = energy_derivative_coupling(r, 0.0)
        metric = quantum_metric(r, 0.0)
        self.assertAlmostEqual(float(np.linalg.norm(coupling)), 1.0 / (2.0 * r))
        self.assertAlmostEqual(float(np.trace(metric)), 1.0 / (4.0 * r * r))

    setattr(NonadiabaticMetricTests, f"test_radius_{name}", test)


for _name, _r in (
    ("one", 1.0),
    ("half", 0.5),
    ("quarter", 0.25),
    ("tenth", 0.1),
    ("hundredth", 0.01),
    ("small", 1e-4),
    ("large", 1e2),
    ("very_large", 1e6),
):
    _add_metric_radius_case(_name, _r)


class DynamicsTests(unittest.TestCase):
    def test_LZ_zero_coupling_probability_one(self) -> None:
        self.assertEqual(landau_zener_probability(0.0, 1.0), 1.0)

    def test_LZ_equal_energy_squared_scales(self) -> None:
        self.assertAlmostEqual(
            landau_zener_probability(1.0, 1.0),
            math.exp(-math.pi),
        )

    def test_LZ_probability_between_zero_and_one(self) -> None:
        value = landau_zener_probability(0.7, 0.3)
        self.assertGreater(value, 0.0)
        self.assertLess(value, 1.0)

    def test_LZ_decreases_with_coupling(self) -> None:
        self.assertGreater(
            landau_zener_probability(0.5, 1.0),
            landau_zener_probability(1.0, 1.0),
        )

    def test_LZ_increases_with_sweep_rate(self) -> None:
        self.assertLess(
            landau_zener_probability(1.0, 0.5),
            landau_zener_probability(1.0, 2.0),
        )

    def test_LZ_rejects_negative_coupling_magnitude(self) -> None:
        with self.assertRaises(ValueError):
            landau_zener_probability(-1.0, 1.0)

    def test_LZ_rejects_nonpositive_hbar_rate(self) -> None:
        with self.assertRaises(ValueError):
            landau_zener_probability(1.0, 0.0)

    def test_same_gap_different_rate_different_probability(self) -> None:
        slow = landau_zener_probability(0.5, 0.2)
        fast = landau_zener_probability(0.5, 2.0)
        self.assertNotAlmostEqual(slow, fast)

    def test_contract_separates_static_gap_and_dynamics(self) -> None:
        prohibition = load_yaml(CONTRACT)["born_oppenheimer_dynamics"][
            "prohibition"
        ]
        self.assertIn(
            "static_gap_does_not_determine_transition_probability",
            prohibition,
        )

    def test_adiabatic_parameter_expression_is_dimensionless(self) -> None:
        expressions = load_yaml(REFERENCE_LEDGER)["documents"][0]["expressions"]
        expression = next(
            item for item in expressions if item["id"] == "adiabatic_parameter"
        )
        self.assertEqual(expression["expect"]["dimension"], [0] * 7)


def _add_LZ_ratio_case(name: str, ratio: float) -> None:
    def test(self: DynamicsTests) -> None:
        coupling = math.sqrt(ratio)
        self.assertAlmostEqual(
            landau_zener_probability(coupling, 1.0),
            math.exp(-math.pi * ratio),
        )

    setattr(DynamicsTests, f"test_LZ_ratio_{name}", test)


for _name, _ratio in (
    ("zero", 0.0),
    ("one_tenth", 0.1),
    ("one_quarter", 0.25),
    ("one_half", 0.5),
    ("one", 1.0),
    ("two", 2.0),
    ("five", 5.0),
    ("ten", 10.0),
):
    _add_LZ_ratio_case(_name, _ratio)


class ObservationAndUncertaintyTests(unittest.TestCase):
    def test_independent_equal_errors(self) -> None:
        sigma = gap_uncertainty(0.02, 0.02, 0.0)
        self.assertAlmostEqual(sigma, math.sqrt(2.0) * 0.02)

    def test_positive_covariance_reduces_gap_uncertainty(self) -> None:
        independent = gap_uncertainty(0.02, 0.02, 0.0)
        correlated = gap_uncertainty(0.02, 0.02, 0.0002)
        self.assertLess(correlated, independent)

    def test_negative_covariance_increases_gap_uncertainty(self) -> None:
        independent = gap_uncertainty(0.02, 0.02, 0.0)
        anticorrelated = gap_uncertainty(0.02, 0.02, -0.0002)
        self.assertGreater(anticorrelated, independent)

    def test_perfect_common_mode_cancels(self) -> None:
        self.assertAlmostEqual(gap_uncertainty(0.02, 0.02, 0.0004), 0.0)

    def test_invalid_covariance_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            gap_uncertainty(0.01, 0.01, 0.001)

    def test_negative_sigma_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            gap_uncertainty(-0.01, 0.01, 0.0)

    def test_unresolved_rule_accepts_small_gap(self) -> None:
        self.assertTrue(unresolved_near_degeneracy(0.01, 0.02, 2.0, 0.0))

    def test_unresolved_rule_rejects_resolved_gap(self) -> None:
        self.assertFalse(unresolved_near_degeneracy(0.05, 0.02, 2.0, 0.0))

    def test_unresolved_rule_is_symmetric_in_gap_sign(self) -> None:
        positive = unresolved_near_degeneracy(0.03, 0.02, 1.0, 0.02)
        negative = unresolved_near_degeneracy(-0.03, 0.02, 1.0, 0.02)
        self.assertEqual(positive, negative)

    def test_resolution_expands_unresolved_region(self) -> None:
        without = unresolved_near_degeneracy(0.03, 0.01, 1.0, 0.0)
        with_resolution = unresolved_near_degeneracy(
            0.03, 0.01, 1.0, 0.03
        )
        self.assertFalse(without)
        self.assertTrue(with_resolution)

    def test_negative_threshold_inputs_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            unresolved_near_degeneracy(0.0, -0.1, 1.0, 0.0)
        with self.assertRaises(ValueError):
            unresolved_near_degeneracy(0.0, 0.1, -1.0, 0.0)
        with self.assertRaises(ValueError):
            unresolved_near_degeneracy(0.0, 0.1, 1.0, -0.1)

    def test_contract_labels_rule_as_unresolved_not_exact_CI(self) -> None:
        finite = load_yaml(CONTRACT)["finite_resolution"]
        self.assertEqual(
            finite["rule_semantics"],
            "unresolved_near_degeneracy_not_exact_CI_certificate",
        )

    def test_energy_values_do_not_recover_projectors(self) -> None:
        identifiability = load_yaml(CONTRACT)["observation_chain"][
            "identifiability"
        ]["energy_values_alone"]
        self.assertFalse(identifiability["recover_projectors"])

    def test_energy_values_do_not_recover_Berry_holonomy(self) -> None:
        identifiability = load_yaml(CONTRACT)["observation_chain"][
            "identifiability"
        ]["energy_values_alone"]
        self.assertFalse(identifiability["recover_Berry_holonomy"])


class ContractLedgerAndArtifactTests(unittest.TestCase):
    def test_contract_schema(self) -> None:
        schema = load_yaml(CONTRACT)["schema"]
        self.assertEqual(
            schema["id"],
            "go-conical-intersections-observation-contract",
        )
        self.assertEqual(schema["version"], "0.9.0")

    def test_contract_has_twelve_reference_gates(self) -> None:
        self.assertEqual(len(load_yaml(CONTRACT)["reference_gates"]), 12)

    def test_reference_ledger_has_one_reference(self) -> None:
        documents = load_yaml(REFERENCE_LEDGER)["documents"]
        self.assertEqual(len(documents), 1)
        self.assertEqual(documents[0]["ledger_level"], "reference")

    def test_reference_ledger_has_36_expressions(self) -> None:
        expressions = load_yaml(REFERENCE_LEDGER)["documents"][0]["expressions"]
        self.assertEqual(len(expressions), 36)

    def test_reference_lint_is_clean(self) -> None:
        summary = load_json(REFERENCE_LINT)["summary"]
        self.assertEqual(summary["status_counts"], {"PASS": 1})
        self.assertEqual(summary["findings_total"], 0)
        self.assertEqual(summary["expressions_checked"], 36)

    def test_corpus_has_15_pass_and_3_fail(self) -> None:
        summary = load_json(CORPUS_LINT)["summary"]
        self.assertEqual(summary["status_counts"], {"FAIL": 3, "PASS": 15})

    def test_corpus_has_208_expressions(self) -> None:
        self.assertEqual(
            load_json(CORPUS_LINT)["summary"]["expressions_checked"],
            208,
        )

    def test_corpus_has_8_legacy_findings(self) -> None:
        self.assertEqual(
            load_json(CORPUS_LINT)["summary"]["findings_total"],
            8,
        )

    def test_old_conical_adapter_is_absent(self) -> None:
        ids = {
            item["id"]
            for item in load_yaml(CORPUS_LEDGER)["documents"]
        }
        self.assertNotIn("conical-intersections-v1", ids)
        self.assertIn("conical-intersections-observation-v1-1", ids)

    def test_legacy_conical_sources_are_superseded(self) -> None:
        records = load_yaml(CORPUS_LEDGER)[
            "duplicate_or_superseded_sources"
        ]
        conical = [
            item
            for item in records
            if "conical_intersections" in item.get("path", "")
        ]
        self.assertEqual(len(conical), 2)
        self.assertTrue(all(item["status"] == "superseded" for item in conical))

    def test_pdf_metadata_and_page_count(self) -> None:
        reader = PdfReader(PDF)
        metadata = reader.metadata or {}
        self.assertEqual(len(reader.pages), 8)
        self.assertEqual(
            metadata.get("/Title"),
            "Conical Intersections as Typed Spectral Singularities under Observation Maps",
        )
        self.assertEqual(
            metadata.get("/Author"),
            "Stas, Independent Research Program",
        )

    def test_pdf_hash_matches_reference_ledger(self) -> None:
        document = load_yaml(REFERENCE_LEDGER)["documents"][0]
        self.assertEqual(sha256(PDF), document["source"]["sha256"])

    def test_all_fonts_are_embedded(self) -> None:
        process = subprocess.run(
            ["pdffonts", str(PDF)],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(process.returncode, 0)
        rows = [
            line.split()
            for line in process.stdout.splitlines()[2:]
            if line.strip()
        ]
        self.assertTrue(rows)
        self.assertTrue(all(len(row) >= 6 and row[-4] == "yes" for row in rows))

    def test_latex_log_has_no_layout_or_reference_warnings(self) -> None:
        log = LOG.read_text(encoding="utf-8", errors="replace")
        for token in (
            "Overfull",
            "Underfull",
            "LaTeX Warning",
            "undefined references",
            "multiply defined",
            "Missing character",
        ):
            self.assertNotIn(token, log)

    def test_source_has_one_references_heading(self) -> None:
        self.assertEqual(
            TEX.read_text(encoding="utf-8").count(r"\section*{References}"),
            1,
        )

    def test_extracted_text_has_one_references_heading(self) -> None:
        headings = [
            line.strip()
            for line in TEXT.read_text(
                encoding="utf-8", errors="replace"
            ).splitlines()
            if line.strip() == "References"
        ]
        self.assertEqual(len(headings), 1)

    def test_required_source_fragments(self) -> None:
        source = TEX.read_text(encoding="utf-8")
        for fragment in (
            r"\section{Projectors, eigenlines, and gauge}",
            r"\section{Berry holonomy without a global eigenvector}",
            r"\section{Derivative coupling and quantum metric}",
            r"\section{Born--Oppenheimer reduction and dynamics firewall}",
            r"\section{Observation chain and finite-resolution identifiability}",
            r"P_{\rm cl}=P_++P_-=I_2",
            r"d_{+-}^{(q)}=J^\mathsf T d_{+-}^{(E)}",
            r"P_{\rm D}=\exp",
        ):
            self.assertIn(fragment, source)

    def test_no_prohibited_tokens(self) -> None:
        for path in (TEX, TEXT):
            content = path.read_text(encoding="utf-8", errors="replace")
            for token in ("TODO", "TBD", "\ufffd"):
                self.assertNotIn(token, content)

    def test_benchmark_row_count(self) -> None:
        with BENCHMARKS.open("r", encoding="utf-8", newline="") as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual(len(rows), 35)

    def test_benchmark_family_counts(self) -> None:
        metrics = load_json(METRICS)
        self.assertEqual(
            metrics["family_counts"],
            {
                "derivative_coupling": 6,
                "finite_resolution": 4,
                "gapped_berry": 6,
                "landau_zener": 6,
                "real_holonomy": 7,
                "spectrum": 6,
            },
        )

    def test_numerical_residuals_are_bounded(self) -> None:
        metrics = load_json(METRICS)
        self.assertLess(
            metrics["max_projector_idempotence_residual"],
            1e-14,
        )
        self.assertLess(
            metrics["max_projector_orthogonality_residual"],
            1e-14,
        )
        self.assertLess(
            metrics["max_quantum_metric_identity_residual"],
            1e-12,
        )
        self.assertLess(
            metrics["max_random_gauge_holonomy_residual"],
            1e-12,
        )
        self.assertLess(
            metrics["max_gapped_berry_discretization_error"],
            3e-7,
        )


if __name__ == "__main__":
    unittest.main()
