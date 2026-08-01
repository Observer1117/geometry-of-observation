#!/usr/bin/env python3
"""Regression tests for the GO distance-scale and Mandelbrot P2 migration."""

from __future__ import annotations

import itertools
import json
import math
import subprocess
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[3]
P2 = ROOT / "work/p2_distance_scale_v0_3"
CONTRACT = P2 / "core/distance_scale_contract_v0_3.yaml"
LEDGER = P2 / "ledgers/distance_scale_mandelbrot_reference_ledgers_v0_3.yaml"
LINT_JSON = P2 / "reports/Distance_Scale_Mandelbrot_Lint_Report_v0_3.json"


def observed_distance(point_a: tuple[float, ...], point_b: tuple[float, ...]) -> float:
    """Orthogonal R^3 -> R^2 observed distance."""
    return math.hypot(point_a[0] - point_b[0], point_a[1] - point_b[1])


def exact_covering_number(points: tuple[float, ...], epsilon: float) -> int:
    """Internal closed-ball covering number for a finite subset of R."""
    if epsilon <= 0:
        raise ValueError("epsilon must be positive")
    size = len(points)
    for count in range(1, size + 1):
        for centers in itertools.combinations(points, count):
            if all(min(abs(point - center) for center in centers) <= epsilon for point in points):
                return count
    return size


def weighted_slope(
    x_values: list[float], y_values: list[float], weights: list[float]
) -> tuple[float, float, list[float]]:
    total_weight = sum(weights)
    x_bar = sum(w * x for w, x in zip(weights, x_values, strict=True)) / total_weight
    y_bar = sum(w * y for w, y in zip(weights, y_values, strict=True)) / total_weight
    denominator = sum(
        w * (x - x_bar) ** 2 for w, x in zip(weights, x_values, strict=True)
    )
    if denominator <= 0:
        raise ValueError("at least two distinct scales are required")
    slope = sum(
        w * (x - x_bar) * (y - y_bar)
        for w, x, y in zip(weights, x_values, y_values, strict=True)
    ) / denominator
    intercept = y_bar - slope * x_bar
    residuals = [
        y - intercept - slope * x
        for x, y in zip(x_values, y_values, strict=True)
    ]
    return slope, intercept, residuals


def pairwise_slope_interval(
    x_values: list[float], y_values: list[float]
) -> tuple[float, float]:
    slopes = [
        (y_values[j] - y_values[i]) / (x_values[j] - x_values[i])
        for i in range(len(x_values))
        for j in range(i + 1, len(x_values))
        if x_values[j] != x_values[i]
    ]
    if not slopes:
        raise ValueError("no distinct scale pair")
    return min(slopes), max(slopes)


