#!/usr/bin/env python3
"""Regression tests for the P6 strict gear-contact release."""

from __future__ import annotations

import hashlib
import json
import math
import subprocess
import unittest
from fractions import Fraction
from pathlib import Path

import yaml
from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[3]
P6 = ROOT / "work/p6_gear_contact_v0_7"
PDF = P6 / "build/gear/gear_contact_geometry_v1_1.pdf"
TEX = P6 / "src/gear_contact_geometry_v1_1.tex"
TEXT = P6 / "checks/gear/gear_contact_geometry_v1_1.txt"
LOG = P6 / "build/gear/gear_contact_geometry_v1_1.log"
CONTRACT = P6 / "core/gear_contact_contract_v0_7.yaml"
REFERENCE_LEDGER = P6 / "ledgers/gear_contact_reference_ledger_v0_7.yaml"
CORPUS_LEDGER = P6 / "ledgers/corpus_ledgers_v0_7.yaml"
REFERENCE_LINT = P6 / "reports/Gear_Contact_Reference_Lint_Report_v0_7.json"
CORPUS_LINT = P6 / "reports/GO_Corpus_Lint_Report_v0_7.json"


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


def orbit(
    n1: int,
    n2: int,
    sigma: int,
    start: tuple[int, int] = (0, 0),
) -> list[tuple[int, int]]:
    state = (start[0] % n1, start[1] % n2)
    result: list[tuple[int, int]] = []
    seen: set[tuple[int, int]] = set()
    while state not in seen:
        seen.add(state)
        result.append(state)
        state = ((state[0] + 1) % n1, (state[1] + sigma) % n2)
    return result


def cycles(n1: int, n2: int, sigma: int) -> list[list[tuple[int, int]]]:
    unseen = {(i, j) for i in range(n1) for j in range(n2)}
    result: list[list[tuple[int, int]]] = []
    while unseen:
        start = min(unseen)
        component = orbit(n1, n2, sigma, start)
        result.append(component)
        unseen.difference_update(component)
    return result


def dot(a: tuple[float, ...], b: tuple[float, ...]) -> float:
    return sum(x * y for x, y in zip(a, b, strict=True))


def matvec(
    matrix: tuple[tuple[float, ...], ...],
    vector: tuple[float, ...],
) -> tuple[float, ...]:
    return tuple(dot(row, vector) for row in matrix)


def rotation_z(angle: float) -> tuple[tuple[float, ...], ...]:
    c, s = math.cos(angle), math.sin(angle)
    return ((c, -s, 0.0), (s, c, 0.0), (0.0, 0.0, 1.0))


def rk4_return(
    initial: float,
    *,
    sigma: int = -1,
    steps: int = 4000,
) -> float:
    """One driver turn for a positive periodic radius benchmark."""

    def rhs(theta1: float, theta2: float) -> float:
        r1 = 1.2 + 0.18 * math.cos(theta1)
        r2 = 1.7 + 0.11 * math.cos(theta2)
        return sigma * r1 / r2

    h = 2.0 * math.pi / steps
    x = 0.0
    y = initial
    for _ in range(steps):
        k1 = rhs(x, y)
        k2 = rhs(x + 0.5 * h, y + 0.5 * h * k1)
        k3 = rhs(x + 0.5 * h, y + 0.5 * h * k2)
        k4 = rhs(x + h, y + h * k3)
        y += h * (k1 + 2.0 * k2 + 2.0 * k3 + k4) / 6.0
        x += h
    return y


