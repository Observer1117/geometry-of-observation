#!/usr/bin/env python3
"""Regression tests for the strict Planck-to-cosmos P3 migration."""

from __future__ import annotations

import csv
import json
import math
import subprocess
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[3]
P3 = ROOT / "work/p3_planck_cosmos_v0_4"
INPUT = P3 / "data/planck_cosmos_inputs_v0_4.yaml"
CSV_PATH = P3 / "data/planck_cosmos_landmarks_v0_4.csv"
METRICS = P3 / "data/planck_cosmos_metrics_v0_4.json"
CONTRACT = P3 / "core/planck_cosmos_scale_contract_v0_4.yaml"
LEDGER = P3 / "ledgers/planck_cosmos_reference_ledger_v0_4.yaml"
CORPUS_LEDGER = P3 / "ledgers/corpus_ledgers_v0_4.yaml"
LINT_JSON = P3 / "reports/Planck_Cosmos_Lint_Report_v0_4.json"
CORPUS_REPORT = P3 / "reports/GO_Corpus_Lint_Report_v0_4.json"


def load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as stream:
        data = yaml.safe_load(stream)
    if not isinstance(data, dict):
        raise TypeError(f"{path}: YAML root is not a mapping")
    return data


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as stream:
        data = json.load(stream)
    if not isinstance(data, dict):
        raise TypeError(f"{path}: JSON root is not an object")
    return data


def chart(
    values: tuple[float, float, float],
    anchors: tuple[float, float, float],
    base: float,
) -> tuple[float, float, float]:
    if base <= 1:
        raise ValueError("base must be greater than one")
    if any(value <= 0 for value in values + anchors):
        raise ValueError("values and anchors must be positive")
    return tuple(math.log(value / anchor, base) for value, anchor in zip(values, anchors))


def inverse_chart(
    coordinates: tuple[float, float, float],
    anchors: tuple[float, float, float],
    base: float,
) -> tuple[float, float, float]:
    return tuple(anchor * base**coordinate for coordinate, anchor in zip(coordinates, anchors))


def diagonal_distance(
    left: tuple[float, float, float],
    right: tuple[float, float, float],
    weights: tuple[float, float, float],
) -> float:
    return math.sqrt(
        sum(
            weight * (x_value - y_value) ** 2
            for x_value, y_value, weight in zip(left, right, weights)
        )
    )


