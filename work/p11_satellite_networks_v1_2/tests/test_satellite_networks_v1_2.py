#!/usr/bin/env python3
"""Independent regressions for the P11 satellite-network release."""

from __future__ import annotations

import csv
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
P11 = ROOT / "work/p11_satellite_networks_v1_2"
sys.path.insert(0, str(P11 / "scripts"))

from generate_satellite_network_benchmarks import (  # noqa: E402
    C_LIGHT,
    DAY,
    MU_E,
    ORBITS,
    R_E,
    centered_gram,
    circular_clock_offset,
    coframe,
    connected_components,
    distance_matrix,
    earliest_arrival,
    kepler_state,
    laplacian_spectrum,
    link_adjacency,
    mean_motion,
    network_state,
    observer_rotation,
    orbit_period,
    retarded_time_static,
    segment_clearance,
    shannon_entropy,
    solve_kepler,
    weak_clock_rate,
)


PDF = P11 / "build/satellite/satellite_networks_typed_frames_v1_2.pdf"
TEX = P11 / "src/satellite_networks_typed_frames_v1_2.tex"
TEXT = P11 / "checks/satellite/satellite_networks_typed_frames_v1_2.txt"
LOG = P11 / "build/satellite/satellite_networks_typed_frames_v1_2.log"
CONTRACT = P11 / "core/satellite_networks_observation_contract_v1_2.yaml"
REFERENCE_LEDGER = P11 / "ledgers/satellite_networks_reference_ledger_v1_2.yaml"
CORPUS_LEDGER = P11 / "ledgers/corpus_ledgers_v1_2.yaml"
REFERENCE_LINT = P11 / "reports/Satellite_Networks_Reference_Lint_Report_v1_2.json"
CORPUS_LINT = P11 / "reports/GO_Corpus_Lint_Report_v1_2.json"
BENCHMARKS = P11 / "data/satellite_networks_benchmarks_v1_2.csv"
METRICS = P11 / "data/satellite_networks_metrics_v1_2.json"


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


class KeplerModelTests(unittest.TestCase):
    def test_reference_network_has_six_labeled_orbits(self) -> None:
        self.assertEqual(len(ORBITS), 6)
        self.assertEqual(len({orbit.name for orbit in ORBITS}), 6)

    def test_kepler_solver_residual_on_grid(self) -> None:
        for eccentricity in (0.0, 0.1, 0.65, 0.9):
            for mean_anomaly in np.linspace(-math.pi, math.pi, 17):
                eccentric_anomaly = solve_kepler(mean_anomaly, eccentricity)
                residual = (
                    eccentric_anomaly
                    - eccentricity * math.sin(eccentric_anomaly)
                    - mean_anomaly
                )
                self.assertAlmostEqual(residual, 0.0, delta=4e-15)

    def test_kepler_solver_rejects_nonelliptic_eccentricity(self) -> None:
        for value in (-0.1, 1.0, 1.2):
            with self.assertRaises(ValueError):
                solve_kepler(0.0, value)

    def test_mean_motion_and_period_are_reciprocal(self) -> None:
        for orbit in ORBITS:
            self.assertAlmostEqual(
                mean_motion(orbit.a) * orbit_period(orbit.a),
                2.0 * math.pi,
                delta=2e-15,
            )

    def test_mean_motion_rejects_nonpositive_axis(self) -> None:
        for value in (0.0, -1.0):
            with self.assertRaises(ValueError):
                mean_motion(value)

    def test_orbital_state_has_correct_shapes(self) -> None:
        position, velocity = kepler_state(ORBITS[0], 1234.5)
        self.assertEqual(position.shape, (3,))
        self.assertEqual(velocity.shape, (3,))
        self.assertTrue(np.isfinite(position).all())
        self.assertTrue(np.isfinite(velocity).all())

    def test_network_state_has_label_preserving_shapes(self) -> None:
        positions, velocities = network_state(456.0)
        self.assertEqual(positions.shape, (6, 3))
        self.assertEqual(velocities.shape, (6, 3))

    def test_two_body_specific_energy_matches_semimajor_axis(self) -> None:
        for orbit in ORBITS:
            for time in (0.0, 1000.0, DAY):
                position, velocity = kepler_state(orbit, time)
                energy = 0.5 * float(velocity @ velocity) - MU_E / float(
                    np.linalg.norm(position)
                )
                expected = -MU_E / (2.0 * orbit.a)
                self.assertAlmostEqual(
                    energy,
                    expected,
                    delta=2e-8 * abs(expected),
                )

    def test_two_body_angular_momentum_is_constant(self) -> None:
        for orbit in ORBITS:
            initial = kepler_state(orbit, 0.0)
            reference = float(np.linalg.norm(np.cross(*initial)))
            for time in (777.0, 10_000.0, DAY):
                state = kepler_state(orbit, time)
                computed = float(np.linalg.norm(np.cross(*state)))
                self.assertAlmostEqual(
                    computed,
                    reference,
                    delta=2e-12 * reference,
                )


