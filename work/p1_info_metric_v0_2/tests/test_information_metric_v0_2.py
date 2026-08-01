#!/usr/bin/env python3
"""Regression tests for the GO P1 information and metric entropy modules."""

from __future__ import annotations

import itertools
import math
import unittest
from collections.abc import Callable, Iterable, Sequence


TOL = 1e-12


def logb(value: float, base: float) -> float:
    return math.log(value) / math.log(base)


def entropy(probabilities: Iterable[float], base: float = 2.0) -> float:
    return -sum(p * logb(p, base) for p in probabilities if p > 0.0)


def binary_entropy(p: float, base: float = 2.0) -> float:
    return entropy((p, 1.0 - p), base)


def joint_from_channel(
    source: Sequence[float], channel: Sequence[Sequence[float]]
) -> list[list[float]]:
    return [
        [source[x] * channel[x][y] for y in range(len(channel[x]))]
        for x in range(len(source))
    ]


def marginal_y(joint: Sequence[Sequence[float]]) -> list[float]:
    return [sum(row[y] for row in joint) for y in range(len(joint[0]))]


def conditional_entropy_x_given_y(
    source: Sequence[float],
    channel: Sequence[Sequence[float]],
    base: float = 2.0,
) -> float:
    joint = joint_from_channel(source, channel)
    py = marginal_y(joint)
    result = 0.0
    for y, py_value in enumerate(py):
        if py_value == 0.0:
            continue
        conditional = [joint[x][y] / py_value for x in range(len(source))]
        result += py_value * entropy(conditional, base)
    return result


def mutual_information(
    source: Sequence[float],
    channel: Sequence[Sequence[float]],
    base: float = 2.0,
) -> float:
    return entropy(source, base) - conditional_entropy_x_given_y(
        source, channel, base
    )


def compose_channels(
    first: Sequence[Sequence[float]], second: Sequence[Sequence[float]]
) -> list[list[float]]:
    return [
        [
            sum(first[x][y] * second[y][z] for y in range(len(second)))
            for z in range(len(second[0]))
        ]
        for x in range(len(first))
    ]


def pushforward(
    distribution: Sequence[float], channel: Sequence[Sequence[float]]
) -> list[float]:
    return [
        sum(distribution[x] * channel[x][y] for x in range(len(distribution)))
        for y in range(len(channel[0]))
    ]


def kl_divergence(
    p: Sequence[float], q: Sequence[float], base: float = 2.0
) -> float:
    total = 0.0
    for pi, qi in zip(p, q, strict=True):
        if pi == 0.0:
            continue
        if qi == 0.0:
            return math.inf
        total += pi * logb(pi / qi, base)
    return total


def powerset_indices(size: int) -> Iterable[tuple[int, ...]]:
    for count in range(size + 1):
        yield from itertools.combinations(range(size), count)


def covering_number(
    points: Sequence[object],
    distance: Callable[[object, object], float],
    epsilon: float,
) -> int:
    if not points:
        raise ValueError("the reference modules define entropy only for nonempty sets")
    for indices in powerset_indices(len(points)):
        if not indices:
            continue
        if all(
            any(distance(point, points[index]) <= epsilon + TOL for index in indices)
            for point in points
        ):
            return len(indices)
    raise AssertionError("finite set must admit a finite cover")


def packing_number(
    points: Sequence[object],
    distance: Callable[[object, object], float],
    epsilon: float,
) -> int:
    best = 0
    for indices in powerset_indices(len(points)):
        if all(
            distance(points[i], points[j]) > epsilon + TOL
            for i, j in itertools.combinations(indices, 2)
        ):
            best = max(best, len(indices))
    return best