class LogarithmicChartTests(unittest.TestCase):
    def setUp(self) -> None:
        data = load_yaml(INPUT)
        anchors = data["planck_anchors"]
        self.anchors = (
            float(anchors["planck_length"]["value_si"]),
            float(anchors["planck_mass"]["value_si"]),
            float(anchors["planck_time"]["value_si"]),
        )

    def test_chart_inverse_round_trip(self) -> None:
        values = (2.3e-7, 7.1e4, 9.2e12)
        coordinates = chart(values, self.anchors, 10.0)
        recovered = inverse_chart(coordinates, self.anchors, 10.0)
        for actual, expected in zip(recovered, values):
            self.assertAlmostEqual(actual / expected, 1.0, places=13)

    def test_coherent_unit_change_is_invariant(self) -> None:
        values = (3.2e-9, 5.4, 7.6e-3)
        factors = (100.0, 1000.0, 1e6)
        original = chart(values, self.anchors, 10.0)
        converted = chart(
            tuple(value * factor for value, factor in zip(values, factors)),
            tuple(anchor * factor for anchor, factor in zip(self.anchors, factors)),
            10.0,
        )
        for first, second in zip(original, converted):
            self.assertAlmostEqual(first, second)

    def test_anchor_change_is_translation(self) -> None:
        values = (4.2e-8, 2.0e9, 3.0e2)
        new_anchors = tuple(anchor * factor for anchor, factor in zip(self.anchors, (3, 5, 7)))
        old = chart(values, self.anchors, 10.0)
        new = chart(values, new_anchors, 10.0)
        for index, factor in enumerate((3, 5, 7)):
            self.assertAlmostEqual(new[index], old[index] - math.log10(factor))

    def test_base_change_is_scalar(self) -> None:
        values = (4.2e-8, 2.0e9, 3.0e2)
        decades = chart(values, self.anchors, 10.0)
        octaves = chart(values, self.anchors, 2.0)
        factor = math.log(10.0) / math.log(2.0)
        for decade, octave in zip(decades, octaves):
            self.assertAlmostEqual(octave, factor * decade)

    def test_weighted_distance_is_anchor_independent(self) -> None:
        values_a = (1e-5, 2e3, 4e-2)
        values_b = (3e-7, 5e5, 7e4)
        weights = (1.0, 2.0, 0.5)
        first = diagonal_distance(
            chart(values_a, self.anchors, 10.0),
            chart(values_b, self.anchors, 10.0),
            weights,
        )
        shifted_anchors = tuple(anchor * factor for anchor, factor in zip(self.anchors, (11, 13, 17)))
        second = diagonal_distance(
            chart(values_a, shifted_anchors, 10.0),
            chart(values_b, shifted_anchors, 10.0),
            weights,
        )
        self.assertAlmostEqual(first, second)

    def test_weight_matrix_base_covariance(self) -> None:
        values_a = (1e-5, 2e3, 4e-2)
        values_b = (3e-7, 5e5, 7e4)
        weights_10 = (1.0, 2.0, 0.5)
        distance_10 = diagonal_distance(
            chart(values_a, self.anchors, 10.0),
            chart(values_b, self.anchors, 10.0),
            weights_10,
        )
        weight_factor = (math.log(2.0) / math.log(10.0)) ** 2
        weights_2 = tuple(weight * weight_factor for weight in weights_10)
        distance_2 = diagonal_distance(
            chart(values_a, self.anchors, 2.0),
            chart(values_b, self.anchors, 2.0),
            weights_2,
        )
        self.assertAlmostEqual(distance_10, distance_2)

    def test_resolution_margin_is_anchor_independent(self) -> None:
        scale = 2.5e-6
        resolution = 4.0e-9
        direct = math.log10(scale / resolution)
        first = math.log10(scale / self.anchors[0]) - math.log10(resolution / self.anchors[0])
        alternate_anchor = 7.0e-4
        second = math.log10(scale / alternate_anchor) - math.log10(resolution / alternate_anchor)
        self.assertAlmostEqual(direct, first)
        self.assertAlmostEqual(direct, second)

    def test_monomial_log_linearization(self) -> None:
        q = (2.0, 3.0, 5.0)
        q_ref = (7.0, 11.0, 13.0)
        exponents = (2.0, -1.0, 0.5)
        constant = 17.0
        value = constant * math.prod(item**power for item, power in zip(q, exponents))
        reference = constant * math.prod(
            item**power for item, power in zip(q_ref, exponents)
        )
        left = math.log10(value / reference)
        right = sum(
            power * math.log10(item / anchor)
            for item, anchor, power in zip(q, q_ref, exponents)
        )
        self.assertAlmostEqual(left, right)


class PhysicalConstraintTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.data = load_yaml(INPUT)
        cls.metrics = load_json(METRICS)
        cls.constants = cls.data["defining_constants"]
        cls.anchors = cls.data["planck_anchors"]
        cls.c = float(cls.constants["speed_of_light"]["value_si"])
        cls.h = float(cls.constants["planck_constant"]["value_si"])
        cls.hbar = cls.h / (2.0 * math.pi)
        cls.G = float(cls.constants["gravitational_constant"]["value_si"])
        cls.ell_p = float(cls.anchors["planck_length"]["value_si"])
        cls.m_p = float(cls.anchors["planck_mass"]["value_si"])
        cls.t_p = float(cls.anchors["planck_time"]["value_si"])

    def test_planck_length_formula_within_three_standard_uncertainties(self) -> None:
        computed = math.sqrt(self.hbar * self.G / self.c**3)
        uncertainty = float(self.anchors["planck_length"]["standard_uncertainty_si"])
        self.assertLessEqual(abs(computed - self.ell_p), 3.0 * uncertainty)

    def test_planck_mass_formula_within_three_standard_uncertainties(self) -> None:
        computed = math.sqrt(self.hbar * self.c / self.G)
        uncertainty = float(self.anchors["planck_mass"]["standard_uncertainty_si"])
        self.assertLessEqual(abs(computed - self.m_p), 3.0 * uncertainty)

    def test_planck_time_formula_within_three_standard_uncertainties(self) -> None:
        computed = math.sqrt(self.hbar * self.G / self.c**5)
        uncertainty = float(self.anchors["planck_time"]["standard_uncertainty_si"])
        self.assertLessEqual(abs(computed - self.t_p), 3.0 * uncertainty)

    def test_planck_speed_identity(self) -> None:
        relative_error = abs(self.ell_p / self.t_p - self.c) / self.c
        self.assertLess(relative_error, 2e-7)

    def test_planck_action_identity(self) -> None:
        relative_error = abs(self.ell_p * self.m_p * self.c - self.hbar) / self.hbar
        self.assertLess(relative_error, 2e-7)

    def test_causal_pair_lies_in_log_half_space(self) -> None:
        duration = 4.0
        length = 0.3 * self.c * duration
        chi_length = math.log10(length / self.ell_p)
        chi_time = math.log10(duration / self.t_p)
        self.assertLessEqual(chi_length, chi_time)

    def test_reduced_compton_plane(self) -> None:
        mass = 2.7e-20
        compton = self.hbar / (mass * self.c)
        chi_length = math.log10(compton / self.ell_p)
        chi_mass = math.log10(mass / self.m_p)
        self.assertAlmostEqual(chi_length, -chi_mass, places=6)

    def test_schwarzschild_affine_plane(self) -> None:
        mass = 8.1e21
        radius = 2.0 * self.G * mass / self.c**2
        chi_length = math.log10(radius / self.ell_p)
        chi_mass = math.log10(mass / self.m_p)
        self.assertAlmostEqual(chi_length, chi_mass + math.log10(2.0), places=6)

    def test_energy_and_mass_coordinates_coincide(self) -> None:
        mass = 3.4e-12
        energy = mass * self.c**2
        planck_energy = self.m_p * self.c**2
        self.assertAlmostEqual(
            math.log10(energy / planck_energy),
            math.log10(mass / self.m_p),
        )

    def test_density_coordinate_is_mu_minus_three_s(self) -> None:
        mass = 2.0e6
        length = 7.0e-3
        density = mass / length**3
        planck_density = self.m_p / self.ell_p**3
        left = math.log10(density / planck_density)
        right = math.log10(mass / self.m_p) - 3.0 * math.log10(length / self.ell_p)
        self.assertAlmostEqual(left, right)

    def test_light_year_and_julian_year_coordinates_match(self) -> None:
        conversions = self.data["unit_conversions"]
        length_coordinate = math.log10(
            float(conversions["light_year"]["value_si"]) / self.ell_p
        )
        time_coordinate = math.log10(
            float(conversions["Julian_year"]["value_si"]) / self.t_p
        )
        self.assertAlmostEqual(length_coordinate, time_coordinate, places=6)

    def test_correlated_ratio_uncertainty_can_cancel(self) -> None:
        relative_standard_uncertainty = 0.02
        relative_variance = relative_standard_uncertainty**2
        covariance_term = relative_variance
        ratio_variance = (
            relative_variance + relative_variance - 2.0 * covariance_term
        ) / math.log(10.0) ** 2
        self.assertAlmostEqual(ratio_variance, 0.0)


