#!/usr/bin/env python3
"""Numerical controls for the P9 quantum-chemistry reference."""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from typing import Iterable

import numpy as np


ROOT = Path(__file__).resolve().parents[3]
P9 = ROOT / "work/p9_quantum_chemistry_v1_0"
BENCHMARKS = P9 / "data/quantum_chemistry_benchmarks_v1_0.csv"
METRICS = P9 / "data/quantum_chemistry_metrics_v1_0.json"

H_PLANCK = 6.62607015e-34
HBAR = H_PLANCK / (2.0 * math.pi)
C_LIGHT = 299792458.0


def _hermitian(matrix: np.ndarray, atol: float = 1e-12) -> bool:
    return bool(np.allclose(matrix, matrix.conj().T, atol=atol, rtol=0.0))


def generalized_eigh(
    fock: np.ndarray,
    overlap: np.ndarray,
    threshold: float = 1e-12,
) -> tuple[np.ndarray, np.ndarray]:
    """Solve F C = S C eps for Hermitian F and positive-definite S."""
    fock = np.asarray(fock, dtype=complex)
    overlap = np.asarray(overlap, dtype=complex)
    if fock.shape != overlap.shape or fock.ndim != 2:
        raise ValueError("F and S must be square matrices of the same shape")
    if not _hermitian(fock) or not _hermitian(overlap):
        raise ValueError("F and S must be Hermitian")
    s_values, s_vectors = np.linalg.eigh(overlap)
    scale = float(np.max(np.abs(s_values)))
    if scale == 0.0 or np.min(s_values) <= threshold * scale:
        raise ValueError("overlap matrix is not positive definite above threshold")
    x = (s_vectors * (s_values ** -0.5)) @ s_vectors.conj().T
    transformed = x.conj().T @ fock @ x
    values, vectors_orth = np.linalg.eigh(transformed)
    coefficients = x @ vectors_orth
    return values.real, coefficients


def generalized_residual(
    fock: np.ndarray,
    overlap: np.ndarray,
    values: np.ndarray,
    coefficients: np.ndarray,
) -> float:
    residual = fock @ coefficients - overlap @ coefficients @ np.diag(values)
    return float(np.linalg.norm(residual))


def s_orthonormality_error(
    coefficients: np.ndarray,
    overlap: np.ndarray,
) -> float:
    identity = np.eye(coefficients.shape[1], dtype=complex)
    return float(
        np.linalg.norm(coefficients.conj().T @ overlap @ coefficients - identity)
    )


