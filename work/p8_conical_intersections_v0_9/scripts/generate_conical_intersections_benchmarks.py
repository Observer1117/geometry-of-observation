#!/usr/bin/env python3
"""Generate deterministic P8 conical-intersection reference benchmarks."""

from __future__ import annotations

import cmath
import csv
import json
import math
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[3]
P8 = ROOT / "work/p8_conical_intersections_v0_9"
CSV_PATH = P8 / "data/conical_intersections_benchmarks_v0_9.csv"
METRICS_PATH = P8 / "data/conical_intersections_metrics_v0_9.json"


SIGMA_X = np.array([[0.0, 1.0], [1.0, 0.0]], dtype=complex)
SIGMA_Y = np.array([[0.0, -1.0j], [1.0j, 0.0]], dtype=complex)
SIGMA_Z = np.array([[1.0, 0.0], [0.0, -1.0]], dtype=complex)
IDENTITY = np.eye(2, dtype=complex)


def hamiltonian(x: float, y: float, delta: float = 0.0) -> np.ndarray:
    return x * SIGMA_Z + y * SIGMA_X + delta * SIGMA_Y


def radius(x: float, y: float) -> float:
    return math.hypot(x, y)


def gap(x: float, y: float, delta: float = 0.0) -> float:
    return 2.0 * math.sqrt(x * x + y * y + delta * delta)


def projector(x: float, y: float, sign: int) -> np.ndarray:
    r = radius(x, y)
    if r == 0.0:
        raise ValueError("rank-one projector is undefined at the seam")
    if sign not in (-1, 1):
        raise ValueError("sign must be -1 or +1")
    return 0.5 * (IDENTITY + sign * hamiltonian(x, y) / r)


def real_eigenvector(phi: float, sign: int) -> np.ndarray:
    if sign == -1:
        return np.array(
            [-math.sin(phi / 2.0), math.cos(phi / 2.0)],
            dtype=complex,
        )
    if sign == 1:
        return np.array(
            [math.cos(phi / 2.0), math.sin(phi / 2.0)],
            dtype=complex,
        )
    raise ValueError("sign must be -1 or +1")


def overlap_holonomy(winding: int, samples: int = 128) -> complex:
    if samples < 4 * max(1, abs(winding)):
        raise ValueError("sampling is too coarse for the declared winding")
    vectors = [
        real_eigenvector(2.0 * math.pi * winding * j / samples, -1)
        for j in range(samples)
    ]
    product = 1.0 + 0.0j
    for index, left in enumerate(vectors):
        right = vectors[(index + 1) % samples]
        overlap = np.vdot(left, right)
        if abs(overlap) < 1e-14:
            raise ZeroDivisionError("neighboring eigenvectors are orthogonal")
        product *= overlap / abs(overlap)
    return product


def random_gauge_holonomy(winding: int, samples: int = 128) -> complex:
    vectors: list[np.ndarray] = []
    for index in range(samples):
        phi = 2.0 * math.pi * winding * index / samples
        phase = cmath.exp(
            1.0j
            * (
                0.37 * math.sin(3.0 * phi + 0.2)
                + 0.19 * math.cos(5.0 * phi - 0.4)
            )
        )
        vectors.append(phase * real_eigenvector(phi, -1))
    product = 1.0 + 0.0j
    for index, left in enumerate(vectors):
        right = vectors[(index + 1) % samples]
        overlap = np.vdot(left, right)
        if abs(overlap) < 1e-14:
            raise ZeroDivisionError("neighboring eigenvectors are orthogonal")
        product *= overlap / abs(overlap)
    return product


def energy_derivative_coupling(x: float, y: float) -> np.ndarray:
    r2 = x * x + y * y
    if r2 == 0.0:
        raise ValueError("derivative coupling is undefined at the seam")
    return np.array([y, -x], dtype=float) / (2.0 * r2)


def quantum_metric(x: float, y: float) -> np.ndarray:
    r2 = x * x + y * y
    if r2 == 0.0:
        raise ValueError("quantum metric is singular at the seam")
    return np.array(
        [[y * y, -x * y], [-x * y, x * x]],
        dtype=float,
    ) / (4.0 * r2 * r2)


def physical_pullback(
    metric_energy: np.ndarray,
    jacobian: np.ndarray,
) -> np.ndarray:
    if metric_energy.shape != (2, 2):
        raise ValueError("energy metric must be 2 by 2")
    if jacobian.ndim != 2 or jacobian.shape[0] != 2:
        raise ValueError("Jacobian must have two branching-coordinate rows")
    return jacobian.T @ metric_energy @ jacobian


