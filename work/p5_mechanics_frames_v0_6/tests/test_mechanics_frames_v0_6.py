#!/usr/bin/env python3
"""Regression tests for the P5 frames, forces, and dissipation release."""

from __future__ import annotations

import cmath
import hashlib
import json
import math
import subprocess
import sys
import unittest
from pathlib import Path

import yaml
from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[3]
P5 = ROOT / "work/p5_mechanics_frames_v0_6"
CONTRACT = P5 / "core/frame_force_dissipation_contract_v0_6.yaml"
REFERENCE_LEDGER = P5 / "ledgers/mechanics_reference_ledgers_v0_6.yaml"
CORPUS_LEDGER = P5 / "ledgers/corpus_ledgers_v0_6.yaml"
REFERENCE_LINT = P5 / "reports/Mechanics_Reference_Lint_Report_v0_6.json"
CORPUS_LINT = P5 / "reports/GO_Corpus_Lint_Report_v0_6.json"


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


def dot(a: tuple[float, ...], b: tuple[float, ...]) -> float:
    return sum(x * y for x, y in zip(a, b, strict=True))


def cross(
    a: tuple[float, float, float], b: tuple[float, float, float]
) -> tuple[float, float, float]:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def norm(a: tuple[float, ...]) -> float:
    return math.sqrt(dot(a, a))


def matvec(
    matrix: tuple[tuple[float, ...], ...], vector: tuple[float, ...]
) -> tuple[float, ...]:
    return tuple(dot(row, vector) for row in matrix)


class FrameInterfaceTests(unittest.TestCase):
    def test_rotation_inverse_and_composition(self) -> None:
        angle = 0.37
        c, s = math.cos(angle), math.sin(angle)
        rotation = ((c, -s, 0.0), (s, c, 0.0), (0.0, 0.0, 1.0))
        transpose = tuple(zip(*rotation))
        vector = (1.3, -0.7, 2.0)
        restored = matvec(transpose, matvec(rotation, vector))
        for actual, expected in zip(restored, vector, strict=True):
            self.assertAlmostEqual(actual, expected, places=12)

    def test_affine_point_map_uses_translation(self) -> None:
        origin = (10.0, -3.0, 2.0)
        rotation = ((0.0, -1.0, 0.0), (1.0, 0.0, 0.0), (0.0, 0.0, 1.0))
        local_point = (2.0, 1.0, -1.0)
        mapped = matvec(rotation, local_point)
        point = tuple(a + b for a, b in zip(origin, mapped, strict=True))
        self.assertEqual(point, (9.0, -1.0, 1.0))

    def test_free_vector_map_has_no_translation(self) -> None:
        rotation = ((0.0, -1.0, 0.0), (1.0, 0.0, 0.0), (0.0, 0.0, 1.0))
        self.assertEqual(matvec(rotation, (2.0, 1.0, -1.0)), (-1.0, 2.0, -1.0))

    def test_uniform_rotation_centripetal_acceleration(self) -> None:
        omega = (0.0, 0.0, 3.0)
        x = (2.0, 0.0, 0.0)
        acceleration = cross(omega, cross(omega, x))
        self.assertEqual(acceleration, (-18.0, 0.0, 0.0))

    def test_coriolis_factor_is_two(self) -> None:
        omega = (0.0, 0.0, 2.0)
        velocity = (1.0, 0.0, 0.0)
        value = tuple(2.0 * item for item in cross(omega, velocity))
        self.assertEqual(value, (0.0, 4.0, 0.0))

    def test_power_is_orthogonally_invariant(self) -> None:
        rotation = ((0.0, -1.0, 0.0), (1.0, 0.0, 0.0), (0.0, 0.0, 1.0))
        force = (4.0, -2.0, 1.0)
        velocity = (3.0, 5.0, -1.0)
        self.assertAlmostEqual(
            dot(matvec(rotation, force), matvec(rotation, velocity)),
            dot(force, velocity),
        )

    def test_mass_form_is_positive_semidefinite(self) -> None:
        jacobians = ((1.0, 0.0), (0.0, 2.0), (1.0, 1.0))
        masses = (2.0, 1.0, 3.0)
        g00 = sum(m * j[0] * j[0] for m, j in zip(masses, jacobians, strict=True))
        g01 = sum(m * j[0] * j[1] for m, j in zip(masses, jacobians, strict=True))
        g11 = sum(m * j[1] * j[1] for m, j in zip(masses, jacobians, strict=True))
        self.assertGreater(g00, 0.0)
        self.assertGreater(g11, 0.0)
        self.assertGreater(g00 * g11 - g01 * g01, 0.0)

    def test_redundant_realization_gives_degenerate_mass_form(self) -> None:
        jacobians = ((1.0, 1.0), (2.0, 2.0))
        masses = (1.0, 3.0)
        g00 = sum(m * j[0] * j[0] for m, j in zip(masses, jacobians, strict=True))
        g01 = sum(m * j[0] * j[1] for m, j in zip(masses, jacobians, strict=True))
        g11 = sum(m * j[1] * j[1] for m, j in zip(masses, jacobians, strict=True))
        self.assertAlmostEqual(g00 * g11 - g01 * g01, 0.0)

    def test_rayleigh_dissipation_is_nonnegative(self) -> None:
        qdot = (2.0, -1.0)
        c = ((3.0, 0.5), (0.5, 2.0))
        cq = matvec(c, qdot)
        rayleigh = 0.5 * dot(qdot, cq)
        self.assertGreaterEqual(2.0 * rayleigh, 0.0)
        self.assertAlmostEqual(-dot(tuple(-x for x in cq), qdot), 2.0 * rayleigh)

    def test_rheonomous_constraint_can_exchange_power(self) -> None:
        multiplier = 7.0
        partial_t_h = -0.4
        constraint_power = -multiplier * partial_t_h
        self.assertAlmostEqual(constraint_power, 2.8)

    def test_guarded_zero_capacity_utilization(self) -> None:
        capacity = 0.0
        tangent_force = 0.0
        utilization = 0.0 if capacity == 0.0 and tangent_force == 0.0 else math.inf
        self.assertEqual(utilization, 0.0)