class CatalogueAndContractTests(unittest.TestCase):
    def test_generated_catalogue_has_twenty_four_rows(self) -> None:
        with CSV_PATH.open("r", encoding="utf-8", newline="") as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual(len(rows), 24)
        self.assertEqual({row["axis"] for row in rows}, {"length", "mass", "time"})

    def test_every_catalogue_coordinate_recomputes(self) -> None:
        data = load_yaml(INPUT)
        anchors = {
            "length": float(data["planck_anchors"]["planck_length"]["value_si"]),
            "mass": float(data["planck_anchors"]["planck_mass"]["value_si"]),
            "time": float(data["planck_anchors"]["planck_time"]["value_si"]),
        }
        with CSV_PATH.open("r", encoding="utf-8", newline="") as stream:
            for row in csv.DictReader(stream):
                expected = math.log10(float(row["value_si"]) / anchors[row["axis"]])
                self.assertAlmostEqual(
                    float(row["planck_log10_coordinate"]), expected, places=13
                )

    def test_cosmic_mass_landmarks_are_not_one_quantity(self) -> None:
        cosmic = load_json(METRICS)["cosmology_landmark"]
        baryonic = cosmic["cosmic_baryonic_mass_equivalent"]
        matter = cosmic["cosmic_matter_mass_equivalent"]
        total = cosmic["cosmic_total_energy_mass_equivalent"]
        self.assertLess(baryonic, matter)
        self.assertLess(matter, total)
        self.assertGreater(total / baryonic, 10.0)

    def test_legacy_sixty_decade_similarity_is_not_exact(self) -> None:
        cosmic = load_json(METRICS)["cosmology_landmark"]
        spans = [
            cosmic["length_legacy_span_decades"],
            cosmic["time_age_span_decades"],
            cosmic["baryonic_mass_span_decades"],
            cosmic["matter_mass_span_decades"],
            cosmic["total_energy_mass_span_decades"],
        ]
        self.assertGreater(max(spans) - min(spans), 1.0)
        self.assertGreater(cosmic["total_energy_mass_span_decades"], 62.0)

    def test_contract_has_required_layers(self) -> None:
        contract = load_yaml(CONTRACT)
        required = {
            "axes",
            "descriptor_chart",
            "protocol_resolution_chart",
            "resolution_margin",
            "transformation_laws",
            "logarithmic_metric",
            "monomial_algebra",
            "planck_anchor_identities",
            "physical_constraint_surfaces",
            "uncertainty",
            "cosmological_landmarks",
            "observation_trace",
            "claim_firewalls",
            "migration",
        }
        self.assertTrue(required.issubset(contract))

    def test_axis_dimension_vectors_are_typed(self) -> None:
        contract = load_yaml(CONTRACT)
        self.assertEqual(contract["axes"]["length"]["quantity_dimension"], [1, 0, 0, 0, 0, 0, 0])
        self.assertEqual(contract["axes"]["mass"]["quantity_dimension"], [0, 1, 0, 0, 0, 0, 0])
        self.assertEqual(contract["axes"]["time"]["quantity_dimension"], [0, 0, 1, 0, 0, 0, 0])

    def test_reference_ledger_is_complete(self) -> None:
        ledger = load_yaml(LEDGER)
        document = ledger["documents"][0]
        self.assertEqual(document["ledger_level"], "reference")
        self.assertEqual(document["migration_status"], "p3_reference_pass")
        self.assertEqual(len(document["expressions"]), 19)
        self.assertEqual(len(document["protocol_fields_present"]), 15)
        self.assertNotIn("PENDING", document["source"]["sha256"])

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
        report = load_json(LINT_JSON)
        self.assertEqual(report["summary"]["findings_total"], 0)
        self.assertEqual(report["summary"]["status_counts"], {"PASS": 1})
        self.assertEqual(report["summary"]["expressions_checked"], 19)

    def test_corpus_status_advanced_by_one_reference(self) -> None:
        corpus = load_yaml(CORPUS_LEDGER)
        self.assertEqual(len(corpus["documents"]), 17)
        self.assertEqual(
            sum(document["ledger_level"] == "reference" for document in corpus["documents"]),
            7,
        )
        report = load_json(CORPUS_REPORT)
        self.assertEqual(
            report["summary"]["status_counts"],
            {"BLOCKED": 1, "FAIL": 9, "PASS": 7},
        )


if __name__ == "__main__":
    unittest.main()