class FrameAndDistanceTests(unittest.TestCase):
    def test_observer_rotation_is_special_orthogonal(self) -> None:
        for time in np.linspace(0.0, DAY, 11):
            rotation = observer_rotation(float(time))
            np.testing.assert_allclose(
                rotation.T @ rotation,
                np.eye(3),
                atol=2e-15,
            )
            self.assertAlmostEqual(np.linalg.det(rotation), 1.0, delta=2e-15)

    def test_distance_matrix_is_symmetric_with_zero_diagonal(self) -> None:
        positions, _ = network_state(4000.0)
        distances = distance_matrix(positions)
        np.testing.assert_allclose(distances, distances.T, atol=0.0)
        np.testing.assert_allclose(np.diag(distances), 0.0, atol=0.0)

    def test_distance_matrix_rejects_nonmatrix_points(self) -> None:
        with self.assertRaises(ValueError):
            distance_matrix(np.ones(3))

    def test_time_dependent_rigid_frame_preserves_distances(self) -> None:
        for time in np.linspace(0.0, DAY, 9):
            positions, _ = network_state(float(time))
            transformed, _ = coframe(positions, np.zeros(3), float(time))
            np.testing.assert_allclose(
                distance_matrix(transformed),
                distance_matrix(positions),
                atol=3e-6,
                rtol=0.0,
            )

    def test_common_translation_cancels_exactly_at_normal_scale(self) -> None:
        points = np.array(((1.0, 2.0, 3.0), (-4.0, 5.0, 2.0)))
        shift = np.array((8.0, -3.0, 1.0))
        self.assertEqual(
            float(np.linalg.norm((points[0] + shift) - (points[1] + shift))),
            float(np.linalg.norm(points[0] - points[1])),
        )

    def test_frame_transform_is_not_a_lossy_sensor_map(self) -> None:
        maps = load_yaml(CONTRACT)["observation_maps"]
        frame = next(item for item in maps if item["id"] == "rigid_frame_change")
        self.assertEqual(frame["kind"], "frame_transform")
        self.assertEqual(frame["invertibility"], "required")
        self.assertFalse(frame["information_loss"])

    def test_time_dependent_rotation_changes_coordinate_velocity(self) -> None:
        point = np.array((7_000_000.0, 0.0, 0.0))
        delta = 0.01
        first, _ = coframe(point[None, :], np.zeros(3), 0.0)
        second, _ = coframe(point[None, :], np.zeros(3), delta)
        coordinate_velocity = (second[0] - first[0]) / delta
        self.assertGreater(float(np.linalg.norm(coordinate_velocity)), 1.0)

    def test_stationary_point_can_acquire_circle_closure(self) -> None:
        samples = np.array(
            [
                (math.cos(time), math.sin(time), 0.0)
                for time in np.linspace(0.0, 2.0 * math.pi, 65)
            ]
        )
        radii = np.linalg.norm(samples, axis=1)
        np.testing.assert_allclose(radii, 1.0, atol=2e-15)
        self.assertGreater(np.linalg.matrix_rank(samples), 1)