class FoucaultTests(unittest.TestCase):
    def test_normal_spin_is_rotation_invariant(self) -> None:
        omega = (1.0, 2.0, 3.0)
        normal = (0.0, 0.0, 1.0)
        rotation = ((0.0, -1.0, 0.0), (1.0, 0.0, 0.0), (0.0, 0.0, 1.0))
        self.assertAlmostEqual(
            dot(matvec(rotation, omega), matvec(rotation, normal)),
            dot(omega, normal),
        )

    def test_spherical_latitude_projection(self) -> None:
        omega = 7.2921150e-5
        self.assertAlmostEqual(omega * math.sin(0.0), 0.0)
        self.assertAlmostEqual(omega * math.sin(math.pi / 2.0), omega)

    def test_exact_reduced_solution_satisfies_ode(self) -> None:
        omega_0 = 2.3
        omega_n = 0.17
        omega_c = math.sqrt(omega_0**2 + omega_n**2)
        t = 0.71
        phase = cmath.exp(-1j * omega_n * t)
        z = phase * math.cos(omega_c * t)
        zdot = phase * (
            -1j * omega_n * math.cos(omega_c * t)
            - omega_c * math.sin(omega_c * t)
        )
        zddot = phase * (
            -(omega_n**2 + omega_c**2) * math.cos(omega_c * t)
            + 2j * omega_n * omega_c * math.sin(omega_c * t)
        )
        residual = zddot + 2j * omega_n * zdot + omega_0**2 * z
        self.assertAlmostEqual(abs(residual), 0.0, places=12)

    def test_precession_sign_follows_orientation(self) -> None:
        omega_n = 0.3
        delta_t = 0.2
        plane_phase = cmath.exp(-1j * omega_n * delta_t)
        self.assertAlmostEqual(cmath.phase(plane_phase) / delta_t, -omega_n)

    def test_coriolis_term_does_no_work(self) -> None:
        velocity = (1.2, -0.7, 0.0)
        j_velocity = (0.7, 1.2, 0.0)
        self.assertAlmostEqual(dot(velocity, j_velocity), 0.0)

    def test_damping_loss_is_nonnegative(self) -> None:
        mass, beta = 4.0, 0.08
        velocity = (1.2, -0.7)
        loss = 2.0 * mass * beta * dot(velocity, velocity)
        self.assertGreaterEqual(loss, 0.0)

    def test_nominal_precession_periods(self) -> None:
        omega = 7.2921150e-5
        pole_hours = 2.0 * math.pi / omega / 3600.0
        mid_hours = 2.0 * math.pi / (omega / math.sqrt(2.0)) / 3600.0
        self.assertAlmostEqual(pole_hours, 23.9344696, places=5)
        self.assertAlmostEqual(mid_hours, 33.8484555, places=5)

    def test_endpoint_frame_sum(self) -> None:
        center = (100.0, 0.0, 0.0)
        attitude = ((0.0, -1.0, 0.0), (1.0, 0.0, 0.0), (0.0, 0.0, 1.0))
        site_plus_local = (2.0, 1.0, 0.5)
        mapped = matvec(attitude, site_plus_local)
        endpoint = tuple(a + b for a, b in zip(center, mapped, strict=True))
        self.assertEqual(endpoint, (99.0, 2.0, 0.5))

    def test_rotating_observer_shifts_frequency(self) -> None:
        signal_frequency = 5.0
        observer_frequency = 1.25
        t = 0.43
        transformed = cmath.exp(-1j * observer_frequency * t) * cmath.exp(
            1j * signal_frequency * t
        )
        expected = cmath.exp(1j * (signal_frequency - observer_frequency) * t)
        self.assertAlmostEqual(abs(transformed - expected), 0.0, places=12)

    def test_periodic_torus_condition(self) -> None:
        omega = (2.0, 3.0, 5.0)
        period = 2.0 * math.pi
        cycles = tuple(period * item / (2.0 * math.pi) for item in omega)
        self.assertTrue(all(abs(x - round(x)) < 1e-12 for x in cycles))