class DistanceInterfaceTests(unittest.TestCase):
    def test_observed_distance_is_symmetric_and_nonnegative(self) -> None:
        a = (1.0, -2.0, 7.0)
        b = (-3.0, 4.0, -9.0)
        self.assertGreaterEqual(observed_distance(a, b), 0.0)
        self.assertAlmostEqual(observed_distance(a, b), observed_distance(b, a))

    def test_observed_distance_triangle_inequality(self) -> None:
        a = (0.0, 0.0, 100.0)
        b = (1.0, 1.0, -20.0)
        c = (3.0, -2.0, 0.0)
        self.assertLessEqual(
            observed_distance(a, c),
            observed_distance(a, b) + observed_distance(b, c) + 1e-12,
        )

    def test_projection_is_nonseparating_on_fibers(self) -> None:
        self.assertEqual(
            observed_distance((2.0, 3.0, -10.0), (2.0, 3.0, 50.0)),
            0.0,
        )

    def test_quotient_distance_matches_image_distance(self) -> None:
        a = (1.0, 2.0, -100.0)
        b = (4.0, 6.0, 200.0)
        self.assertAlmostEqual(observed_distance(a, b), 5.0)

    def test_projected_shell_is_cylinder(self) -> None:
        center = (2.0, -1.0, 0.0)
        radius = 3.5
        for z_value in (-100.0, 0.0, 17.0):
            point = (center[0] + radius, center[1], z_value)
            self.assertAlmostEqual(observed_distance(center, point), radius)

    def test_hidden_distance_profile(self) -> None:
        radius = 2.0
        delta_z = 5.0
        hidden = math.sqrt(radius**2 + delta_z**2)
        self.assertAlmostEqual(hidden**2, radius**2 + delta_z**2)
        self.assertGreaterEqual(hidden, radius)

    def test_shell_unit_covariance(self) -> None:
        distance = 1.03
        radius = 1.00
        tolerance = 0.04
        original = abs(distance - radius) <= tolerance
        scale = 100.0
        converted = abs(scale * distance - scale * radius) <= scale * tolerance
        self.assertEqual(original, converted)

    def test_deterministic_error_envelope(self) -> None:
        true_distance = 7.0
        radius = 7.0
        error_bound = 0.2
        tolerance = 0.2
        estimates = (6.8, 7.0, 7.2)
        self.assertTrue(all(abs(value - radius) <= tolerance + 1e-12 for value in estimates))
        accepted = 7.15
        self.assertLessEqual(
            abs(true_distance - radius),
            abs(true_distance - accepted) + abs(accepted - radius),
        )
        self.assertLessEqual(abs(true_distance - radius), error_bound + tolerance)

    def test_lipschitz_resolution_composition(self) -> None:
        epsilon_x = 0.3
        first = 2.5
        second = 4.0
        epsilon_y = first * epsilon_x
        epsilon_z = second * epsilon_y
        self.assertAlmostEqual(epsilon_z, second * first * epsilon_x)

    def test_rational_step_factors_through_mod_q(self) -> None:
        p, q = 2, 5
        phase = 0.37
        readout = lambda n: math.cos(2.0 * math.pi * p * n / q + phase)
        for n in range(-20, 21):
            self.assertAlmostEqual(readout(n), readout(n + q), places=12)

    def test_half_step_is_parity(self) -> None:
        for n in range(-12, 13):
            self.assertAlmostEqual(math.cos(math.pi * n), (-1.0) ** n, places=12)

    def test_fiber_multiplicity_is_complete_bipartite(self) -> None:
        m, k = 7, 11
        cross_pairs = [(i, j) for i in range(m) for j in range(k)]
        self.assertEqual(len(cross_pairs), m * k)

    def test_log_scale_is_unit_covariant(self) -> None:
        ell_star, epsilon = 12.0, 0.03
        original = math.log10(ell_star / epsilon)
        converted = math.log10((1000.0 * ell_star) / (1000.0 * epsilon))
        self.assertAlmostEqual(original, converted)


class MandelbrotScaleTests(unittest.TestCase):
    def test_covering_number_is_monotone(self) -> None:
        points = (0.0, 0.4, 0.8, 1.2, 1.6)
        fine = exact_covering_number(points, 0.21)
        coarse = exact_covering_number(points, 0.61)
        self.assertGreaterEqual(fine, coarse)

    def test_covering_number_is_unit_covariant(self) -> None:
        points = (0.0, 0.4, 0.8, 1.2, 1.6)
        scale = 100.0
        original = exact_covering_number(points, 0.41)
        converted = exact_covering_number(tuple(scale * x for x in points), scale * 0.41)
        self.assertEqual(original, converted)

    def test_koch_weighted_slope_is_exact(self) -> None:
        base = math.e
        stages = list(range(1, 9))
        x_values = [n * math.log(3.0, base) for n in stages]
        y_values = [n * math.log(4.0, base) for n in stages]
        slope, _, residuals = weighted_slope(x_values, y_values, [1.0] * len(stages))
        self.assertAlmostEqual(slope, math.log(4.0) / math.log(3.0), places=13)
        self.assertLess(max(abs(value) for value in residuals), 1e-12)

    def test_koch_pairwise_interval_collapses(self) -> None:
        x_values = [n * math.log(3.0) for n in range(1, 7)]
        y_values = [n * math.log(4.0) for n in range(1, 7)]
        lower, upper = pairwise_slope_interval(x_values, y_values)
        target = math.log(4.0) / math.log(3.0)
        self.assertAlmostEqual(lower, target, places=13)
        self.assertAlmostEqual(upper, target, places=13)

    def test_reference_shift_does_not_change_slope(self) -> None:
        x_values = [1.0, 2.0, 3.0, 4.0]
        y_values = [2.2 + 1.37 * x for x in x_values]
        first, _, _ = weighted_slope(x_values, y_values, [1.0] * 4)
        shifted = [x + math.log(17.0) for x in x_values]
        second, _, _ = weighted_slope(shifted, y_values, [1.0] * 4)
        self.assertAlmostEqual(first, second)

    def test_log_base_change_does_not_change_slope(self) -> None:
        x_values = [0.5, 1.0, 1.5, 2.0]
        y_values = [0.8 + 1.21 * x for x in x_values]
        first, _, _ = weighted_slope(x_values, y_values, [1.0] * 4)
        factor = 1.0 / math.log(10.0)
        second, _, _ = weighted_slope(
            [factor * x for x in x_values],
            [factor * y for y in y_values],
            [1.0] * 4,
        )
        self.assertAlmostEqual(first, second)

    def test_weight_choice_is_explicit_and_reproducible(self) -> None:
        x_values = [1.0, 2.0, 3.0, 4.0]
        y_values = [1.0, 2.1, 2.9, 4.3]
        first, _, _ = weighted_slope(x_values, y_values, [1.0, 1.0, 1.0, 1.0])
        second, _, _ = weighted_slope(x_values, y_values, [1.0, 1.0, 1.0, 5.0])
        self.assertNotAlmostEqual(first, second, places=6)

    def test_minkowski_normalization_recovers_dimension(self) -> None:
        ambient_dimension = 2.0
        target_dimension = 1.35
        ell_star = 7.0
        epsilons = [ell_star * 10.0 ** (-k) for k in range(1, 7)]
        x_values = [math.log(epsilon / ell_star) for epsilon in epsilons]
        normalized_volumes = [
            2.4 * (epsilon / ell_star) ** (ambient_dimension - target_dimension)
            for epsilon in epsilons
        ]
        y_values = [math.log(value) for value in normalized_volumes]
        exponent, _, _ = weighted_slope(x_values, y_values, [1.0] * len(x_values))
        recovered = ambient_dimension - exponent
        self.assertAlmostEqual(recovered, target_dimension, places=12)

    def test_exponent_equivalent_protocols_share_slope(self) -> None:
        dimension = 1.6
        epsilons = [10.0 ** (-k) for k in range(1, 8)]
        x_values = [math.log(1.0 / epsilon) for epsilon in epsilons]
        first_counts = [(1.0 / epsilon) ** dimension for epsilon in epsilons]
        second_counts = [3.0 * (1.0 / (2.0 * epsilon)) ** dimension for epsilon in epsilons]
        first, _, _ = weighted_slope(
            x_values, [math.log(value) for value in first_counts], [1.0] * len(epsilons)
        )
        second, _, _ = weighted_slope(
            x_values, [math.log(value) for value in second_counts], [1.0] * len(epsilons)
        )
        self.assertAlmostEqual(first, dimension)
        self.assertAlmostEqual(second, dimension)

    def test_matched_lipschitz_cover_for_finite_set(self) -> None:
        points = (0.0, 0.5, 1.0, 1.5, 2.0)
        lipschitz = 2.0
        epsilon = 0.51
        image = tuple(lipschitz * point for point in points)
        input_count = exact_covering_number(points, epsilon)
        image_count = exact_covering_number(image, lipschitz * epsilon)
        self.assertLessEqual(image_count, input_count)