class EuclideanDistanceMatrixTests(unittest.TestCase):
    def test_centered_Gram_matches_centered_coordinates(self) -> None:
        positions, _ = network_state(2345.0)
        centered = positions - positions.mean(axis=0, keepdims=True)
        expected = centered @ centered.T
        computed = centered_gram(distance_matrix(positions))
        np.testing.assert_allclose(
            computed,
            expected,
            atol=25.0,
            rtol=2e-14,
        )

    def test_centered_Gram_is_positive_semidefinite_to_roundoff(self) -> None:
        positions, _ = network_state(400.0)
        eigenvalues = np.linalg.eigvalsh(
            centered_gram(distance_matrix(positions))
        )
        scale = float(np.max(np.abs(eigenvalues)))
        self.assertGreaterEqual(float(eigenvalues.min()), -2e-15 * scale)

    def test_centered_Gram_rank_is_at_most_three(self) -> None:
        positions, _ = network_state(9000.0)
        eigenvalues = np.linalg.eigvalsh(
            centered_gram(distance_matrix(positions))
        )
        threshold = 1e-11 * float(eigenvalues.max())
        self.assertLessEqual(int(np.count_nonzero(eigenvalues > threshold)), 3)

    def test_centered_Gram_rejects_nonsquare_input(self) -> None:
        with self.assertRaises(ValueError):
            centered_gram(np.ones((2, 3)))

    def test_reflection_preserves_distance_matrix(self) -> None:
        points = np.array(
            ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))
        )
        reflected = points @ np.diag((-1.0, 1.0, 1.0))
        np.testing.assert_allclose(
            distance_matrix(points),
            distance_matrix(reflected),
            atol=0.0,
        )

    def test_reflection_reverses_oriented_volume(self) -> None:
        points = np.array(
            ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))
        )
        reflected = points @ np.diag((-1.0, 1.0, 1.0))

        def volume(data: np.ndarray) -> float:
            return float(
                np.linalg.det(
                    np.stack((data[1] - data[0], data[2] - data[0], data[3] - data[0]))
                )
                / 6.0
            )

        self.assertAlmostEqual(volume(reflected), -volume(points), delta=0.0)


class SamplingAndSignalTests(unittest.TestCase):
    def test_uniform_sampling_alias_is_exact_to_roundoff(self) -> None:
        delta = 37.0
        omega = 0.071
        shifted = omega + 2.0 * math.pi * 3 / delta
        first = np.exp(1j * omega * np.arange(128) * delta)
        second = np.exp(1j * shifted * np.arange(128) * delta)
        np.testing.assert_allclose(first, second, atol=1e-12, rtol=0.0)

    def test_nonuniform_sample_breaks_the_uniform_alias(self) -> None:
        delta = 37.0
        omega = 0.071
        shifted = omega + 2.0 * math.pi / delta
        times = np.arange(32) * delta
        times[7] += 0.25
        difference = np.max(
            np.abs(np.exp(1j * omega * times) - np.exp(1j * shifted * times))
        )
        self.assertGreater(float(difference), 0.01)

    def test_finite_support_is_finite_not_a_continuum(self) -> None:
        samples = np.exp(1j * math.sqrt(2.0) * np.arange(32))
        self.assertEqual(len(set(samples.tolist())), 32)
        self.assertLess(len(samples), 100)

    def test_static_retarded_time_satisfies_light_time_equation(self) -> None:
        source = np.array((26_560_000.0, 0.0, 0.0))
        reception = 1000.0
        emission = retarded_time_static(reception, source, np.zeros(3))
        residual = reception - emission - np.linalg.norm(source) / C_LIGHT
        self.assertAlmostEqual(float(residual), 0.0, delta=1e-13)

    def test_bearing_channel_loses_range(self) -> None:
        first = np.array((1.0, 2.0, 3.0))
        second = 7.0 * first
        np.testing.assert_allclose(
            first / np.linalg.norm(first),
            second / np.linalg.norm(second),
            atol=2e-16,
        )
        self.assertNotEqual(float(np.linalg.norm(first)), float(np.linalg.norm(second)))