class BobsleighTests(unittest.TestCase):
    def test_contact_complementarity(self) -> None:
        separated = (0.02, 0.0)
        active = (0.0, 1500.0)
        for gap, normal in (separated, active):
            self.assertGreaterEqual(gap, 0.0)
            self.assertGreaterEqual(normal, 0.0)
            self.assertAlmostEqual(gap * normal, 0.0)

    def test_friction_cone(self) -> None:
        mu, normal, tangent = 0.12, 1200.0, 110.0
        self.assertLessEqual(tangent, mu * normal)

    def test_friction_power_sign(self) -> None:
        tangential_force = (-100.0, 0.0, 0.0)
        relative_velocity = (2.0, 0.0, 0.0)
        loss = -dot(tangential_force, relative_velocity)
        self.assertEqual(loss, 200.0)

    def test_energy_decreases_under_friction_only(self) -> None:
        initial_energy = 1000.0
        loss_power = 40.0
        duration = 3.0
        final_energy = initial_energy - loss_power * duration
        self.assertLess(final_energy, initial_energy)

    def test_cone_utilization_positive_capacity(self) -> None:
        tangent, mu, normal = 60.0, 0.1, 1000.0
        utilization = tangent / (mu * normal)
        self.assertAlmostEqual(utilization, 0.6)
        self.assertAlmostEqual(1.0 - utilization, 0.4)

    def test_load_entropy_base_invariance(self) -> None:
        probabilities = (0.1, 0.2, 0.3, 0.4)
        h_e = -sum(p * math.log(p) for p in probabilities)
        h_2 = -sum(p * math.log2(p) for p in probabilities)
        normalized_e = h_e / math.log(len(probabilities))
        normalized_2 = h_2 / math.log2(len(probabilities))
        self.assertAlmostEqual(normalized_e, normalized_2, places=12)

    def test_load_entropy_requires_positive_total(self) -> None:
        loads = (0.0, 0.0)
        self.assertEqual(sum(loads), 0.0)
        with self.assertRaises(ZeroDivisionError):
            _ = loads[0] / sum(loads)

    def test_two_runner_imbalance_range(self) -> None:
        left, right = 800.0, 1200.0
        imbalance = abs(right - left) / (right + left)
        self.assertGreaterEqual(imbalance, 0.0)
        self.assertLessEqual(imbalance, 1.0)

    def test_curvature_demand(self) -> None:
        speed, curvature = 30.0, 0.025
        self.assertAlmostEqual(speed**2 * curvature, 22.5)

    def test_mass_distribution_changes_inertia(self) -> None:
        masses = (1.0, 1.0)
        compact = ((-1.0, 0.0), (1.0, 0.0))
        spread = ((-2.0, 0.0), (2.0, 0.0))
        inertia_compact = sum(
            m * (x * x + y * y)
            for m, (x, y) in zip(masses, compact, strict=True)
        )
        inertia_spread = sum(
            m * (x * x + y * y)
            for m, (x, y) in zip(masses, spread, strict=True)
        )
        self.assertGreater(inertia_spread, inertia_compact)