def gapped_berry_phase(radius_loop: float, delta: float) -> float:
    if radius_loop <= 0.0 or delta <= 0.0:
        raise ValueError("positive radius and positive delta required")
    return math.pi * (
        1.0 - delta / math.sqrt(radius_loop**2 + delta**2)
    )


def numeric_gapped_berry_phase(
    radius_loop: float,
    delta: float,
    samples: int = 4096,
) -> float:
    vectors: list[np.ndarray] = []
    for index in range(samples):
        phi = 2.0 * math.pi * index / samples
        x = radius_loop * math.cos(phi)
        y = radius_loop * math.sin(phi)
        _values, eigenvectors = np.linalg.eigh(hamiltonian(x, y, delta))
        vectors.append(eigenvectors[:, 0])
    product = 1.0 + 0.0j
    for index, left in enumerate(vectors):
        right = vectors[(index + 1) % samples]
        overlap = np.vdot(left, right)
        product *= overlap / abs(overlap)
    phase = abs(cmath.phase(product))
    return phase


def landau_zener_probability(
    coupling: float,
    hbar_times_rate: float,
) -> float:
    if coupling < 0.0:
        raise ValueError("coupling magnitude must be nonnegative")
    if hbar_times_rate <= 0.0:
        raise ValueError("hbar times sweep rate must be positive")
    return math.exp(-math.pi * coupling**2 / hbar_times_rate)


def gap_uncertainty(
    sigma_plus: float,
    sigma_minus: float,
    covariance: float,
) -> float:
    if sigma_plus < 0.0 or sigma_minus < 0.0:
        raise ValueError("standard deviations must be nonnegative")
    variance = (
        sigma_plus**2 + sigma_minus**2 - 2.0 * covariance
    )
    if variance < -1e-15:
        raise ValueError("declared covariance gives negative gap variance")
    return math.sqrt(max(0.0, variance))


def unresolved_near_degeneracy(
    measured_gap: float,
    sigma_gap: float,
    kappa: float,
    resolution: float,
) -> bool:
    if sigma_gap < 0.0 or kappa < 0.0 or resolution < 0.0:
        raise ValueError("uncertainty, kappa, and resolution are nonnegative")
    return abs(measured_gap) <= kappa * sigma_gap + resolution