def random_unitary(size: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    raw = rng.normal(size=(size, size)) + 1j * rng.normal(size=(size, size))
    q, r = np.linalg.qr(raw)
    phases = np.diag(r)
    phases = np.where(np.abs(phases) > 0.0, phases / np.abs(phases), 1.0)
    return q @ np.diag(phases.conj())


def occupied_density(
    occupied_coefficients: np.ndarray,
    occupations: np.ndarray | None = None,
) -> np.ndarray:
    coefficients = np.asarray(occupied_coefficients, dtype=complex)
    if occupations is None:
        occupations = np.ones(coefficients.shape[1], dtype=float)
    occupations = np.asarray(occupations, dtype=float)
    if occupations.shape != (coefficients.shape[1],):
        raise ValueError("occupation vector has incompatible shape")
    return coefficients @ np.diag(occupations) @ coefficients.conj().T


def electron_count(density_matrix: np.ndarray, overlap: np.ndarray) -> float:
    return float(np.trace(density_matrix @ overlap).real)


def paired_phase_one_rdm(phase: float) -> np.ndarray:
    """1-RDM for (|01> + exp(i phase)|23>)/sqrt(2)."""
    _ = phase
    return 0.5 * np.eye(4)


def pair_coherence_expectation(phase: float) -> float:
    return float(math.cos(phase))


def one_body_expectation(gamma: np.ndarray, operator: np.ndarray) -> complex:
    return complex(np.trace(gamma @ operator))


def active_occupation(gamma: np.ndarray, projector: np.ndarray) -> float:
    return float(np.trace(gamma @ projector).real)


def diatomic_cartesian_hessian(force_constant: float) -> np.ndarray:
    if force_constant <= 0.0:
        raise ValueError("force constant must be positive")
    gradient = np.array([-1.0, 0.0, 0.0, 1.0, 0.0, 0.0])
    return force_constant * np.outer(gradient, gradient)


def repeated_mass_matrix(masses: Iterable[float]) -> np.ndarray:
    masses_array = np.asarray(list(masses), dtype=float)
    if np.any(masses_array <= 0.0):
        raise ValueError("all masses must be positive")
    return np.diag(np.repeat(masses_array, 3))


def mass_weighted_hessian(
    cartesian_hessian: np.ndarray,
    mass_matrix: np.ndarray,
) -> np.ndarray:
    cartesian_hessian = np.asarray(cartesian_hessian, dtype=float)
    mass_matrix = np.asarray(mass_matrix, dtype=float)
    masses = np.diag(mass_matrix)
    if (
        cartesian_hessian.shape != mass_matrix.shape
        or not np.allclose(mass_matrix, np.diag(masses))
        or np.any(masses <= 0.0)
    ):
        raise ValueError("mass matrix must be positive diagonal and shape-compatible")
    inverse_sqrt = np.diag(masses ** -0.5)
    return inverse_sqrt @ cartesian_hessian @ inverse_sqrt


def normal_mode_eigenvalues(
    cartesian_hessian: np.ndarray,
    mass_matrix: np.ndarray,
) -> np.ndarray:
    return np.linalg.eigvalsh(
        mass_weighted_hessian(cartesian_hessian, mass_matrix)
    )


def harmonic_angular_frequencies(
    eigenvalues: np.ndarray,
    zero_tolerance: float = 1e-12,
) -> tuple[np.ndarray, np.ndarray, int]:
    values = np.asarray(eigenvalues, dtype=float)
    scale = max(float(np.max(np.abs(values))), 1.0)
    threshold = zero_tolerance * scale
    positive = values[values > threshold]
    negative = values[values < -threshold]
    zeros = int(values.size - positive.size - negative.size)
    return np.sqrt(positive), np.sqrt(-negative), zeros


def synthetic_mass_weighted_modes(
    vibrational_eigenvalues: Iterable[float],
    rigid_zero_modes: int,
    seed: int,
) -> np.ndarray:
    modes = np.asarray(list(vibrational_eigenvalues), dtype=float)
    if rigid_zero_modes < 0:
        raise ValueError("rigid zero-mode count must be nonnegative")
    diagonal = np.concatenate([np.zeros(rigid_zero_modes), modes])
    rng = np.random.default_rng(seed)
    raw = rng.normal(size=(diagonal.size, diagonal.size))
    q, _ = np.linalg.qr(raw)
    return q @ np.diag(diagonal) @ q.T


def two_determinant_ground_energy(delta: float, coupling: float) -> float:
    matrix = np.array([[0.0, coupling], [coupling, delta]], dtype=float)
    return float(np.linalg.eigvalsh(matrix)[0])


def two_determinant_exact_formula(delta: float, coupling: float) -> float:
    return 0.5 * (delta - math.sqrt(delta * delta + 4.0 * coupling * coupling))


def rayleigh_ritz_ground_sequence(
    matrix: np.ndarray,
    dimensions: Iterable[int],
) -> np.ndarray:
    matrix = np.asarray(matrix, dtype=float)
    if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1]:
        raise ValueError("matrix must be square")
    values: list[float] = []
    for dimension in dimensions:
        if dimension < 1 or dimension > matrix.shape[0]:
            raise ValueError("invalid Ritz dimension")
        values.append(float(np.linalg.eigvalsh(matrix[:dimension, :dimension])[0]))
    return np.asarray(values)