class LineOfSightAndGraphTests(unittest.TestCase):
    def test_diameter_through_Earth_is_blocked(self) -> None:
        left = np.array((2.0 * R_E, 0.0, 0.0))
        right = np.array((-2.0 * R_E, 0.0, 0.0))
        self.assertAlmostEqual(segment_clearance(left, right), 0.0, delta=0.0)

    def test_high_parallel_chord_is_clear(self) -> None:
        height = 2.0 * R_E
        left = np.array((-R_E, height, 0.0))
        right = np.array((R_E, height, 0.0))
        self.assertAlmostEqual(
            segment_clearance(left, right),
            height,
            delta=1e-9,
        )

    def test_tangent_policy_is_strictly_blocked(self) -> None:
        left = np.array((-R_E, R_E, 0.0))
        right = np.array((R_E, R_E, 0.0))
        clearance = segment_clearance(left, right)
        self.assertAlmostEqual(clearance, R_E, delta=1e-9)
        self.assertFalse(clearance > R_E)

    def test_degenerate_segment_clearance_is_point_radius(self) -> None:
        point = np.array((7_000_000.0, 0.0, 0.0))
        self.assertEqual(segment_clearance(point, point), 7_000_000.0)

    def test_segment_clearance_is_frame_invariant(self) -> None:
        positions, _ = network_state(5000.0)
        transformed, transformed_center = coframe(
            positions,
            np.zeros(3),
            5000.0,
        )
        for left in range(6):
            for right in range(left + 1, 6):
                self.assertAlmostEqual(
                    segment_clearance(positions[left], positions[right]),
                    segment_clearance(
                        transformed[left],
                        transformed[right],
                        transformed_center,
                    ),
                    delta=3e-6,
                )

    def test_adjacency_is_symmetric_and_loop_free(self) -> None:
        positions, _ = network_state(3000.0)
        adjacency = link_adjacency(positions)
        np.testing.assert_array_equal(adjacency, adjacency.T)
        np.testing.assert_array_equal(np.diag(adjacency), 0)

    def test_adjacency_is_frame_invariant_when_body_is_transformed(self) -> None:
        positions, _ = network_state(3000.0)
        transformed, transformed_center = coframe(
            positions,
            np.zeros(3),
            3000.0,
        )
        np.testing.assert_array_equal(
            link_adjacency(positions),
            link_adjacency(transformed, center=transformed_center),
        )

    def test_graph_spectrum_is_relabeling_invariant(self) -> None:
        positions, _ = network_state(6000.0)
        adjacency = link_adjacency(positions)
        permutation = np.eye(6)[[3, 0, 5, 2, 1, 4]]
        relabeled = permutation @ adjacency @ permutation.T
        np.testing.assert_allclose(
            laplacian_spectrum(adjacency),
            laplacian_spectrum(relabeled),
            atol=4e-15,
        )

    def test_reference_snapshots_are_connected(self) -> None:
        for time in np.linspace(0.0, DAY, 8):
            positions, _ = network_state(float(time))
            self.assertEqual(connected_components(link_adjacency(positions)), 1)

    def test_empty_graph_has_one_component_per_vertex(self) -> None:
        self.assertEqual(connected_components(np.zeros((5, 5), dtype=int)), 5)

    def test_temporal_earliest_arrival_respects_order(self) -> None:
        events = (
            (1.0, 0, 1, 0.1),
            (0.9, 1, 2, 0.1),
            (2.0, 1, 2, 0.1),
        )
        arrivals = earliest_arrival(3, events, 0, 0.0)
        np.testing.assert_allclose(arrivals, (0.0, 1.1, 2.1), atol=2e-15)

    def test_aggregated_path_need_not_be_time_respecting(self) -> None:
        events = ((2.0, 0, 1, 0.0), (1.0, 1, 2, 0.0))
        arrivals = earliest_arrival(3, events, 0, 0.0)
        self.assertTrue(math.isinf(float(arrivals[2])))

    def test_negative_delay_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            earliest_arrival(2, ((1.0, 0, 1, -0.1),), 0, 0.0)

    def test_source_outside_vertex_set_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            earliest_arrival(2, (), 2, 0.0)