class FiniteContactTests(unittest.TestCase):
    def test_orbit_length_examples(self) -> None:
        self.assertEqual(len(orbit(12, 25, -1)), 300)
        self.assertEqual(len(orbit(12, 18, -1)), 36)

    def test_orbit_length_exhaustive(self) -> None:
        for n1 in range(1, 18):
            for n2 in range(1, 18):
                for sigma in (-1, 1):
                    self.assertEqual(
                        len(orbit(n1, n2, sigma)),
                        math.lcm(n1, n2),
                    )

    def test_cycle_count_exhaustive(self) -> None:
        for n1 in range(1, 14):
            for n2 in range(1, 14):
                for sigma in (-1, 1):
                    decomposition = cycles(n1, n2, sigma)
                    self.assertEqual(len(decomposition), math.gcd(n1, n2))
                    self.assertTrue(
                        all(
                            len(component) == math.lcm(n1, n2)
                            for component in decomposition
                        )
                    )

    def test_full_coverage_iff_coprime(self) -> None:
        for n1 in range(1, 20):
            for n2 in range(1, 20):
                full = len(orbit(n1, n2, -1)) == n1 * n2
                self.assertEqual(full, math.gcd(n1, n2) == 1)

    def test_orientation_reversal_conjugacy(self) -> None:
        n1, n2 = 7, 12
        for state in ((0, 0), (3, 8), (6, 11)):
            reflected = (state[0], (-state[1]) % n2)
            left_step = ((state[0] + 1) % n1, (state[1] - 1) % n2)
            reflected_left = (left_step[0], (-left_step[1]) % n2)
            right_step = (
                (reflected[0] + 1) % n1,
                (reflected[1] + 1) % n2,
            )
            self.assertEqual(reflected_left, right_step)

    def test_label_translation_commutes(self) -> None:
        n1, n2, sigma = 11, 15, -1
        shift = (4, 9)
        for state in ((0, 0), (3, 8), (10, 14)):
            translated = (
                (state[0] + shift[0]) % n1,
                (state[1] + shift[1]) % n2,
            )
            left = (
                (translated[0] + 1) % n1,
                (translated[1] + sigma) % n2,
            )
            stepped = (
                (state[0] + 1) % n1,
                (state[1] + sigma) % n2,
            )
            right = (
                (stepped[0] + shift[0]) % n1,
                (stepped[1] + shift[1]) % n2,
            )
            self.assertEqual(left, right)

    def test_ratio_fiber(self) -> None:
        u, v = 2, 3
        pairs = [(c * u, c * v) for c in range(1, 9)]
        for c, (n1, n2) in enumerate(pairs, start=1):
            self.assertEqual(Fraction(n1, n2), Fraction(u, v))
            self.assertEqual(math.gcd(n1, n2), c)
            self.assertEqual(math.lcm(n1, n2), c * u * v)

    def test_directed_ratio_sign(self) -> None:
        n1, n2 = 12, 25
        self.assertEqual(Fraction(-n1, n2), Fraction(-12, 25))
        self.assertEqual(Fraction(+n1, n2), Fraction(12, 25))

    def test_orbit_fraction(self) -> None:
        for n1, n2 in ((12, 25), (12, 18), (4, 6), (8, 20)):
            fraction = Fraction(math.lcm(n1, n2), n1 * n2)
            self.assertEqual(fraction, Fraction(1, math.gcd(n1, n2)))

    def test_full_orbit_entropy(self) -> None:
        n1, n2 = 12, 18
        states = orbit(n1, n2, -1)
        p = 1.0 / len(states)
        entropy = -sum(p * math.log2(p) for _ in states)
        self.assertAlmostEqual(entropy, math.log2(math.lcm(n1, n2)))

    def test_normalized_defect_base_invariance(self) -> None:
        n1, n2 = 12, 18
        natural = math.log(math.gcd(n1, n2)) / math.log(n1 * n2)
        binary = math.log2(math.gcd(n1, n2)) / math.log2(n1 * n2)
        decimal = math.log10(math.gcd(n1, n2)) / math.log10(n1 * n2)
        self.assertAlmostEqual(natural, binary, places=14)
        self.assertAlmostEqual(natural, decimal, places=14)

    def test_singleton_normalization_guard(self) -> None:
        n1 = n2 = 1
        self.assertEqual(n1 * n2, 1)
        with self.assertRaises(ZeroDivisionError):
            _ = math.log(math.gcd(n1, n2)) / math.log(n1 * n2)