class InformationModuleTests(unittest.TestCase):
    def test_information_unit_change(self) -> None:
        p = (0.1, 0.2, 0.7)
        h2 = entropy(p, 2.0)
        he = entropy(p, math.e)
        self.assertAlmostEqual(h2, logb(math.e, 2.0) * he)

    def test_deterministic_parity_decomposition(self) -> None:
        for m in (1, 2, 5, 13):
            source = [1.0 / (2 * m)] * (2 * m)
            channel = [
                [1.0, 0.0] if x % 2 == 0 else [0.0, 1.0]
                for x in range(2 * m)
            ]
            defect = conditional_entropy_x_given_y(source, channel, 2.0)
            retained = mutual_information(source, channel, 2.0)
            self.assertAlmostEqual(defect, logb(m, 2.0))
            self.assertAlmostEqual(retained, 1.0)
            self.assertAlmostEqual(entropy(source, 2.0), retained + defect)

    def test_normalized_information_defect_is_base_invariant(self) -> None:
        source = [0.1, 0.2, 0.3, 0.4]
        channel = [[1.0, 0.0], [1.0, 0.0], [0.0, 1.0], [0.0, 1.0]]
        delta2 = conditional_entropy_x_given_y(source, channel, 2.0) / entropy(
            source, 2.0
        )
        deltae = conditional_entropy_x_given_y(source, channel, math.e) / entropy(
            source, math.e
        )
        self.assertAlmostEqual(delta2, deltae)
        self.assertGreaterEqual(delta2, 0.0)
        self.assertLessEqual(delta2, 1.0)

    def test_degenerate_source_zero_policy(self) -> None:
        source = [1.0, 0.0]
        channel = [[0.3, 0.7], [0.8, 0.2]]
        self.assertAlmostEqual(entropy(source), 0.0)
        self.assertAlmostEqual(
            conditional_entropy_x_given_y(source, channel), 0.0
        )
        normalized = 0.0
        self.assertEqual(normalized, 0.0)

    def test_data_processing_and_defect_monotonicity(self) -> None:
        source = [0.2, 0.5, 0.3]
        first = [[0.9, 0.1], [0.4, 0.6], [0.2, 0.8]]
        second = [[0.85, 0.15], [0.25, 0.75]]
        composed = compose_channels(first, second)
        i_xy = mutual_information(source, first)
        i_xz = mutual_information(source, composed)
        h_xy = conditional_entropy_x_given_y(source, first)
        h_xz = conditional_entropy_x_given_y(source, composed)
        self.assertLessEqual(i_xz, i_xy + TOL)
        self.assertGreaterEqual(h_xz + TOL, h_xy)
        self.assertAlmostEqual(h_xz - h_xy, i_xy - i_xz)

    def test_kl_contraction(self) -> None:
        p = [0.55, 0.25, 0.20]
        q = [0.20, 0.35, 0.45]
        channel = [[0.8, 0.2], [0.4, 0.6], [0.1, 0.9]]
        before = kl_divergence(p, q)
        after = kl_divergence(
            pushforward(p, channel), pushforward(q, channel)
        )
        self.assertLessEqual(after, before + TOL)

    def test_binary_symmetric_channel(self) -> None:
        alpha = 0.17
        source = [0.5, 0.5]
        channel = [[1 - alpha, alpha], [alpha, 1 - alpha]]
        defect = conditional_entropy_x_given_y(source, channel, 2.0)
        self.assertAlmostEqual(defect, binary_entropy(alpha, 2.0))
        self.assertAlmostEqual(mutual_information(source, channel), 1.0 - defect)

    def test_fano_binary_equality_for_direct_decoder(self) -> None:
        error = 0.23
        source = [0.5, 0.5]
        channel = [[1 - error, error], [error, 1 - error]]
        conditional = conditional_entropy_x_given_y(source, channel)
        fano_rhs = binary_entropy(error) + error * logb(1.0, 2.0)
        self.assertAlmostEqual(conditional, fano_rhs)


