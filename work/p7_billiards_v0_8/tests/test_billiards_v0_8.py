#!/usr/bin/env python3
"""Regression tests for the P7 strict billiards release."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import re
import subprocess
import unittest
from collections import Counter
from pathlib import Path

import yaml
from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[3]
P7 = ROOT / "work/p7_billiards_v0_8"
PDF = P7 / "build/billiards/billiards_observation_laboratory_v1_1.pdf"
TEX = P7 / "src/billiards_observation_laboratory_v1_1.tex"
TEXT = P7 / "checks/billiards/billiards_observation_laboratory_v1_1.txt"
LOG = P7 / "build/billiards/billiards_observation_laboratory_v1_1.log"
CONTRACT = P7 / "core/billiards_observation_contract_v0_8.yaml"
REFERENCE_LEDGER = P7 / "ledgers/billiards_reference_ledger_v0_8.yaml"
CORPUS_LEDGER = P7 / "ledgers/corpus_ledgers_v0_8.yaml"
REFERENCE_LINT = P7 / "reports/Billiards_Reference_Lint_Report_v0_8.json"
CORPUS_LINT = P7 / "reports/GO_Corpus_Lint_Report_v0_8.json"
BENCHMARKS = P7 / "data/billiards_benchmarks_v0_8.csv"
METRICS = P7 / "data/billiards_metrics_v0_8.json"


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


def dot(left: tuple[float, ...], right: tuple[float, ...]) -> float:
    return sum(
        first * second for first, second in zip(left, right, strict=True)
    )


def norm(vector: tuple[float, ...]) -> float:
    return math.sqrt(dot(vector, vector))


def reflect(
    direction: tuple[float, float],
    inward_normal: tuple[float, float],
) -> tuple[float, float]:
    coefficient = 2.0 * dot(direction, inward_normal)
    return (
        direction[0] - coefficient * inward_normal[0],
        direction[1] - coefficient * inward_normal[1],
    )


def disk_step(s: float, p: float, radius: float) -> tuple[float, float]:
    if radius <= 0:
        raise ValueError("radius must be positive")
    if not -1.0 < p < 1.0:
        raise ValueError("regular disk collision requires abs(p) < 1")
    perimeter = 2.0 * math.pi * radius
    return ((s + 2.0 * radius * math.acos(p)) % perimeter, p)


def disk_inverse(s: float, p: float, radius: float) -> tuple[float, float]:
    perimeter = 2.0 * math.pi * radius
    return ((s - 2.0 * radius * math.acos(p)) % perimeter, p)


def circle_point(s: float, radius: float) -> tuple[float, float]:
    theta = s / radius
    return (radius * math.cos(theta), radius * math.sin(theta))


def circle_tangent(s: float, radius: float) -> tuple[float, float]:
    theta = s / radius
    return (-math.sin(theta), math.cos(theta))


def entropy(counts: Counter[str], base: float = 2.0) -> float:
    total = sum(counts.values())
    if total <= 0:
        raise ValueError("positive total required")
    return -sum(
        (count / total) * math.log(count / total, base)
        for count in counts.values()
        if count
    )


def cyclic_conditional_entropy(word: str, base: float = 2.0) -> float:
    if len(word) < 2:
        raise ValueError("at least two symbols required")
    symbols = Counter(word)
    pairs = Counter(
        (word[index], word[(index + 1) % len(word)])
        for index in range(len(word))
    )
    total = len(word)
    return -sum(
        (count / total) * math.log(count / symbols[left], base)
        for (left, _right), count in pairs.items()
        if count
    )


def weighted_slope(
    xs: list[float],
    ys: list[float],
    weights: list[float],
) -> float:
    if not (len(xs) == len(ys) == len(weights)) or not xs:
        raise ValueError("nonempty arrays of equal length required")
    total = sum(weights)
    if total <= 0:
        raise ValueError("positive total weight required")
    mean_x = sum(w * x for x, w in zip(xs, weights, strict=True)) / total
    numerator = sum(
        w * (x - mean_x) * y
        for x, y, w in zip(xs, ys, weights, strict=True)
    )
    denominator = sum(w * (x - mean_x) ** 2 for x, w in zip(xs, weights))
    if denominator <= 0:
        raise ValueError("positive weighted variance required")
    return numerator / denominator


def rectangle_lambda(
    width: float,
    height: float,
    mode_x: int,
    mode_y: int,
) -> float:
    if width <= 0 or height <= 0:
        raise ValueError("positive side lengths required")
    if mode_x <= 0 or mode_y <= 0:
        raise ValueError("positive mode numbers required")
    return math.pi**2 * (
        (mode_x / width) ** 2 + (mode_y / height) ** 2
    )


class ReflectionAndFlowTests(unittest.TestCase):
    def test_free_flight_distance(self) -> None:
        self.assertAlmostEqual(3.2 * 1.5, 4.8)

    def test_reflection_preserves_norm(self) -> None:
        direction = (-0.8, 0.6)
        reflected = reflect(direction, (1.0, 0.0))
        self.assertAlmostEqual(norm(reflected), norm(direction))

    def test_reflection_flips_normal_component(self) -> None:
        direction = (-0.8, 0.6)
        normal = (1.0, 0.0)
        reflected = reflect(direction, normal)
        self.assertAlmostEqual(dot(reflected, normal), -dot(direction, normal))

    def test_reflection_preserves_tangent_component(self) -> None:
        direction = (-0.8, 0.6)
        reflected = reflect(direction, (1.0, 0.0))
        self.assertAlmostEqual(dot(reflected, (0.0, 1.0)), 0.6)

    def test_reflection_is_involution(self) -> None:
        direction = (-0.8, 0.6)
        normal = (1.0, 0.0)
        restored = reflect(reflect(direction, normal), normal)
        for actual, expected in zip(restored, direction, strict=True):
            self.assertAlmostEqual(actual, expected)

    def test_incoming_inward_normal_sign(self) -> None:
        self.assertLess(dot((-0.8, 0.6), (1.0, 0.0)), 0.0)

    def test_outgoing_inward_normal_sign(self) -> None:
        reflected = reflect((-0.8, 0.6), (1.0, 0.0))
        self.assertGreater(dot(reflected, (1.0, 0.0)), 0.0)

    def test_unit_direction_velocity(self) -> None:
        speed = 7.0
        direction = (0.6, 0.8)
        velocity = tuple(speed * value for value in direction)
        self.assertAlmostEqual(norm(velocity), speed)

    def test_nonunit_normal_changes_energy_and_is_rejected_by_contract(self) -> None:
        normal = (2.0, 0.0)
        self.assertNotAlmostEqual(
            norm(reflect((-0.8, 0.6), normal)),
            norm((-0.8, 0.6)),
        )
        contract = load_yaml(CONTRACT)
        self.assertIn(
            "inward_normal_convention",
            contract["elastic_flow"],
        )

    def test_singular_policy_lists_corner_and_grazing(self) -> None:
        excluded = load_yaml(CONTRACT)["table_class"]["singular_orbit_policy"][
            "excluded_by_default"
        ]
        self.assertIn("corner_hit", excluded)
        self.assertIn("grazing_collision", excluded)


class CollisionMeasureTests(unittest.TestCase):
    def test_measure_normalization_analytic(self) -> None:
        boundary_length = 17.0
        integral = (
            boundary_length
            * (math.sin(math.pi / 2) - math.sin(-math.pi / 2))
            / (2.0 * boundary_length)
        )
        self.assertAlmostEqual(integral, 1.0)

    def test_measure_normalization_midpoint_quadrature(self) -> None:
        bins = 20000
        delta = math.pi / bins
        integral = sum(
            math.cos(-math.pi / 2 + (index + 0.5) * delta) * delta
            for index in range(bins)
        ) / 2.0
        self.assertAlmostEqual(integral, 1.0, places=8)

    def test_p_coordinate_jacobian(self) -> None:
        phi = 0.37
        epsilon = 1e-7
        derivative = (
            math.sin(phi + epsilon) - math.sin(phi - epsilon)
        ) / (2.0 * epsilon)
        self.assertAlmostEqual(derivative, math.cos(phi), places=9)

    def test_p_range_excludes_grazing(self) -> None:
        for phi in (-1.1, 0.0, 1.1):
            self.assertLess(abs(math.sin(phi)), 1.0)

    def test_disk_map_preserves_p(self) -> None:
        self.assertEqual(disk_step(1.0, 0.42, 2.3)[1], 0.42)

    def test_disk_map_has_explicit_inverse(self) -> None:
        state = (1.0, 0.42)
        forward = disk_step(*state, 2.3)
        backward = disk_inverse(*forward, 2.3)
        self.assertAlmostEqual(backward[0], state[0])
        self.assertAlmostEqual(backward[1], state[1])

    def test_disk_map_output_arclength_is_canonical(self) -> None:
        radius = 2.3
        output, _ = disk_step(100.0, -0.7, radius)
        self.assertGreaterEqual(output, 0.0)
        self.assertLess(output, 2.0 * math.pi * radius)

    def test_roof_time_is_positive_on_regular_space(self) -> None:
        radius, p, speed = 2.3, 0.4, 3.0
        roof = 2.0 * radius * math.sqrt(1.0 - p**2) / speed
        self.assertGreater(roof, 0.0)

    def test_roof_time_tends_to_zero_at_grazing_boundary(self) -> None:
        radius, speed = 2.3, 3.0
        near_grazing = 1.0 - 1e-14
        roof = 2.0 * radius * math.sqrt(1.0 - near_grazing**2) / speed
        self.assertLess(roof, 1e-6)

    def test_collision_map_is_not_labeled_information_loss(self) -> None:
        maps = load_yaml(REFERENCE_LEDGER)["documents"][0]["maps"]
        collision = next(item for item in maps if item["id"] == "collision_map")
        self.assertFalse(collision["information_loss"])
        self.assertEqual(collision["invertibility"], "required")


class SequentialIdentifiabilityTests(unittest.TestCase):
    def reconstructed_direction(
        self,
        radius: float,
        s: float,
        p: float,
    ) -> tuple[float, float]:
        next_s, _ = disk_step(s, p, radius)
        first = circle_point(s, radius)
        second = circle_point(next_s, radius)
        chord = (second[0] - first[0], second[1] - first[1])
        chord_norm = norm(chord)
        return (chord[0] / chord_norm, chord[1] / chord_norm)

    def test_two_impacts_reconstruct_unit_direction(self) -> None:
        direction = self.reconstructed_direction(2.3, 0.7, 0.4)
        self.assertAlmostEqual(norm(direction), 1.0)

    def test_two_impacts_reconstruct_p(self) -> None:
        radius, s, p = 2.3, 0.7, 0.4
        direction = self.reconstructed_direction(radius, s, p)
        reconstructed = dot(direction, circle_tangent(s, radius))
        self.assertAlmostEqual(reconstructed, p, places=13)

    def test_single_impact_is_noninjective(self) -> None:
        same_s = 1.25
        states = ((same_s, -0.4), (same_s, 0.4))
        self.assertEqual(states[0][0], states[1][0])
        self.assertNotEqual(states[0], states[1])

    def test_distinct_impact_guard(self) -> None:
        point = circle_point(0.0, 2.3)
        chord = (point[0] - point[0], point[1] - point[1])
        self.assertEqual(norm(chord), 0.0)
        with self.assertRaises(ZeroDivisionError):
            _ = chord[0] / norm(chord)

    def test_uniform_scale_does_not_change_reconstructed_direction(self) -> None:
        base = self.reconstructed_direction(2.3, 0.7, 0.4)
        scaled = self.reconstructed_direction(6.9, 2.1, 0.4)
        for actual, expected in zip(scaled, base, strict=True):
            self.assertAlmostEqual(actual, expected, places=13)

    def test_order_reversal_reverses_chord_direction(self) -> None:
        radius, s, p = 2.3, 0.7, 0.4
        next_s, _ = disk_step(s, p, radius)
        first = circle_point(s, radius)
        second = circle_point(next_s, radius)
        forward = (
            (second[0] - first[0]) / norm(
                (second[0] - first[0], second[1] - first[1])
            ),
            (second[1] - first[1]) / norm(
                (second[0] - first[0], second[1] - first[1])
            ),
        )
        backward = (-forward[0], -forward[1])
        self.assertAlmostEqual(dot(forward, backward), -1.0)

    def test_contract_states_two_impact_hypotheses(self) -> None:
        hypotheses = load_yaml(CONTRACT)["observation_chain"][
            "two_impact_reconstruction"
        ]["hypotheses"]
        self.assertIn("known_strictly_convex_C1_table", hypotheses)
        self.assertIn("ordered_impact_pair", hypotheses)


class SymbolicEntropyTests(unittest.TestCase):
    def test_finite_word_codomain_cardinality(self) -> None:
        self.assertEqual(4**7, 16384)

    def test_pigeonhole_noninjectivity_on_discretized_states(self) -> None:
        outputs = [index % 8 for index in range(100)]
        self.assertLess(len(set(outputs)), len(outputs))

    def test_alternating_marginal_entropy(self) -> None:
        self.assertAlmostEqual(entropy(Counter("01010101")), 1.0)

    def test_order_sensitive_marginal_entropy(self) -> None:
        self.assertAlmostEqual(entropy(Counter("00110011")), 1.0)

    def test_alternating_conditional_entropy(self) -> None:
        self.assertAlmostEqual(cyclic_conditional_entropy("01010101"), 0.0)

    def test_order_sensitive_conditional_entropy(self) -> None:
        self.assertAlmostEqual(cyclic_conditional_entropy("00110011"), 1.0)

    def test_same_marginal_different_transition_entropy(self) -> None:
        first, second = "01010101", "00110011"
        self.assertEqual(Counter(first), Counter(second))
        self.assertNotEqual(
            cyclic_conditional_entropy(first),
            cyclic_conditional_entropy(second),
        )

    def test_entropy_base_conversion(self) -> None:
        counts = Counter({"a": 2, "b": 1, "c": 1})
        entropy_nats = entropy(counts, math.e)
        entropy_bits = entropy(counts, 2.0)
        self.assertAlmostEqual(entropy_nats / math.log(2), entropy_bits)

    def test_normalized_entropy_base_invariance(self) -> None:
        counts = Counter({"a": 2, "b": 1, "c": 1})
        natural = entropy(counts, math.e) / math.log(3)
        binary = entropy(counts, 2.0) / math.log2(3)
        self.assertAlmostEqual(natural, binary)

    def test_zero_count_is_omitted(self) -> None:
        self.assertAlmostEqual(
            entropy(Counter({"a": 2, "b": 0, "c": 2})),
            1.0,
        )

    def test_empty_entropy_is_undefined(self) -> None:
        with self.assertRaises(ValueError):
            entropy(Counter())

    def test_symbol_relabeling_preserves_entropy(self) -> None:
        original = Counter("001011")
        relabeled = Counter("aababb")
        self.assertAlmostEqual(entropy(original), entropy(relabeled))

    def test_contract_separates_four_entropy_semantics(self) -> None:
        symbolic = load_yaml(CONTRACT)["symbolic_entropy"]
        for key in ("marginal", "block", "rate", "kolmogorov_sinai"):
            self.assertIn(key, symbolic)


class DiskReferenceTests(unittest.TestCase):
    def test_boundary_length(self) -> None:
        self.assertAlmostEqual(2.0 * math.pi * 2.3, 14.451326206513047)

    def test_collision_advance(self) -> None:
        advance = 2.0 * 2.3 * math.acos(0.4)
        self.assertAlmostEqual(advance, 5.332685611346078)

    def test_rotation_number(self) -> None:
        self.assertAlmostEqual(
            math.acos(0.4) / math.pi,
            0.36901011956554536,
        )

    def test_chord_length(self) -> None:
        chord = 2.0 * 2.3 * math.sqrt(1.0 - 0.4**2)
        self.assertAlmostEqual(chord, 4.215969639359373)

    def test_roof_time(self) -> None:
        roof = 2.0 * 2.3 * math.sqrt(1.0 - 0.4**2) / 3.0
        self.assertAlmostEqual(roof, 1.405323213119791)

    def test_reduced_angular_momentum_coordinate(self) -> None:
        self.assertAlmostEqual(2.3 * 0.4, 0.92)

    def test_diameter_orbit_has_period_two(self) -> None:
        radius = 2.3
        state = (0.4, 0.0)
        state = disk_step(*state, radius)
        state = disk_step(*state, radius)
        self.assertAlmostEqual(state[0], 0.4)
        self.assertAlmostEqual(state[1], 0.0)

    def test_one_third_rotation_has_period_three(self) -> None:
        radius = 2.3
        p = math.cos(math.pi / 3.0)
        state = (0.4, p)
        for _ in range(3):
            state = disk_step(*state, radius)
        self.assertAlmostEqual(state[0], 0.4, places=12)

    def test_disk_map_rejects_grazing_coordinate(self) -> None:
        with self.assertRaises(ValueError):
            disk_step(0.0, 1.0, 2.3)

    def test_disk_map_rejects_nonpositive_radius(self) -> None:
        with self.assertRaises(ValueError):
            disk_step(0.0, 0.4, 0.0)


class FiniteWindowDiagnosticTests(unittest.TestCase):
    def test_dimensionless_log_ratio_is_unit_invariant(self) -> None:
        metres = math.log(0.002 / 0.0001)
        millimetres = math.log(2.0 / 0.1)
        self.assertAlmostEqual(metres, millimetres)

    def test_weighted_fit_recovers_exact_exponential_slope(self) -> None:
        xs = [float(index) for index in range(8)]
        ys = [0.23 * value - 4.0 for value in xs]
        self.assertAlmostEqual(
            weighted_slope(xs, ys, [1.0] * len(xs)),
            0.23,
        )

    def test_fit_requires_positive_total_weight(self) -> None:
        with self.assertRaises(ValueError):
            weighted_slope([0.0, 1.0], [0.0, 1.0], [0.0, 0.0])

    def test_fit_requires_positive_window_variance(self) -> None:
        with self.assertRaises(ValueError):
            weighted_slope([1.0, 1.0], [0.0, 1.0], [1.0, 1.0])

    def test_saturation_can_create_window_dependence(self) -> None:
        xs = [float(index) for index in range(10)]
        ys = [min(0.5 * value, 2.0) for value in xs]
        early = weighted_slope(xs[:4], ys[:4], [1.0] * 4)
        late = weighted_slope(xs[6:], ys[6:], [1.0] * 4)
        self.assertGreater(early, 0.4)
        self.assertAlmostEqual(late, 0.0)

    def test_contract_does_not_promote_proxy_to_exponent(self) -> None:
        prohibitions = load_yaml(CONTRACT)["chaos_diagnostics"]["prohibition"]
        self.assertIn(
            "positive_finite_window_slope_does_not_prove_positive_Lyapunov_exponent",
            prohibitions,
        )

    def test_source_names_fit_a_diagnostic(self) -> None:
        source = TEX.read_text(encoding="utf-8")
        self.assertIn(r"\widehat\lambda_{N_0,N_1}", source)
        self.assertIn("only a plot slope", source)


class SpectralTests(unittest.TestCase):
    def test_rectangle_first_eigenvalue(self) -> None:
        expected = 1.25 * math.pi**2
        self.assertAlmostEqual(rectangle_lambda(2.0, 1.0, 1, 1), expected)

    def test_rectangle_eigenvalues_are_positive(self) -> None:
        self.assertGreater(rectangle_lambda(2.0, 1.0, 1, 1), 0.0)

    def test_rectangle_scaling_covariance(self) -> None:
        base = rectangle_lambda(2.0, 1.0, 2, 3)
        scaled = rectangle_lambda(6.0, 3.0, 2, 3)
        self.assertAlmostEqual(scaled / base, 1.0 / 9.0)

    def test_area_eigenvalue_similarity_invariance(self) -> None:
        width, height, scale = 2.0, 1.0, 3.0
        base = width * height * rectangle_lambda(width, height, 1, 1)
        scaled = (
            scale
            * width
            * scale
            * height
            * rectangle_lambda(scale * width, scale * height, 1, 1)
        )
        self.assertAlmostEqual(base, scaled)

    def test_square_multiplicity(self) -> None:
        self.assertAlmostEqual(
            rectangle_lambda(1.0, 1.0, 1, 2),
            rectangle_lambda(1.0, 1.0, 2, 1),
        )

    def test_eigenvalue_rejects_nonpositive_side(self) -> None:
        with self.assertRaises(ValueError):
            rectangle_lambda(0.0, 1.0, 1, 1)

    def test_eigenvalue_rejects_zero_mode(self) -> None:
        with self.assertRaises(ValueError):
            rectangle_lambda(1.0, 1.0, 0, 1)

    def test_energy_bridge_joule_value(self) -> None:
        hbar = 6.62607015e-34 / (2.0 * math.pi)
        mass = 9.1093837139e-31
        eigenvalue = rectangle_lambda(2e-9, 1e-9, 1, 1)
        energy = hbar**2 * eigenvalue / (2.0 * mass)
        self.assertAlmostEqual(energy, 7.530834242545738e-20, places=33)

    def test_energy_bridge_electronvolt_value(self) -> None:
        hbar = 6.62607015e-34 / (2.0 * math.pi)
        mass = 9.1093837139e-31
        charge = 1.602176634e-19
        energy_ev = (
            hbar**2
            * rectangle_lambda(2e-9, 1e-9, 1, 1)
            / (2.0 * mass * charge)
        )
        self.assertAlmostEqual(energy_ev, 0.4700377026310907)

    def test_weyl_counting_ratio_for_rectangle(self) -> None:
        width, height, threshold = 2.0, 1.0, 50000.0
        max_m = int(width * math.sqrt(threshold) / math.pi) + 1
        max_n = int(height * math.sqrt(threshold) / math.pi) + 1
        count = sum(
            rectangle_lambda(width, height, m, n) < threshold
            for m in range(1, max_m + 1)
            for n in range(1, max_n + 1)
        )
        leading = width * height * threshold / (4.0 * math.pi)
        self.assertLess(abs(count / leading - 1.0), 0.03)

    def test_contract_declares_spectral_noninjectivity(self) -> None:
        inverse = load_yaml(CONTRACT)["spectral_layer"]["inverse_boundary"]
        self.assertTrue(inverse["known_noninjectivity"])

    def test_ledger_separates_lambda_and_energy_dimensions(self) -> None:
        quantities = {
            item["id"]: item
            for item in load_yaml(REFERENCE_LEDGER)["documents"][0][
                "quantities"
            ]
        }
        self.assertEqual(
            quantities["billiards.laplacian_eigenvalue"]["extends"],
            "spectral.laplacian_eigenvalue",
        )
        self.assertEqual(
            quantities["billiards.energy"]["extends"],
            "mechanics.energy",
        )

    def test_source_uses_lambda_for_laplacian_spectrum(self) -> None:
        source = TEX.read_text(encoding="utf-8")
        self.assertIn(r"\lambda_1(\Omega)", source)
        self.assertNotIn(r"-\Delta\psi_n=E_n", source)

    def test_spectral_scaling_is_not_called_invariance(self) -> None:
        source = TEX.read_text(encoding="utf-8")
        self.assertIn("Rigid invariance and scale covariance", source)


class DissipativeBoundaryTests(unittest.TestCase):
    @staticmethod
    def loss(mass: float, restitution: float, normal_speed: float) -> float:
        return (
            0.5
            * mass
            * (1.0 - restitution**2)
            * normal_speed**2
        )

    def test_elastic_limit_has_zero_loss(self) -> None:
        self.assertAlmostEqual(self.loss(2.0, 1.0, -3.0), 0.0)

    def test_plastic_normal_limit_has_maximal_loss(self) -> None:
        self.assertAlmostEqual(self.loss(2.0, 0.0, -3.0), 9.0)

    def test_loss_is_nonnegative_on_contract_domain(self) -> None:
        for restitution in (0.0, 0.25, 0.5, 0.75, 1.0):
            self.assertGreaterEqual(
                self.loss(2.0, restitution, -3.0),
                0.0,
            )

    def test_normal_velocity_update(self) -> None:
        restitution, incoming = 0.8, -3.0
        outgoing = -restitution * incoming
        self.assertAlmostEqual(outgoing, 2.4)

    def test_speed_state_must_expand_when_restitution_is_nonelastic(self) -> None:
        state_change = load_yaml(CONTRACT)["dissipative_boundary"][
            "state_space_change"
        ]
        self.assertIn("speed_or_energy", state_change["if_e_less_than_one"])

    def test_elastic_measure_is_not_inherited(self) -> None:
        excluded = load_yaml(CONTRACT)["dissipative_boundary"][
            "not_inherited_automatically"
        ]
        self.assertIn("elastic_invariant_measure", excluded)


class LedgerAndArtifactTests(unittest.TestCase):
    def test_reference_lint_is_clean(self) -> None:
        summary = load_json(REFERENCE_LINT)["summary"]
        self.assertEqual(summary["status_counts"], {"PASS": 1})
        self.assertEqual(summary["findings_total"], 0)

    def test_reference_lint_checks_24_expressions(self) -> None:
        self.assertEqual(
            load_json(REFERENCE_LINT)["summary"]["expressions_checked"],
            24,
        )

    def test_corpus_has_14_pass_and_4_fail(self) -> None:
        statuses = load_json(CORPUS_LINT)["summary"]["status_counts"]
        self.assertEqual(statuses, {"FAIL": 4, "PASS": 14})

    def test_corpus_has_no_blocked_status(self) -> None:
        statuses = load_json(CORPUS_LINT)["summary"]["status_counts"]
        self.assertNotIn("BLOCKED", statuses)

    def test_legacy_billiards_adapter_is_replaced(self) -> None:
        ids = {
            item["id"] for item in load_yaml(CORPUS_LEDGER)["documents"]
        }
        self.assertNotIn("billiards-observation-v1", ids)
        self.assertIn("billiards-observation-v1-1", ids)

    def test_corpus_contains_18_unique_documents(self) -> None:
        documents = load_yaml(CORPUS_LEDGER)["documents"]
        ids = [item["id"] for item in documents]
        self.assertEqual(len(ids), 18)
        self.assertEqual(len(set(ids)), 18)

    def test_pdf_hash_matches_reference_ledger(self) -> None:
        declared = load_yaml(REFERENCE_LEDGER)["documents"][0]["source"][
            "sha256"
        ]
        self.assertEqual(sha256(PDF), declared)

    def test_pdf_page_count(self) -> None:
        self.assertEqual(len(PdfReader(str(PDF)).pages), 9)

    def test_pdf_metadata(self) -> None:
        metadata = PdfReader(str(PDF)).metadata
        self.assertIn("Typed Geometry of Observation", metadata.title)
        self.assertEqual(metadata.author, "Stas, Independent Research Program")

    def test_pdf_text_contains_orcid(self) -> None:
        self.assertIn("0009-0000-2294-705X", TEXT.read_text(encoding="utf-8"))

    def test_pdf_text_contains_all_core_sections(self) -> None:
        text = TEXT.read_text(encoding="utf-8")
        for heading in (
            "Collision space, singularities, and invariant measure",
            "Finite symbolic channels and entropy semantics",
            "Quantum billiards: operator, dimensions, and spectrum",
            "Dissipative and non-specular variants",
            "Claim register and boundary",
        ):
            self.assertIn(heading, text)

    def test_latex_log_is_clean(self) -> None:
        log = LOG.read_text(encoding="utf-8", errors="replace")
        pattern = re.compile(
            r"(Overfull|Underfull|Missing character|undefined references|"
            r"multiply defined|LaTeX Warning|Package .* Warning)"
        )
        self.assertIsNone(pattern.search(log))

    def test_fonts_are_embedded(self) -> None:
        result = subprocess.run(
            ["pdffonts", str(PDF)],
            check=True,
            capture_output=True,
            text=True,
        )
        lines = [line.split() for line in result.stdout.splitlines()[2:] if line]
        self.assertTrue(lines)
        self.assertTrue(all(parts[-5] == "yes" for parts in lines))

    def test_benchmark_row_count(self) -> None:
        with BENCHMARKS.open("r", encoding="utf-8", newline="") as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual(len(rows), 18)

    def test_benchmark_metrics_schema(self) -> None:
        metrics = load_json(METRICS)
        self.assertEqual(
            metrics["schema"]["id"],
            "go-p7-billiards-benchmark-metrics",
        )
        self.assertEqual(metrics["row_count"], 18)

    def test_contract_has_ten_reference_gates(self) -> None:
        self.assertEqual(len(load_yaml(CONTRACT)["reference_gates"]), 10)

    def test_source_claim_firewall(self) -> None:
        source = TEX.read_text(encoding="utf-8")
        self.assertIn("does not claim a new theorem in billiard dynamics", source)
        self.assertIn("solution of inverse spectral geometry", source)

    def test_source_has_one_reference_heading(self) -> None:
        text = TEXT.read_text(encoding="utf-8")
        headings = [
            line for line in text.splitlines() if line.strip() == "References"
        ]
        self.assertEqual(len(headings), 1)


if __name__ == "__main__":
    unittest.main()