class ContactMechanicsTests(unittest.TestCase):
    def test_complementarity_separated(self) -> None:
        gap, normal = 0.01, 0.0
        self.assertGreaterEqual(gap, 0.0)
        self.assertGreaterEqual(normal, 0.0)
        self.assertEqual(gap * normal, 0.0)

    def test_complementarity_active(self) -> None:
        gap, normal = 0.0, 1500.0
        self.assertGreaterEqual(gap, 0.0)
        self.assertGreaterEqual(normal, 0.0)
        self.assertEqual(gap * normal, 0.0)

    def test_friction_loss_sign(self) -> None:
        tangent_force = (-120.0, 0.0, 0.0)
        tangent_velocity = (2.5, 0.0, 0.0)
        loss = -dot(tangent_force, tangent_velocity)
        self.assertEqual(loss, 300.0)

    def test_zero_slip_zero_friction_power(self) -> None:
        tangent_force = (15.0, -4.0, 0.0)
        tangent_velocity = (0.0, 0.0, 0.0)
        self.assertEqual(-dot(tangent_force, tangent_velocity), 0.0)

    def test_ideal_reaction_power(self) -> None:
        n1, n2, sigma = 12.0, 18.0, -1.0
        omega1 = 3.0
        omega2 = sigma * n1 * omega1 / n2
        multiplier = 7.3
        power = multiplier * (n1 * omega1 - sigma * n2 * omega2)
        self.assertAlmostEqual(power, 0.0, places=13)

    def test_contact_power_is_coframed_rotation_invariant(self) -> None:
        rotation = rotation_z(0.73)
        force = (-120.0, 30.0, 5.0)
        velocity = (2.5, -0.4, 0.2)
        self.assertAlmostEqual(
            dot(matvec(rotation, force), matvec(rotation, velocity)),
            dot(force, velocity),
            places=12,
        )

    def test_normal_impulse_exposure(self) -> None:
        normal_force, duration = 800.0, 0.025
        self.assertAlmostEqual(normal_force * duration, 20.0)

    def test_dissipative_work(self) -> None:
        power, duration = 350.0, 4.0
        self.assertAlmostEqual(power * duration, 1400.0)

    def test_zero_total_exposure_is_undefined(self) -> None:
        weights = (0.0, 0.0, 0.0)
        with self.assertRaises(ZeroDivisionError):
            _ = weights[0] / sum(weights)

    def test_count_impulse_and_energy_are_distinct_channels(self) -> None:
        contract = load_yaml(CONTRACT)["exposure_channels"]
        dimensions = {
            contract["event_count"]["dimension"],
            contract["normal_impulse_exposure"]["dimension"],
            contract["dissipative_work"]["dimension"],
        }
        self.assertEqual(len(dimensions), 3)


class GearTrainTests(unittest.TestCase):
    def test_external_pair_ratio(self) -> None:
        self.assertEqual(Fraction(-12, 25), Fraction(-12, 25))

    def test_two_external_meshes_cancel_sign(self) -> None:
        n0, n1, n2 = 20, 35, 50
        ratio = Fraction(-n0, n1) * Fraction(-n1, n2)
        self.assertEqual(ratio, Fraction(n0, n2))

    def test_internal_mesh_preserves_sign(self) -> None:
        n1, n2 = 30, 78
        ratio = Fraction(+n1, n2)
        self.assertGreater(ratio, 0)

    def test_compatible_closed_loop_product(self) -> None:
        ratios = (Fraction(-2, 3), Fraction(-3, 5), Fraction(5, 2))
        product = math.prod(ratios)
        self.assertEqual(product, 1)

    def test_incompatible_closed_loop_rejects_nonzero_motion(self) -> None:
        ratios = (Fraction(-2, 3), Fraction(-3, 5), Fraction(-5, 2))
        self.assertNotEqual(math.prod(ratios), 1)