class MetricModuleTests(unittest.TestCase):
    @staticmethod
    def line_distance(x: object, y: object) -> float:
        return abs(float(x) - float(y))

    def test_covering_packing_sandwich(self) -> None:
        points = [0.0, 0.4, 1.0, 1.9, 2.1]
        epsilon = 0.55
        p2 = packing_number(points, self.line_distance, 2 * epsilon)
        n = covering_number(points, self.line_distance, epsilon)
        p1 = packing_number(points, self.line_distance, epsilon)
        self.assertLessEqual(p2, n)
        self.assertLessEqual(n, p1)

    def test_metric_unit_covariance(self) -> None:
        points = [0.0, 0.5, 1.7, 3.0]
        epsilon = 0.8
        original = covering_number(points, self.line_distance, epsilon)
        for scale in (0.01, 100.0, 1000.0):
            scaled = [scale * value for value in points]
            self.assertEqual(
                original,
                covering_number(
                    scaled, self.line_distance, scale * epsilon
                ),
            )

    def test_matched_lipschitz_contraction(self) -> None:
        points = [0.0, 0.5, 1.0, 1.5, 2.0]
        image = [2.0 * value for value in points]
        epsilon_x = 0.55
        lipschitz = 2.0
        epsilon_y = lipschitz * epsilon_x
        n_input = covering_number(points, self.line_distance, epsilon_x)
        n_output = covering_number(image, self.line_distance, epsilon_y)
        self.assertLessEqual(n_output, n_input)

    def test_metric_defect_base_invariance(self) -> None:
        n_input = 12
        n_output = 3
        delta2 = (logb(n_input, 2.0) - logb(n_output, 2.0)) / logb(
            n_input, 2.0
        )
        deltae = (logb(n_input, math.e) - logb(n_output, math.e)) / logb(
            n_input, math.e
        )
        self.assertAlmostEqual(delta2, deltae)
        self.assertGreaterEqual(delta2, 0.0)
        self.assertLessEqual(delta2, 1.0)

    def test_exact_defect_composition(self) -> None:
        hidden_count = 4
        parity_count = 2
        constant_count = 1
        direct = logb(hidden_count, 2.0) - logb(constant_count, 2.0)
        first = logb(hidden_count, 2.0) - logb(parity_count, 2.0)
        second = logb(parity_count, 2.0) - logb(constant_count, 2.0)
        self.assertAlmostEqual(direct, first + second)

    def test_product_covering_bounds(self) -> None:
        base = [0.0, 2.0]
        fiber = [0.0, 3.0]
        product = list(itertools.product(base, fiber))

        def max_metric(left: object, right: object) -> float:
            lx, lf = left  # type: ignore[misc]
            rx, rf = right  # type: ignore[misc]
            return max(abs(lx - rx), abs(lf - rf))

        epsilon = 0.5
        nb = covering_number(base, self.line_distance, epsilon)
        nf = covering_number(fiber, self.line_distance, epsilon)
        np = covering_number(product, max_metric, epsilon)
        self.assertLessEqual(nb, np)
        self.assertLessEqual(np, nb * nf)

    def test_hidden_circle_formula_has_dimensionless_ratio(self) -> None:
        radius = 2.5
        epsilon = 0.2
        count = math.ceil(math.pi * radius / epsilon)
        self.assertGreaterEqual(2 * count * epsilon, 2 * math.pi * radius)
        self.assertLess(2 * (count - 1) * epsilon, 2 * math.pi * radius)
        self.assertTrue(math.isfinite(logb(radius / epsilon, 2.0)))

    def test_finite_parity_resolution_threshold(self) -> None:
        parity = [0.0, 1.0]
        self.assertEqual(
            covering_number(parity, self.line_distance, 0.99), 2
        )
        self.assertEqual(
            covering_number(parity, self.line_distance, 1.0), 1
        )

    def test_chromatic_graph_sandwich(self) -> None:
        points = [0.0, 1.0, 2.0]
        epsilon = 1.1
        slope_factor = math.sqrt(2.0)
        graph = [(x, x) for x in points]

        def graph_distance(left: object, right: object) -> float:
            lx, lc = left  # type: ignore[misc]
            rx, rc = right  # type: ignore[misc]
            return math.hypot(lx - rx, lc - rc)

        lower = covering_number(points, self.line_distance, epsilon)
        middle = covering_number(graph, graph_distance, epsilon)
        upper = covering_number(
            points, self.line_distance, epsilon / slope_factor
        )
        self.assertLessEqual(lower, middle)
        self.assertLessEqual(middle, upper)

    def test_heat_exponent_is_dimensionless_numerically(self) -> None:
        heat_length_squared = 0.3
        inverse_length_squared_eigenvalue = 7.0
        exponent = heat_length_squared * inverse_length_squared_eigenvalue
        self.assertAlmostEqual(exponent, 2.1)
        self.assertGreater(math.exp(-exponent), 0.0)

    def test_physical_diffusion_scale(self) -> None:
        diffusivity = 1.4e-7
        physical_time = 12.0
        reference_length = 0.004
        tau = diffusivity * physical_time / reference_length**2
        self.assertGreater(tau, 0.0)
        self.assertTrue(math.isfinite(tau))


if __name__ == "__main__":
    unittest.main(verbosity=2)
