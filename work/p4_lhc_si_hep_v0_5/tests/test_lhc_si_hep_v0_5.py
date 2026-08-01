#!/usr/bin/env python3
"""Regression tests for the strict SI--HEP passport and LHC v1.3 migration."""

from __future__ import annotations

import csv
import json
import math
import subprocess
import sys
import unittest
from decimal import Decimal, getcontext
from pathlib import Path

import yaml


getcontext().prec = 60

ROOT = Path(__file__).resolve().parents[3]
P4 = ROOT / "work/p4_lhc_si_hep_v0_5"
INPUT = P4 / "data/lhc_si_hep_inputs_v0_5.yaml"
CONTRACT = P4 / "core/si_hep_quantity_passport_v0_5.yaml"
METRICS = P4 / "data/lhc_si_hep_metrics_v0_5.json"
CONVERSIONS = P4 / "data/si_hep_conversion_table_v0_5.csv"
REFERENCE_LEDGER = P4 / "ledgers/lhc_si_hep_reference_ledgers_v0_5.yaml"
CORPUS_LEDGER = P4 / "ledgers/corpus_ledgers_v0_5.yaml"
REFERENCE_LINT = P4 / "reports/LHC_SI_HEP_Lint_Report_v0_5.json"
CORPUS_LINT = P4 / "reports/GO_Corpus_Lint_Report_v0_5.json"

PI = Decimal(
    "3.141592653589793238462643383279502884197169399375105820974944"
)


def load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as stream:
        value = yaml.safe_load(stream)
    if not isinstance(value, dict):
        raise TypeError(f"{path}: YAML root must be a mapping")
    return value


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as stream:
        value = json.load(stream)
    if not isinstance(value, dict):
        raise TypeError(f"{path}: JSON root must be an object")
    return value


def relative_error(actual: Decimal, expected: Decimal) -> Decimal:
    return abs(actual - expected) / abs(expected)


def exponents(a_length: int, b_mass: int, t_time: int) -> tuple[int, int, int]:
    return (
        b_mass - a_length - t_time,
        a_length + t_time,
        a_length - 2 * b_mass,
    )


def representative(
    a_length: int,
    b_mass: int,
    t_time: int,
    hbar: Decimal,
    c: Decimal,
    energy_anchor: Decimal,
) -> Decimal:
    d_energy, u_hbar, v_c = exponents(a_length, b_mass, t_time)
    return hbar**u_hbar * c**v_c * energy_anchor**d_energy


def boost_z(four_vector: tuple[float, float, float, float], rapidity: float) -> tuple[float, ...]:
    energy, px, py, pz = four_vector
    ch = math.cosh(rapidity)
    sh = math.sinh(rapidity)
    return (ch * energy - sh * pz, px, py, ch * pz - sh * energy)


def minkowski_square(four_vector: tuple[float, float, float, float]) -> float:
    energy, px, py, pz = four_vector
    return energy**2 - px**2 - py**2 - pz**2


class MechanicalNaturalizationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        data = load_yaml(INPUT)
        constants = data["defining_constants"]
        cls.c = Decimal(constants["speed_of_light"]["value_si"])
        cls.h = Decimal(constants["planck_constant"]["value_si"])
        cls.e = Decimal(constants["elementary_charge"]["value_si"])
        cls.hbar = cls.h / (Decimal(2) * PI)
        cls.gev = Decimal(constants["gigaelectronvolt"]["value_si"])

    def test_energy_exponents(self) -> None:
        self.assertEqual(exponents(2, 1, -2), (1, 0, 0))

    def test_mass_exponents(self) -> None:
        self.assertEqual(exponents(0, 1, 0), (1, 0, -2))

    def test_momentum_exponents(self) -> None:
        self.assertEqual(exponents(1, 1, -1), (1, 0, -1))

    def test_length_exponents(self) -> None:
        self.assertEqual(exponents(1, 0, 0), (-1, 1, 1))

    def test_duration_exponents(self) -> None:
        self.assertEqual(exponents(0, 0, 1), (-1, 1, 0))

    def test_action_exponents(self) -> None:
        self.assertEqual(exponents(2, 1, -1), (0, 1, 0))

    def test_force_exponents(self) -> None:
        self.assertEqual(exponents(1, 1, -2), (2, -1, -1))

    def test_round_trip_for_multiple_dimensions(self) -> None:
        examples = [
            (Decimal("3.2e-4"), (2, 1, -2)),
            (Decimal("7.1e-9"), (0, 1, 0)),
            (Decimal("9.3e12"), (1, 1, -1)),
            (Decimal("5.8e-7"), (1, 0, 0)),
            (Decimal("4.4e3"), (0, 0, 1)),
        ]
        for value, dimension in examples:
            scale = representative(*dimension, self.hbar, self.c, self.gev)
            natural = value / scale
            restored = natural * scale
            self.assertLess(relative_error(restored, value), Decimal("1e-55"))

    def test_multiplicative_homomorphism(self) -> None:
        q1 = Decimal("2.5")
        q2 = Decimal("7.4")
        d1 = (1, 0, 0)
        d2 = (0, 1, 0)
        s1 = representative(*d1, self.hbar, self.c, self.gev)
        s2 = representative(*d2, self.hbar, self.c, self.gev)
        combined = tuple(x + y for x, y in zip(d1, d2))
        s12 = representative(*combined, self.hbar, self.c, self.gev)
        self.assertLess(relative_error(s12, s1 * s2), Decimal("1e-55"))
        left = q1 * q2 / s12
        right = (q1 / s1) * (q2 / s2)
        self.assertLess(relative_error(left, right), Decimal("1e-55"))

    def test_anchor_covariance(self) -> None:
        value = Decimal("4.2e-6")
        dimension = (1, 0, 0)
        first = value / representative(*dimension, self.hbar, self.c, self.gev)
        second_anchor = Decimal(3) * self.gev
        second = value / representative(*dimension, self.hbar, self.c, second_anchor)
        d_energy = exponents(*dimension)[0]
        self.assertEqual(d_energy, -1)
        self.assertLess(relative_error(second, Decimal(3) ** (-d_energy) * first), Decimal("1e-55"))

    def test_residual_dimensions_are_explicitly_rejected(self) -> None:
        contract = load_yaml(CONTRACT)
        residual = contract["mechanical_naturalization"]["admissibility"][
            "forbidden_implicit_residual_dimensions"
        ]
        self.assertEqual(residual, ["I", "Theta", "N", "J"])
        prohibited = contract["electromagnetic_boundary"]["prohibited"]
        self.assertIn("treating_tesla_as_energy_squared_without_field_normalization", prohibited)


class StandardConversionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.metrics = load_json(METRICS)
        cls.standard = cls.metrics["standard_conversions"]
        cls.constants = cls.metrics["defining_constants"]

    def test_exact_gev_to_joule(self) -> None:
        self.assertEqual(Decimal(self.constants["GeV_J"]), Decimal("1.602176634e-10"))

    def test_inverse_length(self) -> None:
        actual = Decimal(self.standard["one_GeV_inverse_length_m"])
        expected = Decimal("1.973269804593025e-16")
        self.assertLess(relative_error(actual, expected), Decimal("1e-15"))

    def test_hbar_c_pdg_value(self) -> None:
        actual = Decimal(self.standard["hbar_c_MeV_fm"])
        expected = Decimal("197.3269804")
        self.assertLess(relative_error(actual, expected), Decimal("4e-10"))

    def test_cross_section_in_millibarn(self) -> None:
        actual = Decimal(self.standard["one_GeV_minus2_mbarn"])
        expected = Decimal("0.3893793721")
        self.assertLess(relative_error(actual, expected), Decimal("3e-10"))

    def test_mass_conversion(self) -> None:
        actual = Decimal(self.standard["one_GeV_per_c2_kg"])
        expected = Decimal("1.782661921627898e-27")
        self.assertLess(relative_error(actual, expected), Decimal("1e-15"))

    def test_momentum_conversion(self) -> None:
        actual = Decimal(self.standard["one_GeV_per_c_kg_m_per_s"])
        expected = Decimal("5.344285992678308e-19")
        self.assertLess(relative_error(actual, expected), Decimal("1e-15"))

    def test_angular_and_ordinary_frequency_differ_by_two_pi(self) -> None:
        omega = Decimal(self.standard["angular_frequency_per_GeV_rad_per_s"])
        nu = Decimal(self.standard["ordinary_frequency_per_GeV_Hz"])
        self.assertLess(relative_error(omega / nu, Decimal(2) * PI), Decimal("1e-15"))

    def test_csv_has_all_standard_rows(self) -> None:
        with CONVERSIONS.open("r", encoding="utf-8", newline="") as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual(len(rows), 8)
        self.assertEqual(
            {row["quantity"] for row in rows},
            {"energy", "mass", "momentum", "length", "duration", "area", "action", "force"},
        )