class PlanetaryFrameTests(unittest.TestCase):
    @staticmethod
    def action(
        rates: tuple[float, float, float],
        alpha: float,
    ) -> tuple[float, float, float]:
        return tuple(value - alpha for value in rates)

    @staticmethod
    def quotient(
        rates: tuple[float, float, float],
    ) -> tuple[float, float]:
        sun, ring, carrier = rates
        return (sun - carrier, ring - carrier)

    def test_group_identity(self) -> None:
        rates = (4.0, -1.0, 0.7)
        self.assertEqual(self.action(rates, 0.0), rates)

    def test_group_composition(self) -> None:
        rates = (4.0, -1.0, 0.7)
        lhs = self.action(self.action(rates, 1.2), -0.4)
        rhs = self.action(rates, 0.8)
        for actual, expected in zip(lhs, rhs, strict=True):
            self.assertAlmostEqual(actual, expected)

    def test_group_inverse(self) -> None:
        rates = (4.0, -1.0, 0.7)
        shifted = self.action(rates, 1.2)
        restored = self.action(shifted, -1.2)
        for actual, expected in zip(restored, rates, strict=True):
            self.assertAlmostEqual(actual, expected)

    def test_quotient_invariance(self) -> None:
        rates = (4.0, -1.0, 0.7)
        for alpha in (-3.0, 0.0, 2.4):
            actual = self.quotient(self.action(rates, alpha))
            expected = self.quotient(rates)
            for left, right in zip(actual, expected, strict=True):
                self.assertAlmostEqual(left, right, places=14)

    def test_quotient_fibers_are_uniform_shifts(self) -> None:
        first = (4.0, -1.0, 0.7)
        second = (6.5, 1.5, 3.2)
        for left, right in zip(
            self.quotient(first),
            self.quotient(second),
            strict=True,
        ):
            self.assertAlmostEqual(left, right, places=14)
        differences = tuple(b - a for a, b in zip(first, second, strict=True))
        self.assertEqual(differences, (2.5, 2.5, 2.5))

    def test_willis_residual(self) -> None:
        ns, nr = 30.0, 78.0
        omega_s, omega_r = 1.0, 0.0
        omega_c = ns * omega_s / (ns + nr)
        residual = ns * (omega_s - omega_c) + nr * (omega_r - omega_c)
        self.assertAlmostEqual(residual, 0.0, places=13)

    def test_fixed_ring_example(self) -> None:
        omega_c = Fraction(30, 30 + 78)
        self.assertEqual(omega_c, Fraction(5, 18))
        self.assertAlmostEqual(float(omega_c), 0.2777777777777778)

    def test_equal_module_geometry_compatibility(self) -> None:
        ns, np = 30, 24
        self.assertEqual(ns + 2 * np, 78)

    def test_absolute_carrier_encoder_is_not_quotient_invariant(self) -> None:
        rates = (4.0, -1.0, 0.7)
        shifted = self.action(rates, 2.0)
        self.assertNotEqual(rates[2], shifted[2])


class NonCircularReturnTests(unittest.TestCase):
    def test_constant_radius_return_lift(self) -> None:
        ratio, sigma, x = Fraction(2, 5), -1, 0.7
        returned = x + 2.0 * math.pi * sigma * float(ratio)
        expected = x - 0.8 * math.pi
        self.assertAlmostEqual(returned, expected)

    def test_constant_rotation_lift_property(self) -> None:
        rho, x = -0.37, 1.3
        lift = lambda value: value + 2.0 * math.pi * rho
        self.assertAlmostEqual(lift(x + 2.0 * math.pi), lift(x) + 2.0 * math.pi)

    def test_constant_rotation_iterates(self) -> None:
        rho, x, n = -0.37, 1.3, 41
        iterate = x + n * 2.0 * math.pi * rho
        estimate = (iterate - x) / (2.0 * math.pi * n)
        self.assertAlmostEqual(estimate, rho, places=14)

    def test_lift_integer_shift(self) -> None:
        rho, integer = -0.37, 3
        self.assertAlmostEqual((rho + integer) - rho, integer)

    def test_rotation_number_mod_one_is_lift_independent(self) -> None:
        rho = -0.37
        for integer in (-4, -1, 0, 2, 7):
            self.assertAlmostEqual((rho + integer) % 1.0, rho % 1.0)

    def test_variable_radius_flow_preserves_order(self) -> None:
        first = rk4_return(0.3)
        second = rk4_return(1.1)
        self.assertLess(first, second)

    def test_variable_radius_return_is_degree_one(self) -> None:
        x = 0.7
        first = rk4_return(x)
        shifted = rk4_return(x + 2.0 * math.pi)
        self.assertAlmostEqual(shifted, first + 2.0 * math.pi, places=9)