class RollerCoasterTests(unittest.TestCase):
    def test_circle_acceleration_magnitude(self) -> None:
        radius, speed = 20.0, 15.0
        self.assertAlmostEqual(speed**2 / radius, 11.25)

    def test_frame_angular_velocity_dimensionally_matches(self) -> None:
        speed, frame_strain = 12.0, 0.04
        angular_velocity = speed * frame_strain
        self.assertAlmostEqual(angular_velocity, 0.48)

    def test_load_norm_is_roll_invariant(self) -> None:
        specific_force = (3.0, 4.0, 12.0)
        angle = 0.8
        c, s = math.cos(angle), math.sin(angle)
        roll = ((1.0, 0.0, 0.0), (0.0, c, -s), (0.0, s, c))
        self.assertAlmostEqual(norm(matvec(roll, specific_force)), norm(specific_force))

    def test_vector_and_norm_are_distinct_types(self) -> None:
        vector = (0.2, -1.1, 2.3)
        scalar = norm(vector)
        self.assertIsInstance(vector, tuple)
        self.assertIsInstance(scalar, float)

    def test_body_jerk_rotation_correction(self) -> None:
        omega = (0.0, 0.0, 2.0)
        body_force = (3.0, 0.0, 0.0)
        mapped_inertial_derivative = (0.0, 0.0, 0.0)
        correction = cross(omega, body_force)
        body_derivative = tuple(
            a - b
            for a, b in zip(mapped_inertial_derivative, correction, strict=True)
        )
        self.assertEqual(body_derivative, (0.0, -6.0, 0.0))

    def test_offset_regularity_sufficient_bound(self) -> None:
        radius, gauge = 10.0, 1.2
        ratio = 0.5 * gauge / radius
        self.assertLess(ratio, 1.0)

    def test_concentric_circle_rail_lengths(self) -> None:
        radius, gauge = 10.0, 1.2
        plus = 2.0 * math.pi * (radius + gauge / 2.0)
        minus = 2.0 * math.pi * (radius - gauge / 2.0)
        self.assertAlmostEqual(plus - minus, 2.0 * math.pi * gauge)

    def test_rail_swap_sign_law(self) -> None:
        plus, minus = 70.0, 62.0
        signed = plus - minus
        swapped = minus - plus
        self.assertEqual(swapped, -signed)
        self.assertEqual(abs(swapped), abs(signed))

    def test_ideal_wheel_count_is_dimensionless(self) -> None:
        rail_length, wheel_radius = 100.0, 0.25
        count = rail_length / (2.0 * math.pi * wheel_radius)
        self.assertAlmostEqual(count, 200.0 / math.pi)

    def test_dissipative_force_power(self) -> None:
        force = (-300.0, 0.0, 0.0)
        velocity = (20.0, 0.0, 0.0)
        self.assertEqual(-dot(force, velocity), 6000.0)

    def test_scalar_load_forgets_roll(self) -> None:
        acceleration_minus_gravity = (2.0, 3.0, 9.0)
        self.assertAlmostEqual(
            norm(acceleration_minus_gravity),
            norm((2.0, -9.0, 3.0)),
        )