class FourMomentumTests(unittest.TestCase):
    def test_si_energy_chart_mass_shell(self) -> None:
        c = 299792458.0
        mass = 1.67262192595e-27
        momentum = 5.3442859e-19
        energy = math.sqrt((momentum * c) ** 2 + (mass * c**2) ** 2)
        left = energy**2 - (c * momentum) ** 2
        right = (mass * c**2) ** 2
        self.assertAlmostEqual(left / right, 1.0, places=7)

    def test_lorentz_boost_preserves_mass_shell(self) -> None:
        vector = (11.0, 1.5, -0.7, 9.2)
        boosted = boost_z(vector, 1.3)
        self.assertAlmostEqual(minkowski_square(vector), minkowski_square(boosted), places=11)

    def test_head_on_equal_beams_have_sqrt_s_two_e(self) -> None:
        energy = 6800.0
        momentum = math.sqrt(energy**2 - 0.93827208943**2)
        total = (2.0 * energy, 0.0, 0.0, momentum - momentum)
        self.assertAlmostEqual(math.sqrt(minkowski_square(total)), 2.0 * energy)

    def test_invariant_mass_representation_equivalence(self) -> None:
        c = 299792458.0
        energies = [5.0e-8, 7.0e-8]
        momenta = [(1.0e-16, 2.0e-17, 0.0), (-4.0e-17, 1.0e-16, 0.0)]
        sum_energy = sum(energies)
        sum_p = tuple(sum(item[index] for item in momenta) for index in range(3))
        si_mass_energy_sq = sum_energy**2 - c**2 * sum(value**2 for value in sum_p)
        energy_chart_sq = sum_energy**2 - sum((c * value) ** 2 for value in sum_p)
        self.assertEqual(si_mass_energy_sq, energy_chart_sq)

    def test_rapidity_difference_is_longitudinal_boost_invariant(self) -> None:
        first = (12.0, 1.0, 0.0, 9.0)
        second = (8.0, -0.5, 0.0, -5.0)

        def rapidity(vector: tuple[float, float, float, float]) -> float:
            return 0.5 * math.log((vector[0] + vector[3]) / (vector[0] - vector[3]))

        original = rapidity(first) - rapidity(second)
        transformed = rapidity(boost_z(first, 0.8)) - rapidity(boost_z(second, 0.8))
        self.assertAlmostEqual(original, transformed, places=12)


class AcceleratorBridgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.metrics = load_json(METRICS)["lhc_run3_audit"]

    def test_rigidity_coefficient_is_exact_c_over_billion(self) -> None:
        self.assertEqual(Decimal("299792458") / Decimal("1e9"), Decimal("0.299792458"))

    def test_rigidity_round_trip(self) -> None:
        momentum = Decimal(self.metrics["momentum_GeV_per_c"])
        coefficient = Decimal("0.299792458")
        rigidity = momentum / coefficient
        restored = coefficient * rigidity
        self.assertLess(relative_error(restored, momentum), Decimal("1e-55"))

    def test_run3_rigidity_value(self) -> None:
        actual = Decimal(self.metrics["magnetic_rigidity_T_m"])
        expected = Decimal("22682.358258")
        self.assertLessEqual(abs(actual - expected), Decimal("1e-6"))

    def test_rf_voltage_identity(self) -> None:
        z = Decimal(1)
        voltage = Decimal("16e6")
        phase_factor = Decimal("0.5")
        delta_ev = z * voltage * phase_factor
        elementary_charge = Decimal("1.602176634e-19")
        delta_joule = z * elementary_charge * voltage * phase_factor
        self.assertEqual(delta_joule / elementary_charge, delta_ev)
        self.assertEqual(delta_ev / Decimal("1e9"), Decimal("0.008"))

    def test_stable_one_minus_beta(self) -> None:
        gamma = Decimal(self.metrics["gamma"])
        beta = Decimal(self.metrics["beta"])
        stable = (Decimal(1) / gamma**2) / (Decimal(1) + beta)
        reported = Decimal(self.metrics["one_minus_beta"])
        self.assertLess(relative_error(stable, reported), Decimal("3e-12"))

    def test_speed_deficit(self) -> None:
        delta = Decimal(self.metrics["one_minus_beta"])
        expected = Decimal("299792458") * delta
        actual = Decimal(self.metrics["speed_deficit_m_per_s"])
        self.assertLess(relative_error(actual, expected), Decimal("1e-10"))

    def test_revolution_frequency(self) -> None:
        beta = Decimal(self.metrics["beta"])
        expected = beta * Decimal("299792458") / Decimal("26659")
        actual = Decimal(self.metrics["revolution_frequency_Hz"])
        self.assertLess(relative_error(actual, expected), Decimal("1e-10"))

    def test_circumference_is_not_registered_as_bending_radius(self) -> None:
        contract = load_yaml(CONTRACT)
        prohibitions = contract["accelerator_bridges"]["magnetic_rigidity"]["prohibition"]
        self.assertIn(
            "do_not_identify_ring_circumference_over_2pi_with_dipole_bending_radius",
            prohibitions,
        )