def transition_angular_frequency(
    final_energy: float,
    initial_energy: float,
    hbar: float = HBAR,
) -> float:
    if hbar <= 0.0:
        raise ValueError("hbar must be positive")
    return (final_energy - initial_energy) / hbar


def transition_cyclic_frequency(
    final_energy: float,
    initial_energy: float,
    planck: float = H_PLANCK,
) -> float:
    if planck <= 0.0:
        raise ValueError("Planck constant must be positive")
    return (final_energy - initial_energy) / planck


def gaussian_line(
    axis: np.ndarray,
    center: float,
    width: float,
    weight: float = 1.0,
) -> np.ndarray:
    if width <= 0.0:
        raise ValueError("Gaussian width must be positive")
    axis = np.asarray(axis, dtype=float)
    normalized = np.exp(-0.5 * ((axis - center) / width) ** 2)
    normalized /= width * math.sqrt(2.0 * math.pi)
    return weight * normalized


def ideal_absorption_spectrum(
    axis: np.ndarray,
    energies: np.ndarray,
    populations: np.ndarray,
    transition_operator: np.ndarray,
    width: float,
    hbar: float = 1.0,
) -> np.ndarray:
    energies = np.asarray(energies, dtype=float)
    populations = np.asarray(populations, dtype=float)
    operator = np.asarray(transition_operator, dtype=complex)
    if (
        energies.ndim != 1
        or populations.shape != energies.shape
        or operator.shape != (energies.size, energies.size)
    ):
        raise ValueError("incompatible spectrum inputs")
    if np.any(populations < 0.0) or not np.isclose(populations.sum(), 1.0):
        raise ValueError("populations must be nonnegative and normalized")
    spectrum = np.zeros_like(np.asarray(axis, dtype=float))
    for initial in range(energies.size):
        for final in range(energies.size):
            if energies[final] <= energies[initial]:
                continue
            weight = (
                populations[initial]
                * abs(operator[final, initial]) ** 2
            )
            center = (energies[final] - energies[initial]) / hbar
            spectrum += gaussian_line(axis, center, width, float(weight))
    return spectrum


