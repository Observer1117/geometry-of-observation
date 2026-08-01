#!/usr/bin/env python3
"""Independent regressions for the P9 quantum-chemistry reference release."""

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
P9 = ROOT / "work/p9_quantum_chemistry_v1_0"
sys.path.insert(0, str(P9 / "scripts"))

from generate_quantum_chemistry_benchmarks import (  # noqa: E402
    C_LIGHT,
    H_PLANCK,
    HBAR,
    active_occupation,
    diatomic_cartesian_hessian,
    electron_count,
    gaussian_line,
    gaussian_response_convolution,
    generalized_eigh,
    generalized_residual,
    harmonic_angular_frequencies,
    ideal_absorption_spectrum,
    mass_weighted_hessian,
    normal_mode_eigenvalues,
    occupied_density,
    one_body_expectation,
    pair_coherence_expectation,
    paired_phase_one_rdm,
    random_unitary,
    rayleigh_ritz_ground_sequence,
    repeated_mass_matrix,
    s_orthonormality_error,
    synthetic_mass_weighted_modes,
    transition_angular_frequency,
    transition_cyclic_frequency,
    two_determinant_exact_formula,
    two_determinant_ground_energy,
)


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
BENCHMARKS = P9 / "data/quantum_chemistry_benchmarks_v1_0.csv"
METRICS = P9 / "data/quantum_chemistry_metrics_v1_0.json"


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