class ClockAndEntropyTests(unittest.TestCase):
    def test_circular_offset_zero_crossing_is_three_halves_reference_radius(self) -> None:
        self.assertAlmostEqual(
            circular_clock_offset(1.5 * R_E),
            0.0,
            delta=1e-24,
        )

    def test_LEO_offset_is_negative(self) -> None:
        self.assertLess(circular_clock_offset(7_000_000.0), 0.0)

    def test_GPS_like_offset_is_positive(self) -> None:
        self.assertGreater(circular_clock_offset(26_560_000.0), 0.0)

    def test_circular_formula_matches_direct_weak_rate_difference(self) -> None:
        for radius in (7_000_000.0, 26_560_000.0, 42_164_000.0):
            speed = math.sqrt(MU_E / radius)
            direct = weak_clock_rate(radius, speed) - weak_clock_rate(R_E, 0.0)
            self.assertAlmostEqual(
                direct,
                circular_clock_offset(radius),
                delta=4e-16,
            )

    def test_clock_offsets_match_document_scale(self) -> None:
        expected = {
            7_000_000.0: -22.0333,
            26_560_000.0: 38.4373,
            42_164_000.0: 46.4461,
        }
        for radius, microseconds_per_day in expected.items():
            computed = circular_clock_offset(radius) * DAY * 1e6
            self.assertAlmostEqual(computed, microseconds_per_day, delta=0.001)

    def test_clock_functions_reject_invalid_inputs(self) -> None:
        with self.assertRaises(ValueError):
            circular_clock_offset(0.0)
        with self.assertRaises(ValueError):
            weak_clock_rate(-1.0, 1.0)
        with self.assertRaises(ValueError):
            weak_clock_rate(1.0, -1.0)

    def test_entropy_controls(self) -> None:
        self.assertEqual(shannon_entropy((1.0, 0.0)), 0.0)
        self.assertEqual(shannon_entropy((0.5, 0.5)), 1.0)
        self.assertEqual(shannon_entropy((1.0, 1.0, 1.0, 1.0)), 2.0)

    def test_entropy_normalizes_positive_weights(self) -> None:
        self.assertAlmostEqual(
            shannon_entropy((2.0, 2.0)),
            shannon_entropy((0.5, 0.5)),
            delta=0.0,
        )

    def test_entropy_rejects_invalid_inputs(self) -> None:
        for probabilities in ((), (0.0, 0.0), (1.0, -0.1)):
            with self.assertRaises(ValueError):
                shannon_entropy(probabilities)
        with self.assertRaises(ValueError):
            shannon_entropy((1.0,), base=1.0)