class ContractAndLedgerTests(unittest.TestCase):
    def test_contract_has_required_layers(self) -> None:
        contract = yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))
        required = {
            "scale_roles",
            "global_distance",
            "local_global_separation",
            "shells",
            "unit_covariance",
            "matched_scales",
            "logarithmic_scale",
            "periodic_readout",
            "scale_trace",
            "protocol_equivalence",
            "claim_firewalls",
        }
        self.assertTrue(required.issubset(contract))

    def test_all_physical_scale_roles_have_seven_dimensions(self) -> None:
        contract = yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))
        for role, record in contract["scale_roles"].items():
            with self.subTest(role=role):
                self.assertEqual(len(record["dimension"]), 7)
                self.assertEqual(record["dimension"], [1, 0, 0, 0, 0, 0, 0])

    def test_reference_ledgers_are_complete(self) -> None:
        ledger = yaml.safe_load(LEDGER.read_text(encoding="utf-8"))
        documents = ledger["documents"]
        self.assertEqual(len(documents), 2)
        self.assertTrue(all(document["ledger_level"] == "reference" for document in documents))
        self.assertEqual(sum(len(document["expressions"]) for document in documents), 24)
        self.assertTrue(all("PENDING" not in document["source"]["sha256"] for document in documents))

    def test_reference_linter_is_clean(self) -> None:
        command = [
            "python3",
            str(ROOT / "work/go_core_v0_2/src/go_lint.py"),
            "--core-dir",
            str(ROOT / "work/go_core_v0_2/core"),
            "--ledger",
            str(LEDGER),
            "--mode",
            "strict",
            "--output-json",
            str(LINT_JSON),
        ]
        subprocess.run(command, check=True, capture_output=True, text=True)
        report = json.loads(LINT_JSON.read_text(encoding="utf-8"))
        self.assertEqual(report["summary"]["findings_total"], 0)
        self.assertEqual(report["summary"]["status_counts"], {"PASS": 2})
        self.assertEqual(report["summary"]["expressions_checked"], 24)


if __name__ == "__main__":
    unittest.main()