def random_positive_definite(size: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    raw = rng.normal(size=(size, size))
    return raw.T @ raw + (0.6 + 0.2 * size) * np.eye(size)


def random_symmetric(size: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    raw = rng.normal(size=(size, size))
    return 0.5 * (raw + raw.T)


class GeneralizedEigenproblemTests(unittest.TestCase):
    def test_identity_overlap_reduces_to_standard_problem(self) -> None:
        fock = np.array([[2.0, -0.4], [-0.4, 0.3]])
        values, coefficients = generalized_eigh(fock, np.eye(2))
        np.testing.assert_allclose(values, np.linalg.eigvalsh(fock))
        np.testing.assert_allclose(
            coefficients.conj().T @ coefficients,
            np.eye(2),
            atol=1e-14,
        )

    def test_complex_Hermitian_problem(self) -> None:
        fock = np.array([[1.0, 0.2j], [-0.2j, 3.0]], dtype=complex)
        overlap = np.array([[1.2, 0.1j], [-0.1j, 0.9]], dtype=complex)
        values, coefficients = generalized_eigh(fock, overlap)
        self.assertLess(
            generalized_residual(fock, overlap, values, coefficients),
            1e-13,
        )
        self.assertLess(
            s_orthonormality_error(coefficients, overlap),
            1e-13,
        )

    def test_non_Hermitian_fock_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            generalized_eigh(
                np.array([[1.0, 1.0], [0.0, 2.0]]),
                np.eye(2),
            )

    def test_non_Hermitian_overlap_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            generalized_eigh(
                np.eye(2),
                np.array([[1.0, 1.0], [0.0, 1.0]]),
            )

    def test_singular_overlap_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            generalized_eigh(np.eye(2), np.diag([1.0, 0.0]))

    def test_indefinite_overlap_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            generalized_eigh(np.eye(2), np.diag([1.0, -0.1]))

    def test_threshold_guard_is_relative(self) -> None:
        with self.assertRaises(ValueError):
            generalized_eigh(
                np.eye(2),
                np.diag([1.0, 1e-14]),
                threshold=1e-12,
            )

    def test_shape_mismatch_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            generalized_eigh(np.eye(2), np.eye(3))

    def test_eigenvalues_are_sorted(self) -> None:
        values, _ = generalized_eigh(
            np.diag([4.0, -1.0, 2.0]),
            np.eye(3),
        )
        self.assertTrue(np.all(np.diff(values) >= 0.0))

    def test_ledger_registers_overlap_equations(self) -> None:
        identifiers = {
            item["id"]
            for item in load_yaml(REFERENCE_LEDGER)["documents"][0][
                "expressions"
            ]
        }
        self.assertIn("generalized_eigenproblem_dimension_match", identifiers)
        self.assertIn("F_times_C", identifiers)
        self.assertIn("S_C_times_epsilon", identifiers)


def add_generalized_case(seed: int) -> None:
    def test_residual(self: GeneralizedEigenproblemTests) -> None:
        size = 3 + seed % 5
        fock = random_symmetric(size, 1000 + seed)
        overlap = random_positive_definite(size, 2000 + seed)
        values, coefficients = generalized_eigh(fock, overlap)
        self.assertLess(
            generalized_residual(fock, overlap, values, coefficients),
            2e-11,
        )

    def test_metric(self: GeneralizedEigenproblemTests) -> None:
        size = 3 + seed % 5
        fock = random_symmetric(size, 1000 + seed)
        overlap = random_positive_definite(size, 2000 + seed)
        _, coefficients = generalized_eigh(fock, overlap)
        self.assertLess(
            s_orthonormality_error(coefficients, overlap),
            2e-11,
        )

    def test_spectrum(self: GeneralizedEigenproblemTests) -> None:
        size = 3 + seed % 5
        fock = random_symmetric(size, 1000 + seed)
        overlap = random_positive_definite(size, 2000 + seed)
        values, _ = generalized_eigh(fock, overlap)
        direct = np.sort(np.linalg.eigvals(np.linalg.solve(overlap, fock)).real)
        np.testing.assert_allclose(values, direct, atol=2e-11, rtol=1e-11)

    setattr(
        GeneralizedEigenproblemTests,
        f"test_random_residual_seed_{seed:02d}",
        test_residual,
    )
    setattr(
        GeneralizedEigenproblemTests,
        f"test_random_metric_seed_{seed:02d}",
        test_metric,
    )
    setattr(
        GeneralizedEigenproblemTests,
        f"test_random_spectrum_seed_{seed:02d}",
        test_spectrum,
    )


for _seed in range(16):
    add_generalized_case(_seed)


class OrbitalGaugeTests(unittest.TestCase):
    def test_unitary_constructor(self) -> None:
        unitary = random_unitary(5, 17)
        np.testing.assert_allclose(
            unitary.conj().T @ unitary,
            np.eye(5),
            atol=1e-14,
        )

    def test_default_occupations(self) -> None:
        coefficients = np.eye(4)[:, :2]
        np.testing.assert_allclose(
            occupied_density(coefficients),
            np.diag([1.0, 1.0, 0.0, 0.0]),
        )

    def test_fractional_occupations(self) -> None:
        coefficients = np.eye(4)[:, :3]
        density = occupied_density(
            coefficients,
            np.array([1.0, 0.5, 0.25]),
        )
        np.testing.assert_allclose(
            density,
            np.diag([1.0, 0.5, 0.25, 0.0]),
        )

    def test_bad_occupation_shape_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            occupied_density(np.eye(3)[:, :2], np.ones(3))

    def test_nonunitary_rotation_changes_density(self) -> None:
        coefficients = np.eye(4)[:, :2]
        scaling = np.diag([2.0, 0.5])
        self.assertGreater(
            np.linalg.norm(
                occupied_density(coefficients @ scaling)
                - occupied_density(coefficients)
            ),
            1.0,
        )

    def test_contract_declares_occupied_unitary_group(self) -> None:
        gauge = load_yaml(CONTRACT)["orbital_gauge"]
        self.assertEqual(gauge["group"], "U(N_occ)")
        self.assertIn("occupied_subspace", gauge["invariants"])

    def test_representation_choice_is_not_measurement(self) -> None:
        prohibitions = load_yaml(CONTRACT)["orbital_gauge"]["prohibitions"]
        self.assertIn("representation_choice_is_not_measurement", prohibitions)


def add_orbital_case(seed: int) -> None:
    def test_unitarity(self: OrbitalGaugeTests) -> None:
        unitary = random_unitary(4, 3000 + seed)
        np.testing.assert_allclose(
            unitary.conj().T @ unitary,
            np.eye(4),
            atol=2e-14,
        )

    def test_density_invariance(self: OrbitalGaugeTests) -> None:
        size, occupied = 8, 4
        overlap = random_positive_definite(size, 4000 + seed)
        _, coefficients = generalized_eigh(
            random_symmetric(size, 5000 + seed),
            overlap,
        )
        c_occ = coefficients[:, :occupied]
        unitary = random_unitary(occupied, 6000 + seed)
        np.testing.assert_allclose(
            occupied_density(c_occ @ unitary),
            occupied_density(c_occ),
            atol=2e-12,
        )

    def test_electron_count(self: OrbitalGaugeTests) -> None:
        size, occupied = 8, 4
        overlap = random_positive_definite(size, 4000 + seed)
        _, coefficients = generalized_eigh(
            random_symmetric(size, 5000 + seed),
            overlap,
        )
        density = occupied_density(coefficients[:, :occupied])
        self.assertAlmostEqual(electron_count(density, overlap), occupied)

    def test_determinant_phase(self: OrbitalGaugeTests) -> None:
        unitary = random_unitary(4, 3000 + seed)
        self.assertAlmostEqual(abs(np.linalg.det(unitary)), 1.0)

    setattr(
        OrbitalGaugeTests,
        f"test_random_unitarity_seed_{seed:02d}",
        test_unitarity,
    )
    setattr(
        OrbitalGaugeTests,
        f"test_density_invariance_seed_{seed:02d}",
        test_density_invariance,
    )
    setattr(
        OrbitalGaugeTests,
        f"test_electron_count_seed_{seed:02d}",
        test_electron_count,
    )
    setattr(
        OrbitalGaugeTests,
        f"test_determinant_phase_seed_{seed:02d}",
        test_determinant_phase,
    )


for _seed in range(14):
    add_orbital_case(_seed)


class ReducedDensityTests(unittest.TestCase):
    def test_reference_one_RDM_is_positive(self) -> None:
        self.assertGreaterEqual(
            float(np.min(np.linalg.eigvalsh(paired_phase_one_rdm(0.7)))),
            0.0,
        )

    def test_reference_one_RDM_has_trace_two(self) -> None:
        self.assertAlmostEqual(
            float(np.trace(paired_phase_one_rdm(0.7))),
            2.0,
        )

    def test_reference_natural_occupations_are_one_half(self) -> None:
        np.testing.assert_allclose(
            np.linalg.eigvalsh(paired_phase_one_rdm(2.3)),
            0.5 * np.ones(4),
        )

    def test_distinct_pair_coherences(self) -> None:
        self.assertAlmostEqual(pair_coherence_expectation(0.0), 1.0)
        self.assertAlmostEqual(pair_coherence_expectation(math.pi), -1.0)

    def test_one_body_identity_expectation_is_particle_number(self) -> None:
        gamma = paired_phase_one_rdm(1.4)
        self.assertAlmostEqual(
            one_body_expectation(gamma, np.eye(4)).real,
            2.0,
        )

    def test_active_space_full_projector(self) -> None:
        gamma = paired_phase_one_rdm(0.0)
        self.assertAlmostEqual(active_occupation(gamma, np.eye(4)), 2.0)

    def test_active_space_zero_projector(self) -> None:
        gamma = paired_phase_one_rdm(0.0)
        self.assertAlmostEqual(active_occupation(gamma, np.zeros((4, 4))), 0.0)

    def test_contract_forbids_one_RDM_tomography(self) -> None:
        prohibitions = load_yaml(CONTRACT)["reduced_density_layer"][
            "prohibitions"
        ]
        self.assertIn(
            "one_RDM_does_not_determine_arbitrary_many_body_state",
            prohibitions,
        )


def add_phase_case(index: int, phase: float) -> None:
    def test_same_one_RDM(self: ReducedDensityTests) -> None:
        np.testing.assert_allclose(
            paired_phase_one_rdm(phase),
            0.5 * np.eye(4),
            atol=1e-15,
        )

    def test_pair_coherence(self: ReducedDensityTests) -> None:
        self.assertAlmostEqual(
            pair_coherence_expectation(phase),
            math.cos(phase),
        )

    def test_diagonal_one_body_observable(self: ReducedDensityTests) -> None:
        gamma = paired_phase_one_rdm(phase)
        operator = np.diag([1.0, 2.0, -1.0, 4.0])
        self.assertAlmostEqual(
            one_body_expectation(gamma, operator).real,
            3.0,
        )

    setattr(
        ReducedDensityTests,
        f"test_phase_same_one_RDM_{index:02d}",
        test_same_one_RDM,
    )
    setattr(
        ReducedDensityTests,
        f"test_phase_pair_coherence_{index:02d}",
        test_pair_coherence,
    )
    setattr(
        ReducedDensityTests,
        f"test_phase_one_body_observable_{index:02d}",
        test_diagonal_one_body_observable,
    )


for _index, _phase in enumerate(np.linspace(0.0, 2.0 * math.pi, 21)):
    add_phase_case(_index, float(_phase))


class NormalModeTests(unittest.TestCase):
    def test_nonpositive_force_constant_is_rejected(self) -> None:
        for force_constant in (0.0, -1.0):
            with self.assertRaises(ValueError):
                diatomic_cartesian_hessian(force_constant)

    def test_nonpositive_mass_is_rejected(self) -> None:
        for masses in ([1.0, 0.0], [1.0, -1.0]):
            with self.assertRaises(ValueError):
                repeated_mass_matrix(masses)

    def test_mass_matrix_shape_guard(self) -> None:
        with self.assertRaises(ValueError):
            mass_weighted_hessian(np.eye(3), np.eye(2))

    def test_mass_matrix_diagonal_guard(self) -> None:
        with self.assertRaises(ValueError):
            mass_weighted_hessian(
                np.eye(2),
                np.array([[1.0, 0.1], [0.1, 1.0]]),
            )

    def test_synthetic_negative_zero_count_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            synthetic_mass_weighted_modes([1.0], -1, 1)

    def test_negative_mode_becomes_imaginary_frequency_magnitude(self) -> None:
        positive, imaginary, zeros = harmonic_angular_frequencies(
            np.array([-9.0, 0.0, 4.0])
        )
        np.testing.assert_allclose(positive, [2.0])
        np.testing.assert_allclose(imaginary, [3.0])
        self.assertEqual(zeros, 1)

    def test_contract_types_eigenvalue_as_inverse_time_squared(self) -> None:
        modes = load_yaml(CONTRACT)["normal_modes"]
        self.assertEqual(modes["mass_weighted_Hessian"]["dimension"], "inverse_time_squared")
        self.assertEqual(modes["eigenproblem"]["relation"], "lambda_k = omega_k^2")

    def test_contract_requires_five_or_six_zero_modes(self) -> None:
        zeros = load_yaml(CONTRACT)["normal_modes"]["rigid_zero_modes"]
        self.assertEqual(zeros["isolated_linear_molecule"], 5)
        self.assertEqual(zeros["isolated_nonlinear_molecule"], 6)


MASS_CASES = [
    (1.0, 1.0, 0.5),
    (1.0, 2.0, 3.0),
    (2.0, 5.0, 7.0),
    (12.0, 1.0, 4.0),
    (16.0, 1.0, 9.0),
    (35.0, 37.0, 1.5),
    (0.5, 4.0, 11.0),
    (100.0, 2.0, 0.2),
    (3.0, 7.0, 1.3),
    (9.0, 11.0, 2.7),
    (0.25, 0.75, 5.0),
    (50.0, 80.0, 0.05),
]


def add_diatomic_case(index: int, m1: float, m2: float, k: float) -> None:
    def values() -> tuple[np.ndarray, np.ndarray, np.ndarray, int]:
        eigenvalues = normal_mode_eigenvalues(
            diatomic_cartesian_hessian(k),
            repeated_mass_matrix([m1, m2]),
        )
        positive, imaginary, zeros = harmonic_angular_frequencies(eigenvalues)
        return eigenvalues, positive, imaginary, zeros

    def test_lambda(self: NormalModeTests) -> None:
        eigenvalues, _, _, _ = values()
        expected = k * (1.0 / m1 + 1.0 / m2)
        self.assertAlmostEqual(float(eigenvalues[-1]), expected)

    def test_omega(self: NormalModeTests) -> None:
        _, positive, _, _ = values()
        expected = math.sqrt(k * (1.0 / m1 + 1.0 / m2))
        self.assertAlmostEqual(float(positive[0]), expected)

    def test_zero_count(self: NormalModeTests) -> None:
        _, _, _, zeros = values()
        self.assertEqual(zeros, 5)

    def test_no_negative_mode(self: NormalModeTests) -> None:
        _, _, imaginary, _ = values()
        self.assertEqual(imaginary.size, 0)

    setattr(NormalModeTests, f"test_diatomic_lambda_{index:02d}", test_lambda)
    setattr(NormalModeTests, f"test_diatomic_omega_{index:02d}", test_omega)
    setattr(
        NormalModeTests,
        f"test_diatomic_zero_count_{index:02d}",
        test_zero_count,
    )
    setattr(
        NormalModeTests,
        f"test_diatomic_no_negative_{index:02d}",
        test_no_negative_mode,
    )


for _index, (_m1, _m2, _k) in enumerate(MASS_CASES):
    add_diatomic_case(_index, _m1, _m2, _k)


def add_synthetic_mode_case(index: int, zeros_expected: int, modes: list[float]) -> None:
    def spectrum() -> tuple[np.ndarray, np.ndarray, np.ndarray, int]:
        matrix = synthetic_mass_weighted_modes(
            modes,
            zeros_expected,
            7000 + index,
        )
        eigenvalues = np.linalg.eigvalsh(matrix)
        positive, imaginary, zeros = harmonic_angular_frequencies(eigenvalues)
        return eigenvalues, positive, imaginary, zeros

    def test_zero_count(self: NormalModeTests) -> None:
        _, _, _, zeros = spectrum()
        self.assertEqual(zeros, zeros_expected)

    def test_negative_count(self: NormalModeTests) -> None:
        _, _, imaginary, _ = spectrum()
        self.assertEqual(imaginary.size, sum(value < 0.0 for value in modes))

    def test_positive_count(self: NormalModeTests) -> None:
        _, positive, _, _ = spectrum()
        self.assertEqual(positive.size, sum(value > 0.0 for value in modes))

    def test_nonzero_spectrum(self: NormalModeTests) -> None:
        eigenvalues, _, _, _ = spectrum()
        actual = np.sort(eigenvalues[np.abs(eigenvalues) > 1e-10])
        np.testing.assert_allclose(actual, np.sort(modes), atol=2e-12)

    setattr(
        NormalModeTests,
        f"test_synthetic_zeros_{index:02d}",
        test_zero_count,
    )
    setattr(
        NormalModeTests,
        f"test_synthetic_negative_{index:02d}",
        test_negative_count,
    )
    setattr(
        NormalModeTests,
        f"test_synthetic_positive_{index:02d}",
        test_positive_count,
    )
    setattr(
        NormalModeTests,
        f"test_synthetic_spectrum_{index:02d}",
        test_nonzero_spectrum,
    )


SYNTHETIC_CASES = [
    (6, [0.4, 1.1, 2.7]),
    (5, [0.2, 0.8, 1.7, 3.1]),
    (6, [-0.3, 0.7, 1.9]),
    (5, [-0.6, 0.5, 1.0, 2.0]),
    (6, [0.1, 0.2, 0.3, 0.4]),
    (5, [-2.0, -0.5, 0.7, 1.4]),
]

for _index, (_zeros, _modes) in enumerate(SYNTHETIC_CASES):
    add_synthetic_mode_case(_index, _zeros, _modes)


class VariationalTests(unittest.TestCase):
    def test_zero_coupling_zero_correlation(self) -> None:
        for delta in (0.0, 0.2, 2.0, 20.0):
            self.assertEqual(two_determinant_ground_energy(delta, 0.0), 0.0)

    def test_correlation_is_even_in_coupling(self) -> None:
        self.assertAlmostEqual(
            two_determinant_ground_energy(2.0, -0.7),
            two_determinant_ground_energy(2.0, 0.7),
        )

    def test_correlation_is_nonpositive(self) -> None:
        self.assertLessEqual(two_determinant_ground_energy(1.0, 0.5), 0.0)

    def test_Ritz_rejects_nonsquare_matrix(self) -> None:
        with self.assertRaises(ValueError):
            rayleigh_ritz_ground_sequence(np.ones((2, 3)), [1])

    def test_Ritz_rejects_zero_dimension(self) -> None:
        with self.assertRaises(ValueError):
            rayleigh_ritz_ground_sequence(np.eye(2), [0])

    def test_Ritz_rejects_oversized_dimension(self) -> None:
        with self.assertRaises(ValueError):
            rayleigh_ritz_ground_sequence(np.eye(2), [3])

    def test_HF_contract_is_variational(self) -> None:
        hf = load_yaml(CONTRACT)["Hartree_Fock_layer"]
        self.assertEqual(hf["variational_domain"], "normalized_Slater_determinants")
        self.assertEqual(hf["correlation_energy"]["sign"], "nonpositive")

    def test_SCF_convergence_is_not_global_minimum(self) -> None:
        self.assertIn(
            "SCF_convergence_does_not_certify_global_minimum",
            load_yaml(CONTRACT)["Hartree_Fock_layer"]["prohibitions"],
        )


CORRELATION_CASES = [
    (delta, coupling)
    for delta in (0.0, 0.1, 0.5, 2.0, 10.0)
    for coupling in (0.0, 0.05, 0.2, 0.7, 1.5)
]


def add_correlation_case(index: int, delta: float, coupling: float) -> None:
    def test_formula(self: VariationalTests) -> None:
        self.assertAlmostEqual(
            two_determinant_ground_energy(delta, coupling),
            two_determinant_exact_formula(delta, coupling),
            places=13,
        )

    def test_sign(self: VariationalTests) -> None:
        self.assertLessEqual(
            two_determinant_ground_energy(delta, coupling),
            1e-15,
        )

    setattr(
        VariationalTests,
        f"test_correlation_formula_{index:02d}",
        test_formula,
    )
    setattr(
        VariationalTests,
        f"test_correlation_sign_{index:02d}",
        test_sign,
    )


for _index, (_delta, _coupling) in enumerate(CORRELATION_CASES):
    add_correlation_case(_index, _delta, _coupling)


def add_Ritz_case(seed: int) -> None:
    def test_nested_upper_bounds(self: VariationalTests) -> None:
        matrix = random_symmetric(7, 8000 + seed)
        sequence = rayleigh_ritz_ground_sequence(matrix, range(1, 8))
        exact = float(np.linalg.eigvalsh(matrix)[0])
        self.assertTrue(np.all(sequence >= exact - 2e-13))

    def test_nested_monotonicity(self: VariationalTests) -> None:
        matrix = random_symmetric(7, 8000 + seed)
        sequence = rayleigh_ritz_ground_sequence(matrix, range(1, 8))
        self.assertTrue(np.all(np.diff(sequence) <= 2e-13))

    def test_full_space_exactness(self: VariationalTests) -> None:
        matrix = random_symmetric(7, 8000 + seed)
        sequence = rayleigh_ritz_ground_sequence(matrix, range(1, 8))
        self.assertAlmostEqual(
            float(sequence[-1]),
            float(np.linalg.eigvalsh(matrix)[0]),
            places=12,
        )

    setattr(
        VariationalTests,
        f"test_Ritz_upper_bounds_seed_{seed:02d}",
        test_nested_upper_bounds,
    )
    setattr(
        VariationalTests,
        f"test_Ritz_monotonicity_seed_{seed:02d}",
        test_nested_monotonicity,
    )
    setattr(
        VariationalTests,
        f"test_Ritz_exactness_seed_{seed:02d}",
        test_full_space_exactness,
    )


for _seed in range(10):
    add_Ritz_case(_seed)


class SpectroscopyTests(unittest.TestCase):
    def test_exact_constants(self) -> None:
        self.assertEqual(H_PLANCK, 6.62607015e-34)
        self.assertEqual(C_LIGHT, 299792458.0)
        self.assertAlmostEqual(HBAR, H_PLANCK / (2.0 * math.pi))

    def test_angular_and_cyclic_frequency_bridge(self) -> None:
        delta_energy = 3.4e-19
        omega = transition_angular_frequency(delta_energy, 0.0)
        nu = transition_cyclic_frequency(delta_energy, 0.0)
        self.assertTrue(
            math.isclose(
                omega / (2.0 * math.pi),
                nu,
                rel_tol=2e-16,
                abs_tol=0.0,
            )
        )

    def test_nonpositive_hbar_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            transition_angular_frequency(1.0, 0.0, hbar=0.0)

    def test_nonpositive_h_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            transition_cyclic_frequency(1.0, 0.0, planck=-1.0)

    def test_nonpositive_line_width_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            gaussian_line(np.linspace(-1.0, 1.0, 11), 0.0, 0.0)

    def test_bad_population_normalization_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            ideal_absorption_spectrum(
                np.linspace(-1.0, 3.0, 101),
                np.array([0.0, 1.0]),
                np.array([0.7, 0.7]),
                np.ones((2, 2)),
                0.1,
            )

    def test_negative_population_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            ideal_absorption_spectrum(
                np.linspace(-1.0, 3.0, 101),
                np.array([0.0, 1.0]),
                np.array([1.1, -0.1]),
                np.ones((2, 2)),
                0.1,
            )

    def test_spectrum_shape_guard(self) -> None:
        with self.assertRaises(ValueError):
            ideal_absorption_spectrum(
                np.linspace(-1.0, 3.0, 101),
                np.array([0.0, 1.0]),
                np.array([1.0, 0.0]),
                np.ones((3, 3)),
                0.1,
            )

    def test_nonuniform_channel_axis_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            gaussian_response_convolution(
                np.array([0.0, 1.0, 3.0]),
                np.ones(3),
                0.1,
            )

    def test_channel_shape_guard(self) -> None:
        with self.assertRaises(ValueError):
            gaussian_response_convolution(
                np.linspace(0.0, 1.0, 5),
                np.ones(4),
                0.1,
            )

    def test_contract_requires_operator_populations_and_line_profile(self) -> None:
        required = load_yaml(CONTRACT)["spectroscopy"]["ideal_spectrum"][
            "required_inputs"
        ]
        for field in (
            "initial_populations",
            "transition_operator",
            "normalized_line_profile",
        ):
            self.assertIn(field, required)

    def test_observation_channel_is_separate(self) -> None:
        channel = load_yaml(CONTRACT)["observation_channel"]
        self.assertEqual(
            channel["observed_data"],
            "Y = D_epsilon(C_inst(S_A)) + eta",
        )


def add_gaussian_case(index: int, width: float, center: float, weight: float) -> None:
    def test_area(self: SpectroscopyTests) -> None:
        axis = np.linspace(-20.0, 20.0, 120001)
        line = gaussian_line(axis, center, width, weight)
        self.assertAlmostEqual(float(np.trapezoid(line, axis)), weight, places=10)

    def test_centroid(self: SpectroscopyTests) -> None:
        axis = np.linspace(-20.0, 20.0, 120001)
        line = gaussian_line(axis, center, width, weight)
        area = float(np.trapezoid(line, axis))
        centroid = float(np.trapezoid(axis * line, axis) / area)
        self.assertAlmostEqual(centroid, center, places=10)

    setattr(SpectroscopyTests, f"test_gaussian_area_{index:02d}", test_area)
    setattr(
        SpectroscopyTests,
        f"test_gaussian_centroid_{index:02d}",
        test_centroid,
    )


for _index, (_width, _center, _weight) in enumerate(
    (
        (0.05, -3.0, 0.2),
        (0.08, 1.0, 1.0),
        (0.1, 2.2, 0.7),
        (0.2, -0.4, 2.0),
        (0.3, 4.0, 0.1),
        (0.5, 0.0, 3.0),
        (0.8, -2.5, 0.8),
        (1.0, 3.0, 1.7),
        (1.5, -1.0, 0.4),
        (2.0, 0.5, 1.1),
    )
):
    add_gaussian_case(_index, _width, _center, _weight)


class ArtifactAndContractTests(unittest.TestCase):
    def test_required_artifacts_exist(self) -> None:
        for path in (
            PDF,
            TEX,
            TEXT,
            LOG,
            CONTRACT,
            REFERENCE_LEDGER,
            CORPUS_LEDGER,
            REFERENCE_LINT,
            CORPUS_LINT,
            BENCHMARKS,
            METRICS,
        ):
            self.assertTrue(path.is_file(), path)

    def test_pdf_hash_matches_reference_ledger(self) -> None:
        document = load_yaml(REFERENCE_LEDGER)["documents"][0]
        self.assertEqual(document["source"]["sha256"], sha256(PDF))

    def test_pdf_page_count(self) -> None:
        self.assertEqual(len(PdfReader(PDF).pages), 9)

    def test_pdf_metadata(self) -> None:
        metadata = PdfReader(PDF).metadata or {}
        self.assertEqual(
            metadata.get("/Title"),
            "Quantum Chemistry as a Typed Inference Stack under Observation Maps",
        )
        self.assertEqual(
            metadata.get("/Author"),
            "Stas, Independent Research Program",
        )

    def test_contract_schema(self) -> None:
        contract = load_yaml(CONTRACT)
        self.assertEqual(
            contract["schema"]["id"],
            "go-quantum-chemistry-observation-contract",
        )
        self.assertEqual(contract["schema"]["version"], "1.0.0")

    def test_contract_gate_count(self) -> None:
        self.assertEqual(len(load_yaml(CONTRACT)["reference_gates"]), 15)

    def test_reference_expression_count(self) -> None:
        document = load_yaml(REFERENCE_LEDGER)["documents"][0]
        self.assertEqual(len(document["expressions"]), 47)

    def test_reference_lint_is_clean(self) -> None:
        summary = load_json(REFERENCE_LINT)["summary"]
        self.assertEqual(summary["findings_total"], 0)
        self.assertEqual(summary["status_counts"], {"PASS": 1})

    def test_corpus_status(self) -> None:
        summary = load_json(CORPUS_LINT)["summary"]
        self.assertEqual(summary["status_counts"], {"FAIL": 2, "PASS": 16})
        self.assertEqual(summary["findings_total"], 5)

    def test_corpus_expression_count(self) -> None:
        summary = load_json(CORPUS_LINT)["summary"]
        self.assertEqual(summary["expressions_checked"], 253)

    def test_legacy_adapter_is_superseded(self) -> None:
        corpus = load_yaml(CORPUS_LEDGER)
        ids = {item["id"] for item in corpus["documents"]}
        self.assertNotIn("quantum-chemistry-observation-v1", ids)
        self.assertIn("quantum-chemistry-observation-v1-1", ids)

    def test_only_expected_adapters_remain(self) -> None:
        corpus = load_yaml(CORPUS_LEDGER)
        failing = sorted(
            item["id"]
            for item in corpus["documents"]
            if item["ledger_level"] == "critical_adapter"
        )
        self.assertEqual(
            failing,
            ["regular-polyhedra-v1", "satellite-networks-v1-1"],
        )

    def test_benchmark_rows_all_pass(self) -> None:
        with BENCHMARKS.open("r", encoding="utf-8", newline="") as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual(len(rows), 202)
        self.assertTrue(all(row["status"] == "PASS" for row in rows))

    def test_benchmark_categories(self) -> None:
        metrics = load_json(METRICS)
        self.assertEqual(
            metrics["categories"],
            [
                "Rayleigh_Ritz",
                "active_space",
                "correlation",
                "generalized_eigenproblem",
                "normal_modes",
                "one_RDM",
                "orbital_gauge",
                "spectroscopy",
            ],
        )

    def test_benchmark_residual_bound(self) -> None:
        metrics = load_json(METRICS)
        self.assertEqual(metrics["failed_rows"], 0)
        self.assertLess(metrics["max_absolute_error"], 1e-12)

    def test_no_release_placeholders(self) -> None:
        for path in (TEX, TEXT, CONTRACT, REFERENCE_LEDGER):
            content = path.read_text(encoding="utf-8", errors="replace")
            for token in ("TODO", "TBD", "PENDING", "\ufffd"):
                self.assertNotIn(token, content)

    def test_unique_reference_heading(self) -> None:
        extracted = TEXT.read_text(encoding="utf-8", errors="replace")
        self.assertEqual(
            sum(line.strip() == "References" for line in extracted.splitlines()),
            1,
        )

    def test_latex_log_is_clean(self) -> None:
        log = LOG.read_text(encoding="utf-8", errors="replace")
        for token in (
            "Overfull",
            "Underfull",
            "LaTeX Warning",
            "undefined references",
            "Fatal error",
            "Missing character",
        ):
            self.assertNotIn(token, log)

    def test_required_source_firewalls(self) -> None:
        source = TEX.read_text(encoding="utf-8")
        for fragment in (
            r"\section{Exact molecule and Born--Oppenheimer reduction}",
            r"\section{Reduced density data and information loss}",
            r"\section{Finite bases, Hartree--Fock, and orbital gauge}",
            r"\section{Density-functional theory firewall}",
            r"\section{Nuclear geometry and the normal-mode theorem}",
            r"\section{Ideal spectra and finite-resolution data}",
            r"\lambda_k=\omega_k^2",
            r"C^\dagger SC=I",
            r"\mathcal D_\epsilon",
        ):
            self.assertIn(fragment, source)

    def test_primary_reference_identifiers(self) -> None:
        source = TEX.read_text(encoding="utf-8")
        for doi in (
            "10.1002/andp.19273892002",
            "10.1103/PhysRev.34.1293",
            "10.1103/RevModPhys.23.69",
            "10.1103/PhysRev.97.1474",
            "10.1103/RevModPhys.35.668",
            "10.1103/PhysRev.136.B864",
            "10.1103/PhysRev.140.A1133",
            "10.1073/pnas.76.12.6062",
            "10.1063/1.437734",
        ):
            self.assertIn(doi, source)

    def test_reference_lint_replay(self) -> None:
        process = subprocess.run(
            [
                "python3",
                str(ROOT / "work/go_core_v0_2/src/go_lint.py"),
                "--core-dir",
                str(ROOT / "work/go_core_v0_2/core"),
                "--ledger",
                str(REFERENCE_LEDGER),
                "--mode",
                "strict",
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertIn("expressions=47", process.stdout)
        self.assertIn("findings=0", process.stdout)


if __name__ == "__main__":
    unittest.main()