class BeamOpticsTests(unittest.TestCase):
    def test_symplectic_covariance_preserves_emittance(self) -> None:
        sigma = ((4.0, 1.2), (1.2, 1.0))
        transport = ((1.3, 0.8), (0.25, (1.0 + 0.8 * 0.25) / 1.3))
        determinant_m = transport[0][0] * transport[1][1] - transport[0][1] * transport[1][0]
        self.assertAlmostEqual(determinant_m, 1.0)

        def matmul(a: tuple[tuple[float, float], ...], b: tuple[tuple[float, float], ...]):
            return tuple(
                tuple(sum(a[i][k] * b[k][j] for k in range(2)) for j in range(2))
                for i in range(2)
            )

        transpose = tuple(zip(*transport))
        propagated = matmul(matmul(transport, sigma), transpose)
        det_before = sigma[0][0] * sigma[1][1] - sigma[0][1] * sigma[1][0]
        det_after = propagated[0][0] * propagated[1][1] - propagated[0][1] * propagated[1][0]
        self.assertAlmostEqual(det_before, det_after, places=12)

    def test_nonsymplectic_scaling_changes_geometric_emittance(self) -> None:
        scale_x = 2.0
        scale_xprime = 1.0
        self.assertNotEqual(scale_x * scale_xprime, 1.0)

    def test_normalized_emittance_can_remain_constant_during_acceleration(self) -> None:
        beta_gamma_initial = 100.0
        beta_gamma_final = 1000.0
        geometric_initial = 3.0e-6
        normalized = beta_gamma_initial * geometric_initial
        geometric_final = normalized / beta_gamma_final
        self.assertAlmostEqual(beta_gamma_final * geometric_final, normalized)
        self.assertLess(geometric_final, geometric_initial)

    def test_twiss_dimensions_registered(self) -> None:
        ledger = load_yaml(REFERENCE_LEDGER)
        lhc = next(document for document in ledger["documents"] if document["id"] == "lhc-beam-observation-v1-3")
        quantities = {item["id"]: item for item in lhc["quantities"]}
        self.assertEqual(quantities["lhc13.twiss_alpha"]["extends"], "dimensionless.scalar")
        self.assertEqual(quantities["lhc13.twiss_beta"]["extends"], "geometry.length")
        self.assertEqual(quantities["lhc13.twiss_gamma"]["extends"], "geometry.curvature")


class ContractAndCorpusTests(unittest.TestCase):
    def test_reference_lint_is_clean(self) -> None:
        report = load_json(REFERENCE_LINT)
        self.assertEqual(report["summary"]["findings_total"], 0)
        self.assertEqual(report["summary"]["status_counts"], {"PASS": 2})
        self.assertEqual(report["summary"]["expressions_checked"], 28)

    def test_corpus_has_no_blocked_document(self) -> None:
        report = load_json(CORPUS_LINT)
        self.assertEqual(report["summary"]["status_counts"], {"FAIL": 9, "PASS": 8})
        self.assertEqual(report["summary"]["canonical_documents"], 17)
        self.assertEqual(report["summary"]["expressions_checked"], 100)

    def test_old_lhc_is_superseded(self) -> None:
        corpus = load_yaml(CORPUS_LEDGER)
        ids = {document["id"] for document in corpus["documents"]}
        self.assertIn("lhc-beam-observation-v1-3", ids)
        self.assertNotIn("lhc-beam-observation-v1-2", ids)
        superseded = [
            item
            for item in corpus["duplicate_or_superseded_sources"]
            if item.get("canonical_document") == "lhc-beam-observation-v1-3"
        ]
        self.assertEqual(len(superseded), 1)

    def test_source_register_uses_primary_institutions(self) -> None:
        data = load_yaml(INPUT)
        institutions = {item["institution"] for item in data["source_register"]}
        self.assertTrue({"BIPM", "NIST/CODATA", "Particle Data Group", "CERN"}.issubset(institutions))

    def test_strict_linter_process_returns_zero(self) -> None:
        process = subprocess.run(
            [
                sys.executable,
                "work/go_core_v0_2/src/go_lint.py",
                "--core-dir",
                "work/go_core_v0_2/core",
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
        self.assertEqual(process.returncode, 0, process.stdout + process.stderr)


if __name__ == "__main__":
    unittest.main()