class ContractAndArtifactTests(unittest.TestCase):
    def test_contract_has_twenty_one_reference_gates(self) -> None:
        contract = load_yaml(CONTRACT)
        self.assertEqual(contract["schema"]["version"], "1.2.0")
        self.assertEqual(len(contract["reference_gates"]), 21)

    def test_contract_separates_closure_equivariance(self) -> None:
        closure = load_yaml(CONTRACT)["phase_closure_layer"]
        self.assertEqual(
            closure["constant_isometry"]["status"],
            "equivariance_not_pointwise_invariance",
        )
        self.assertFalse(
            closure["time_dependent_frame"]["closure_congruence_guaranteed"]
        )

    def test_contract_separates_Euclidean_and_Lorentz_invariants(self) -> None:
        clock = load_yaml(CONTRACT)["relativistic_clock_layer"]
        self.assertFalse(
            clock["flat_spacetime"][
                "equal_time_Euclidean_distance_invariant_under_boosts"
            ]
        )
        self.assertTrue(
            clock["comparison_boundary"]["individual_worldline_integral_invariant"]
        )

    def test_contract_separates_proximity_and_conjunction(self) -> None:
        distinction = load_yaml(CONTRACT)["line_of_sight_graph"]["distinction"]
        self.assertFalse(distinction["operational_collision_risk_claimed"])
        self.assertIn("covariance", distinction["conjunction_assessment"])

    def test_reference_ledger_has_53_typed_expressions(self) -> None:
        document = load_yaml(REFERENCE_LEDGER)["documents"][0]
        self.assertEqual(len(document["expressions"]), 53)
        self.assertEqual(document["ledger_level"], "reference")

    def test_every_claimed_invariant_has_a_declared_group(self) -> None:
        document = load_yaml(REFERENCE_LEDGER)["documents"][0]
        groups = set(document["groups"])
        for invariant in document["invariants"]:
            if invariant.get("claimed_invariant"):
                self.assertIn(invariant.get("group"), groups)

    def test_reference_protocol_fields_are_complete(self) -> None:
        document = load_yaml(REFERENCE_LEDGER)["documents"][0]
        expected = {
            "hidden_space",
            "system_descriptor",
            "reduction",
            "deterministic_observation",
            "stochastic_channel_or_explicit_noiseless_model",
            "observed_space",
            "reference_frame",
            "quantizer_or_partition",
            "spatial_resolution",
            "temporal_resolution",
            "observation_horizon",
            "estimator_or_declared_direct_readout",
            "uncertainty_or_exactness_statement",
            "unit_context",
            "defect_normalizations",
        }
        self.assertEqual(set(document["protocol_fields_present"]), expected)

    def test_reference_lint_is_clean(self) -> None:
        summary = load_json(REFERENCE_LINT)["summary"]
        self.assertEqual(summary["canonical_documents"], 1)
        self.assertEqual(summary["expressions_checked"], 53)
        self.assertEqual(summary["findings_total"], 0)
        self.assertEqual(summary["status_counts"], {"PASS": 1})

    def test_corpus_lint_is_fully_clean(self) -> None:
        summary = load_json(CORPUS_LINT)["summary"]
        self.assertEqual(summary["canonical_documents"], 18)
        self.assertEqual(summary["reference_documents"], 18)
        self.assertEqual(summary["critical_adapters"], 0)
        self.assertEqual(summary["expressions_checked"], 347)
        self.assertEqual(summary["findings_total"], 0)
        self.assertEqual(summary["status_counts"], {"PASS": 18})

    def test_legacy_satellite_source_is_superseded_once(self) -> None:
        corpus = load_yaml(CORPUS_LEDGER)
        records = [
            item
            for item in corpus["duplicate_or_superseded_sources"]
            if "satellite_networks_observation" in item.get("path", "")
        ]
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["status"], "superseded")
        self.assertEqual(
            records[0]["canonical_document"],
            "satellite-networks-observation-v1-2",
        )

    def test_metrics_and_benchmarks_are_clean(self) -> None:
        metrics = load_json(METRICS)
        self.assertEqual(metrics["benchmark_rows"], 553)
        self.assertEqual(metrics["failed_rows"], 0)
        with BENCHMARKS.open("r", encoding="utf-8", newline="") as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual(len(rows), 553)
        self.assertTrue(all(row["status"] == "PASS" for row in rows))

    def test_PDF_has_expected_metadata_and_page_count(self) -> None:
        reader = PdfReader(PDF)
        metadata = reader.metadata or {}
        self.assertEqual(len(reader.pages), 8)
        self.assertEqual(
            metadata.get("/Title"),
            "Satellite Networks under Typed Frames and Temporal Observation Channels",
        )
        self.assertEqual(
            metadata.get("/Author"),
            "Stas, Independent Research Program",
        )

    def test_PDF_is_A4_unencrypted_and_noninteractive(self) -> None:
        reader = PdfReader(PDF)
        box = reader.pages[0].mediabox
        self.assertFalse(reader.is_encrypted)
        self.assertIn(reader.get_fields(), (None, {}))
        self.assertAlmostEqual(float(box.width), 595.28, delta=0.2)
        self.assertAlmostEqual(float(box.height), 841.89, delta=0.2)

    def test_fonts_are_embedded(self) -> None:
        result = subprocess.run(
            ["pdffonts", str(PDF)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0)
        rows = [
            line.split()
            for line in result.stdout.splitlines()[2:]
            if line.strip()
        ]
        self.assertTrue(rows)
        self.assertTrue(
            all(len(row) >= 7 and row[-5].lower() == "yes" for row in rows)
        )

    def test_LaTeX_log_is_clean(self) -> None:
        content = LOG.read_text(encoding="utf-8", errors="replace")
        for token in (
            "Overfull",
            "Underfull",
            "LaTeX Warning",
            "undefined references",
            "multiply defined",
            "Fatal error",
            "Missing character",
        ):
            self.assertNotIn(token, content)

    def test_extracted_text_is_complete(self) -> None:
        content = TEXT.read_text(encoding="utf-8", errors="replace")
        self.assertGreater(len(content), 22_000)
        self.assertEqual(content.count("\f"), 8)
        self.assertIn("Closure is equivariant, not invariant", content)
        self.assertIn("Time-respecting journey", content)
        self.assertEqual(
            sum(line.strip() == "References" for line in content.splitlines()),
            1,
        )

    def test_source_contains_required_fragments(self) -> None:
        content = TEX.read_text(encoding="utf-8")
        for fragment in (
            r"\Gcal_I=C^1(I,\SE(3))",
            r"D_{ij}^{\mathfrak f}(t)",
            r"L_\omega=\{m\in\Z^k:m\cdot\omega=0\}",
            r"K_{F_g}=gK_F",
            r"e^{i(\omega+2\pi q/\Delta t)t_m}",
            r"\operatorname{LOS}_{ij}(t)",
            r"t_{k+1}\ge t_k+\ell_{e_k}(t_k)",
            r"\tau_i[\gamma_i]",
        ):
            self.assertIn(fragment, content)

    def test_no_prohibited_tokens(self) -> None:
        for path in (TEX, TEXT, CONTRACT, REFERENCE_LEDGER, CORPUS_LEDGER):
            content = path.read_text(encoding="utf-8", errors="replace")
            for token in ("TODO", "TBD", "PENDING", "\ufffd"):
                self.assertNotIn(token, content)

    def test_bibliography_heading_is_unique(self) -> None:
        extracted = TEXT.read_text(encoding="utf-8", errors="replace")
        source = TEX.read_text(encoding="utf-8")
        self.assertEqual(
            sum(line.strip() == "References" for line in extracted.splitlines()),
            1,
        )
        self.assertEqual(source.count(r"\section*{References}"), 1)


class BenchmarkRowTests(unittest.TestCase):
    """One independently discoverable regression per benchmark row."""


def _benchmark_rows() -> list[dict[str, str]]:
    if not BENCHMARKS.is_file():
        return []
    with BENCHMARKS.open("r", encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def add_benchmark_case(index: int, row: dict[str, str]) -> None:
    def test_case(self: BenchmarkRowTests) -> None:
        expected = float(row["expected"])
        computed = float(row["computed"])
        tolerance = float(row["tolerance"])
        self.assertLessEqual(abs(computed - expected), tolerance)
        self.assertEqual(row["status"], "PASS")

    safe = "".join(
        character if character.isalnum() else "_"
        for character in f"{row['category']}_{row['case']}_{row['quantity']}"
    )
    setattr(
        BenchmarkRowTests,
        f"test_benchmark_{index:03d}_{safe}",
        test_case,
    )


for _index, _row in enumerate(_benchmark_rows()):
    add_benchmark_case(_index, _row)


if __name__ == "__main__":
    unittest.main()