class ContractAndCorpusTests(unittest.TestCase):
    def test_contract_version_and_sign(self) -> None:
        contract = load_yaml(CONTRACT)
        self.assertEqual(contract["schema"]["version"], "0.6.0")
        self.assertIn(
            "P_diss = -pairing(Q_d,qdot) >= 0",
            contract["dissipation_convention"]["generalized"]["nonnegative_loss"],
        )

    def test_reference_lint_is_clean(self) -> None:
        summary = load_json(REFERENCE_LINT)["summary"]
        self.assertEqual(summary["canonical_documents"], 4)
        self.assertEqual(summary["expressions_checked"], 39)
        self.assertEqual(summary["findings_total"], 0)
        self.assertEqual(summary["status_counts"], {"PASS": 4})

    def test_corpus_statuses(self) -> None:
        summary = load_json(CORPUS_LINT)["summary"]
        self.assertEqual(summary["canonical_documents"], 18)
        self.assertEqual(summary["reference_documents"], 12)
        self.assertEqual(summary["expressions_checked"], 132)
        self.assertEqual(summary["status_counts"], {"FAIL": 6, "PASS": 12})

    def test_old_mechanics_adapters_are_superseded(self) -> None:
        corpus = load_yaml(CORPUS_LEDGER)
        ids = {item["id"] for item in corpus["documents"]}
        self.assertFalse(
            {
                "celestial-foucault-networks-v1",
                "bobsleigh-contact-v1",
                "roller-coaster-v1",
            }
            & ids
        )
        self.assertTrue(
            {
                "frames-forces-dissipation-interface-v0-1",
                "celestial-foucault-networks-v1-1",
                "bobsleigh-contact-v1-1",
                "roller-coaster-v1-1",
            }.issubset(ids)
        )

    def test_pdf_hashes_match_reference_ledger(self) -> None:
        ledger = load_yaml(REFERENCE_LEDGER)
        for document in ledger["documents"]:
            path = ROOT / document["source"]["pdf"]
            self.assertEqual(sha256(path), document["source"]["sha256"])

    def test_pdf_metadata_and_pages(self) -> None:
        ledger = load_yaml(REFERENCE_LEDGER)
        expected_titles = {
            "frames-forces-dissipation-interface-v0-1":
                "Frames, Forces, Constraints, and Dissipation under Observation Maps",
            "celestial-foucault-networks-v1-1":
                "Foucault Networks on Celestial Bodies as Typed Observation Geometry",
            "bobsleigh-contact-v1-1":
                "Bobsleigh Contact Geometry as a Typed Observation System",
            "roller-coaster-v1-1":
                "Roller-Coaster Geometry as a Typed Observation Laboratory",
        }
        for document in ledger["documents"]:
            reader = PdfReader(ROOT / document["source"]["pdf"])
            self.assertEqual(len(reader.pages), document["source"]["pages"])
            self.assertEqual(reader.metadata.get("/Title"), expected_titles[document["id"]])

    def test_reference_strict_linter_returns_zero(self) -> None:
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

    def test_full_corpus_strict_linter_fails_open_findings(self) -> None:
        process = subprocess.run(
            [
                sys.executable,
                "work/go_core_v0_2/src/go_lint.py",
                "--core-dir",
                "work/go_core_v0_2/core",
                "--ledger",
                str(CORPUS_LEDGER),
                "--mode",
                "strict",
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(process.returncode, 1)


if __name__ == "__main__":
    unittest.main()