class ReleaseContractTests(unittest.TestCase):
    def test_contract_schema(self) -> None:
        contract = load_yaml(CONTRACT)
        self.assertEqual(contract["schema"]["id"], "go-gear-contact-contract")
        self.assertEqual(contract["schema"]["version"], "0.7.0")
        self.assertEqual(
            contract["schema"]["mechanics_contract"],
            "go-frame-force-dissipation-contract@0.6.0",
        )

    def test_contract_event_safeguards(self) -> None:
        contract = load_yaml(CONTRACT)
        prohibitions = contract["finite_event_model"]["prohibition"]
        self.assertIn(
            "pitch_event_state_is_not_simultaneous_active_contact_set",
            prohibitions,
        )
        self.assertIn("event_count_is_not_wear", prohibitions)

    def test_reference_lint_summary(self) -> None:
        summary = load_json(REFERENCE_LINT)["summary"]
        self.assertEqual(summary["canonical_documents"], 1)
        self.assertEqual(summary["reference_documents"], 1)
        self.assertEqual(summary["expressions_checked"], 20)
        self.assertEqual(summary["findings_total"], 0)
        self.assertEqual(summary["status_counts"], {"PASS": 1})

    def test_corpus_lint_summary(self) -> None:
        summary = load_json(CORPUS_LINT)["summary"]
        self.assertEqual(summary["canonical_documents"], 18)
        self.assertEqual(summary["reference_documents"], 13)
        self.assertEqual(summary["critical_adapters"], 5)
        self.assertEqual(summary["expressions_checked"], 151)
        self.assertEqual(summary["status_counts"], {"FAIL": 5, "PASS": 13})

    def test_supersession(self) -> None:
        corpus = load_yaml(CORPUS_LEDGER)
        ids = {item["id"] for item in corpus["documents"]}
        self.assertNotIn("gear-contact-v1", ids)
        self.assertIn("gear-contact-v1-1", ids)
        targets = {
            item.get("canonical_document")
            for item in corpus["duplicate_or_superseded_sources"]
        }
        self.assertIn("gear-contact-v1-1", targets)

    def test_pdf_metadata(self) -> None:
        reader = PdfReader(PDF)
        self.assertEqual(len(reader.pages), 9)
        self.assertEqual(
            (reader.metadata or {}).get("/Title"),
            "Gear Contact Geometry as a Typed Finite Observation System",
        )

    def test_required_source_fragments(self) -> None:
        source = TEX.read_text(encoding="utf-8")
        for fragment in (
            r"\section{Finite pitch-event dynamics}",
            r"\section{Planetary frames as an explicit group action}",
            r"\section{Periodic non-circular kinematics}",
            r"P_{\rm fric}",
            r"\widetilde F(x+2\pi)=\widetilde F(x)+2\pi",
        ):
            self.assertIn(fragment, source)

    def test_latex_log_is_clean(self) -> None:
        log = LOG.read_text(encoding="utf-8", errors="replace")
        for pattern in (
            "Overfull",
            "Underfull",
            "LaTeX Warning",
            "undefined references",
            "multiply defined",
            "Fatal error",
            "Missing character",
        ):
            self.assertNotIn(pattern, log)

    def test_fonts_are_embedded(self) -> None:
        process = subprocess.run(
            ["pdffonts", str(PDF)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(process.returncode, 0)
        rows = [
            line.split()
            for line in process.stdout.splitlines()[2:]
            if line.strip()
        ]
        self.assertTrue(rows)
        self.assertTrue(all(len(row) >= 6 and row[-4].lower() == "yes" for row in rows))

    def test_bibliography_heading_is_unique(self) -> None:
        extracted = TEXT.read_text(encoding="utf-8", errors="replace")
        count = sum(line.strip() == "References" for line in extracted.splitlines())
        self.assertEqual(count, 1)
        self.assertNotIn(r"\section*{References}", TEX.read_text(encoding="utf-8"))

    def test_pdf_checksum_matches_reference_ledger(self) -> None:
        ledger = load_yaml(REFERENCE_LEDGER)
        expected = ledger["documents"][0]["source"]["sha256"]
        self.assertEqual(sha256(PDF), expected)

    def test_no_prohibited_tokens(self) -> None:
        for path in (TEX, TEXT):
            content = path.read_text(encoding="utf-8", errors="replace")
            for token in ("TODO", "TBD", "\ufffd"):
                self.assertNotIn(token, content)


if __name__ == "__main__":
    unittest.main()