def gaussian_response_convolution(
    axis: np.ndarray,
    signal: np.ndarray,
    response_width: float,
) -> np.ndarray:
    axis = np.asarray(axis, dtype=float)
    signal = np.asarray(signal, dtype=float)
    if axis.ndim != 1 or signal.shape != axis.shape or axis.size < 3:
        raise ValueError("axis and signal must be compatible one-dimensional arrays")
    spacing = float(axis[1] - axis[0])
    if spacing <= 0.0 or not np.allclose(np.diff(axis), spacing):
        raise ValueError("axis must be uniformly increasing")
    offsets = (np.arange(axis.size) - axis.size // 2) * spacing
    kernel = gaussian_line(offsets, 0.0, response_width)
    kernel /= np.sum(kernel) * spacing
    return np.convolve(signal, kernel, mode="same") * spacing


def _random_positive_definite(size: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    raw = rng.normal(size=(size, size))
    return raw.T @ raw + (0.8 + 0.1 * size) * np.eye(size)


def _random_symmetric(size: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    raw = rng.normal(size=(size, size))
    return 0.5 * (raw + raw.T)


def build_benchmarks() -> tuple[list[dict[str, object]], dict[str, object]]:
    rows: list[dict[str, object]] = []
    errors: list[float] = []

    def add(
        category: str,
        case: str,
        quantity: str,
        expected: float,
        computed: float,
        tolerance: float,
    ) -> None:
        error = abs(float(computed) - float(expected))
        errors.append(error)
        rows.append(
            {
                "category": category,
                "case": case,
                "quantity": quantity,
                "expected": f"{float(expected):.17g}",
                "computed": f"{float(computed):.17g}",
                "abs_error": f"{error:.6e}",
                "tolerance": f"{float(tolerance):.6e}",
                "status": "PASS" if error <= tolerance else "FAIL",
            }
        )

    for seed in range(8):
        size = 3 + seed % 3
        overlap = _random_positive_definite(size, 100 + seed)
        fock = _random_symmetric(size, 200 + seed)
        values, coefficients = generalized_eigh(fock, overlap)
        residual = generalized_residual(fock, overlap, values, coefficients)
        orth_error = s_orthonormality_error(coefficients, overlap)
        transformed = np.linalg.solve(overlap, fock)
        direct = np.sort(np.linalg.eigvals(transformed).real)
        add("generalized_eigenproblem", f"seed_{seed}", "residual", 0.0, residual, 5e-12)
        add("generalized_eigenproblem", f"seed_{seed}", "S_orthonormality", 0.0, orth_error, 5e-12)
        add(
            "generalized_eigenproblem",
            f"seed_{seed}",
            "eigenvalue_match",
            0.0,
            float(np.max(np.abs(values - direct))),
            5e-12,
        )

    for seed in range(12):
        size = 7
        occupied = 3
        overlap = _random_positive_definite(size, 300 + seed)
        _, coefficients = generalized_eigh(
            _random_symmetric(size, 400 + seed),
            overlap,
        )
        c_occ = coefficients[:, :occupied]
        unitary = random_unitary(occupied, 500 + seed)
        density = occupied_density(c_occ)
        rotated_density = occupied_density(c_occ @ unitary)
        add(
            "orbital_gauge",
            f"seed_{seed}",
            "density_invariance",
            0.0,
            float(np.linalg.norm(rotated_density - density)),
            5e-12,
        )
        add(
            "orbital_gauge",
            f"seed_{seed}",
            "electron_count",
            float(occupied),
            electron_count(density, overlap),
            5e-12,
        )
        add(
            "orbital_gauge",
            f"seed_{seed}",
            "determinant_modulus",
            1.0,
            abs(np.linalg.det(unitary)),
            5e-12,
        )

    phases = np.linspace(0.0, 2.0 * math.pi, 13)
    for index, phase in enumerate(phases):
        gamma = paired_phase_one_rdm(float(phase))
        occupations = np.linalg.eigvalsh(gamma)
        add("one_RDM", f"phase_{index}", "trace", 2.0, float(np.trace(gamma)), 1e-14)
        add(
            "one_RDM",
            f"phase_{index}",
            "occupation_spread",
            0.0,
            float(np.max(occupations) - np.min(occupations)),
            1e-14,
        )
        add(
            "one_RDM",
            f"phase_{index}",
            "pair_coherence",
            math.cos(float(phase)),
            pair_coherence_expectation(float(phase)),
            1e-14,
        )

    mass_cases = [
        (1.0, 1.0, 0.5),
        (1.0, 2.0, 3.0),
        (2.0, 5.0, 7.0),
        (12.0, 1.0, 4.0),
        (16.0, 1.0, 9.0),
        (35.0, 37.0, 1.5),
        (0.5, 4.0, 11.0),
        (100.0, 2.0, 0.2),
    ]
    for index, (m1, m2, force_constant) in enumerate(mass_cases):
        hessian = diatomic_cartesian_hessian(force_constant)
        masses = repeated_mass_matrix([m1, m2])
        eigenvalues = normal_mode_eigenvalues(hessian, masses)
        frequencies, imaginary, zeros = harmonic_angular_frequencies(eigenvalues)
        expected_lambda = force_constant * (1.0 / m1 + 1.0 / m2)
        add(
            "normal_modes",
            f"diatomic_{index}",
            "positive_lambda",
            expected_lambda,
            float(eigenvalues[-1]),
            2e-12 * max(1.0, expected_lambda),
        )
        add(
            "normal_modes",
            f"diatomic_{index}",
            "angular_frequency",
            math.sqrt(expected_lambda),
            float(frequencies[0]),
            2e-12 * max(1.0, math.sqrt(expected_lambda)),
        )
        add("normal_modes", f"diatomic_{index}", "rigid_zero_count", 5.0, float(zeros), 0.0)
        add("normal_modes", f"diatomic_{index}", "imaginary_count", 0.0, float(imaginary.size), 0.0)

    synthetic_cases = [
        ("nonlinear_minimum", 6, [0.4, 1.1, 2.7], 0),
        ("linear_minimum", 5, [0.2, 0.8, 1.7, 3.1], 0),
        ("nonlinear_TS", 6, [-0.3, 0.7, 1.9], 1),
        ("linear_TS", 5, [-0.6, 0.5, 1.0, 2.0], 1),
    ]
    for index, (name, zeros_expected, modes, negative_expected) in enumerate(synthetic_cases):
        k_matrix = synthetic_mass_weighted_modes(modes, zeros_expected, 600 + index)
        eigenvalues = np.linalg.eigvalsh(k_matrix)
        positive, imaginary, zeros = harmonic_angular_frequencies(eigenvalues)
        add("normal_modes", name, "zero_count", float(zeros_expected), float(zeros), 0.0)
        add("normal_modes", name, "negative_count", float(negative_expected), float(imaginary.size), 0.0)
        add(
            "normal_modes",
            name,
            "nonzero_spectral_match",
            0.0,
            float(
                np.max(
                    np.abs(
                        np.sort(eigenvalues[np.abs(eigenvalues) > 1e-10])
                        - np.sort(np.asarray(modes, dtype=float))
                    )
                )
            ),
            5e-12,
        )
        add(
            "normal_modes",
            name,
            "positive_frequency_count",
            float(sum(value > 0.0 for value in modes)),
            float(positive.size),
            0.0,
        )

    correlation_cases = [
        (delta, coupling)
        for delta in (0.0, 0.5, 2.0, 10.0)
        for coupling in (0.0, 0.2, 1.0)
    ]
    for index, (delta, coupling) in enumerate(correlation_cases):
        exact = two_determinant_exact_formula(delta, coupling)
        numeric = two_determinant_ground_energy(delta, coupling)
        add("correlation", f"case_{index}", "formula_match", exact, numeric, 2e-14)
        add(
            "correlation",
            f"case_{index}",
            "nonpositive_ground",
            0.0,
            max(numeric, 0.0),
            1e-14,
        )

    hamiltonian = np.array(
        [
            [4.0, 1.0, 0.8, 0.2, -0.1, 0.3],
            [1.0, 3.0, 0.7, -0.4, 0.2, 0.0],
            [0.8, 0.7, 2.5, 0.9, 0.1, -0.2],
            [0.2, -0.4, 0.9, 1.8, 0.6, 0.4],
            [-0.1, 0.2, 0.1, 0.6, 1.2, 0.7],
            [0.3, 0.0, -0.2, 0.4, 0.7, 0.5],
        ]
    )
    ritz = rayleigh_ritz_ground_sequence(hamiltonian, range(1, 7))
    exact_ground = float(np.linalg.eigvalsh(hamiltonian)[0])
    for index, value in enumerate(ritz):
        add(
            "Rayleigh_Ritz",
            f"dimension_{index + 1}",
            "upper_bound_violation",
            0.0,
            max(exact_ground - float(value), 0.0),
            1e-13,
        )
        if index:
            add(
                "Rayleigh_Ritz",
                f"dimension_{index + 1}",
                "monotonicity_violation",
                0.0,
                max(float(value - ritz[index - 1]), 0.0),
                1e-13,
            )
    add(
        "Rayleigh_Ritz",
        "full_dimension",
        "exact_match",
        exact_ground,
        float(ritz[-1]),
        1e-13,
    )

    axis = np.linspace(-20.0, 20.0, 200001)
    for index, width in enumerate((0.05, 0.1, 0.2, 0.5, 1.0, 2.0)):
        weight = 0.25 + 0.3 * index
        line = gaussian_line(axis, 1.3, width, weight)
        area = float(np.trapezoid(line, axis))
        centroid = float(np.trapezoid(axis * line, axis) / area)
        add("spectroscopy", f"gaussian_{index}", "line_area", weight, area, 2e-12)
        add("spectroscopy", f"gaussian_{index}", "centroid", 1.3, centroid, 2e-12)

    spectrum_axis = np.linspace(-1.0, 6.0, 70001)
    energies = np.array([0.0, 2.0, 5.0])
    populations = np.array([0.8, 0.2, 0.0])
    transition = np.array(
        [
            [0.0, 1.0, 0.5],
            [1.0, 0.0, 2.0],
            [0.5, 2.0, 0.0],
        ],
        dtype=complex,
    )
    spectrum = ideal_absorption_spectrum(
        spectrum_axis,
        energies,
        populations,
        transition,
        width=0.03,
        hbar=1.0,
    )
    expected_area = (
        0.8 * abs(transition[1, 0]) ** 2
        + 0.8 * abs(transition[2, 0]) ** 2
        + 0.2 * abs(transition[2, 1]) ** 2
    )
    spectrum_area = float(np.trapezoid(spectrum, spectrum_axis))
    convolved = gaussian_response_convolution(
        spectrum_axis,
        spectrum,
        response_width=0.08,
    )
    convolved_area = float(np.trapezoid(convolved, spectrum_axis))
    add("spectroscopy", "three_level", "ideal_area", expected_area, spectrum_area, 3e-10)
    add("spectroscopy", "three_level", "channel_area", expected_area, convolved_area, 3e-8)
    add(
        "spectroscopy",
        "Planck_bridge",
        "omega_over_2pi_equals_nu",
        transition_cyclic_frequency(2e-19, 0.0),
        transition_angular_frequency(2e-19, 0.0) / (2.0 * math.pi),
        1e-12 * transition_cyclic_frequency(2e-19, 0.0),
    )

    gamma = np.diag([0.9, 0.7, 0.3, 0.1])
    projectors = [
        np.diag([1.0, 1.0, 0.0, 0.0]),
        np.diag([0.0, 1.0, 1.0, 0.0]),
        np.diag([0.0, 0.0, 1.0, 1.0]),
        np.eye(4),
    ]
    expected_active = [1.6, 1.0, 0.4, 2.0]
    for index, (projector, expected) in enumerate(zip(projectors, expected_active, strict=True)):
        add(
            "active_space",
            f"projector_{index}",
            "occupation",
            expected,
            active_occupation(gamma, projector),
            1e-14,
        )

    failures = [row for row in rows if row["status"] != "PASS"]
    metrics = {
        "schema": {
            "id": "go-p9-quantum-chemistry-metrics",
            "version": "1.0.0",
        },
        "date": "2026-07-28",
        "benchmark_rows": len(rows),
        "failed_rows": len(failures),
        "max_absolute_error": max(errors, default=0.0),
        "categories": sorted({str(row["category"]) for row in rows}),
        "constants": {
            "h_exact_J_s": H_PLANCK,
            "hbar_J_s": HBAR,
            "c_exact_m_s": C_LIGHT,
        },
        "controls": {
            "generalized_eigenproblem_seeds": 8,
            "orbital_gauge_seeds": 12,
            "one_RDM_phase_samples": len(phases),
            "diatomic_mass_cases": len(mass_cases),
            "correlation_cases": len(correlation_cases),
        },
    }
    return rows, metrics


def main() -> None:
    rows, metrics = build_benchmarks()
    BENCHMARKS.parent.mkdir(parents=True, exist_ok=True)
    with BENCHMARKS.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=[
                "category",
                "case",
                "quantity",
                "expected",
                "computed",
                "abs_error",
                "tolerance",
                "status",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)
    METRICS.write_text(
        json.dumps(metrics, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )
    if metrics["failed_rows"]:
        raise SystemExit(f"{metrics['failed_rows']} benchmark rows failed")
    print(BENCHMARKS)
    print(METRICS)


if __name__ == "__main__":
    main()