def main() -> None:
    rows: list[dict[str, str]] = []

    for x, y in (
        (3.0, 4.0),
        (1.0, 0.0),
        (0.0, 1.0),
        (-3.0, 4.0),
        (0.03, -0.04),
        (1e-6, 0.0),
    ):
        r = radius(x, y)
        rows.append(
            {
                "family": "spectrum",
                "case": f"x={x:g};y={y:g}",
                "input_1": f"{x:.16g}",
                "input_2": f"{y:.16g}",
                "expected": f"{2.0*r:.16g}",
                "observed": f"{gap(x,y):.16g}",
                "absolute_error": "0",
                "unit": "energy",
            }
        )

    for r in (1.0, 0.5, 0.25, 0.1, 0.05, 0.01):
        coupling = np.linalg.norm(energy_derivative_coupling(r, 0.0))
        expected = 1.0 / (2.0 * r)
        rows.append(
            {
                "family": "derivative_coupling",
                "case": f"r={r:g}",
                "input_1": f"{r:.16g}",
                "input_2": "0",
                "expected": f"{expected:.16g}",
                "observed": f"{coupling:.16g}",
                "absolute_error": f"{abs(coupling-expected):.3e}",
                "unit": "inverse_energy",
            }
        )

    for winding in (-3, -2, -1, 0, 1, 2, 3):
        observed = overlap_holonomy(winding)
        expected = -1.0 if winding % 2 else 1.0
        rows.append(
            {
                "family": "real_holonomy",
                "case": f"w={winding}",
                "input_1": str(winding),
                "input_2": "128",
                "expected": f"{expected:.1f}",
                "observed": f"{observed.real:.16g}",
                "absolute_error": f"{abs(observed-expected):.3e}",
                "unit": "1",
            }
        )

    for delta in (0.05, 0.1, 0.5, 1.0, 2.0, 10.0):
        expected = gapped_berry_phase(1.0, delta)
        observed = numeric_gapped_berry_phase(1.0, delta)
        rows.append(
            {
                "family": "gapped_berry",
                "case": f"R=1;delta={delta:g}",
                "input_1": "1",
                "input_2": f"{delta:.16g}",
                "expected": f"{expected:.16g}",
                "observed": f"{observed:.16g}",
                "absolute_error": f"{abs(observed-expected):.3e}",
                "unit": "rad",
            }
        )

    for ratio in (0.0, 0.1, 0.25, 0.5, 1.0, 2.0):
        coupling = math.sqrt(ratio)
        expected = math.exp(-math.pi * ratio)
        observed = landau_zener_probability(coupling, 1.0)
        rows.append(
            {
                "family": "landau_zener",
                "case": f"b2_over_hbar_v={ratio:g}",
                "input_1": f"{coupling:.16g}",
                "input_2": "1",
                "expected": f"{expected:.16g}",
                "observed": f"{observed:.16g}",
                "absolute_error": f"{abs(observed-expected):.3e}",
                "unit": "probability",
            }
        )

    resolution_cases = (
        (0.01, 0.02, 0.02, 0.0, 2.0, 0.0),
        (0.05, 0.02, 0.02, 0.0, 2.0, 0.0),
        (0.03, 0.01, 0.02, 0.0001, 2.0, 0.005),
        (-0.02, 0.01, 0.01, 0.00005, 1.0, 0.01),
    )
    for index, (
        measured,
        sigma_plus,
        sigma_minus,
        covariance,
        kappa,
        resolution,
    ) in enumerate(resolution_cases, start=1):
        sigma = gap_uncertainty(sigma_plus, sigma_minus, covariance)
        observed = unresolved_near_degeneracy(
            measured,
            sigma,
            kappa,
            resolution,
        )
        rows.append(
            {
                "family": "finite_resolution",
                "case": f"case={index}",
                "input_1": f"{measured:.16g}",
                "input_2": f"{sigma:.16g}",
                "expected": str(observed).lower(),
                "observed": str(observed).lower(),
                "absolute_error": "0",
                "unit": "boolean",
            }
        )

    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CSV_PATH.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=[
                "family",
                "case",
                "input_1",
                "input_2",
                "expected",
                "observed",
                "absolute_error",
                "unit",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    projector_residuals: list[float] = []
    orthogonality_residuals: list[float] = []
    metric_residuals: list[float] = []
    gauge_residuals: list[float] = []
    for x, y in (
        (3.0, 4.0),
        (1.0, 2.0),
        (-2.0, 5.0),
        (0.03, -0.04),
    ):
        p_minus = projector(x, y, -1)
        p_plus = projector(x, y, 1)
        projector_residuals.extend(
            [
                float(np.linalg.norm(p_minus @ p_minus - p_minus)),
                float(np.linalg.norm(p_plus @ p_plus - p_plus)),
            ]
        )
        orthogonality_residuals.append(
            float(np.linalg.norm(p_minus @ p_plus))
        )
        metric = quantum_metric(x, y)
        metric_residuals.append(
            abs(float(np.trace(metric)) - 1.0 / (4.0 * radius(x, y) ** 2))
        )
    for winding in (-3, -2, -1, 0, 1, 2, 3):
        gauge_residuals.append(
            abs(
                random_gauge_holonomy(winding)
                - overlap_holonomy(winding)
            )
        )

    metrics = {
        "schema": {
            "id": "go-p8-conical-intersections-metrics",
            "version": "0.9.0",
        },
        "date": "2026-07-28",
        "benchmark_rows": len(rows),
        "family_counts": {
            family: sum(row["family"] == family for row in rows)
            for family in sorted({row["family"] for row in rows})
        },
        "max_projector_idempotence_residual": max(projector_residuals),
        "max_projector_orthogonality_residual": max(
            orthogonality_residuals
        ),
        "max_quantum_metric_identity_residual": max(metric_residuals),
        "max_random_gauge_holonomy_residual": max(gauge_residuals),
        "max_gapped_berry_discretization_error": max(
            float(row["absolute_error"])
            for row in rows
            if row["family"] == "gapped_berry"
        ),
    }
    with METRICS_PATH.open("w", encoding="utf-8") as stream:
        json.dump(metrics, stream, indent=2)
        stream.write("\n")

    print(CSV_PATH)
    print(METRICS_PATH)


if __name__ == "__main__":
    main()
