#!/usr/bin/env python3
"""Generate deterministic controls for the P11 satellite-network reference."""

from __future__ import annotations

import csv
import heapq
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np


ROOT = Path(__file__).resolve().parents[3]
P11 = ROOT / "work/p11_satellite_networks_v1_2"
CSV_PATH = P11 / "data/satellite_networks_benchmarks_v1_2.csv"
METRICS_PATH = P11 / "data/satellite_networks_metrics_v1_2.json"

MU_E = 3.986004418e14
R_E = 6_378_137.0
C_LIGHT = 299_792_458.0
DAY = 86_400.0


@dataclass(frozen=True)
class Orbit:
    name: str
    a: float
    e: float
    inc: float
    raan: float
    argp: float
    mean_anomaly_0: float


ORBITS = (
    Orbit("LEO_A", 7_000_000.0, 0.001, math.radians(53.0), 0.0, 0.0, 0.0),
    Orbit(
        "LEO_B",
        7_200_000.0,
        0.010,
        math.radians(70.0),
        math.radians(120.0),
        math.radians(25.0),
        0.4,
    ),
    Orbit(
        "MEO_A",
        26_560_000.0,
        0.010,
        math.radians(55.0),
        0.0,
        math.radians(15.0),
        0.2,
    ),
    Orbit(
        "MEO_B",
        26_560_000.0,
        0.020,
        math.radians(55.0),
        math.radians(120.0),
        math.radians(45.0),
        2.2,
    ),
    Orbit(
        "GEO_A",
        42_164_000.0,
        0.001,
        math.radians(0.1),
        math.radians(240.0),
        0.0,
        1.0,
    ),
    Orbit(
        "HEO_A",
        26_600_000.0,
        0.650,
        math.radians(63.4),
        math.radians(60.0),
        math.radians(270.0),
        0.3,
    ),
)


def solve_kepler(mean_anomaly: float, eccentricity: float) -> float:
    """Solve E - e sin(E) = M for an elliptic orbit."""
    if not 0.0 <= eccentricity < 1.0:
        raise ValueError("elliptic eccentricity must satisfy 0 <= e < 1")
    mean_anomaly = math.remainder(float(mean_anomaly), 2.0 * math.pi)
    estimate = mean_anomaly if eccentricity < 0.8 else math.pi
    for _ in range(50):
        residual = estimate - eccentricity * math.sin(estimate) - mean_anomaly
        derivative = 1.0 - eccentricity * math.cos(estimate)
        update = residual / derivative
        estimate -= update
        if abs(update) <= 2e-15:
            break
    return estimate


def rotation_x(angle: float) -> np.ndarray:
    c, s = math.cos(angle), math.sin(angle)
    return np.array(((1.0, 0.0, 0.0), (0.0, c, -s), (0.0, s, c)))


def rotation_z(angle: float) -> np.ndarray:
    c, s = math.cos(angle), math.sin(angle)
    return np.array(((c, -s, 0.0), (s, c, 0.0), (0.0, 0.0, 1.0)))


def orbital_rotation(orbit: Orbit) -> np.ndarray:
    return (
        rotation_z(orbit.raan)
        @ rotation_x(orbit.inc)
        @ rotation_z(orbit.argp)
    )


def mean_motion(semimajor_axis: float) -> float:
    if semimajor_axis <= 0.0:
        raise ValueError("semimajor axis must be positive")
    return math.sqrt(MU_E / semimajor_axis**3)


def orbit_period(semimajor_axis: float) -> float:
    return 2.0 * math.pi / mean_motion(semimajor_axis)


def kepler_state(orbit: Orbit, time: float) -> tuple[np.ndarray, np.ndarray]:
    n = mean_motion(orbit.a)
    eccentric_anomaly = solve_kepler(
        orbit.mean_anomaly_0 + n * time,
        orbit.e,
    )
    c_e, s_e = math.cos(eccentric_anomaly), math.sin(eccentric_anomaly)
    beta = math.sqrt(1.0 - orbit.e**2)
    radius_factor = 1.0 - orbit.e * c_e
    d_e_dt = n / radius_factor
    position_plane = np.array(
        (orbit.a * (c_e - orbit.e), orbit.a * beta * s_e, 0.0)
    )
    velocity_plane = np.array(
        (
            -orbit.a * s_e * d_e_dt,
            orbit.a * beta * c_e * d_e_dt,
            0.0,
        )
    )
    rotation = orbital_rotation(orbit)
    return rotation @ position_plane, rotation @ velocity_plane


def network_state(time: float) -> tuple[np.ndarray, np.ndarray]:
    states = [kepler_state(orbit, time) for orbit in ORBITS]
    return (
        np.stack([item[0] for item in states]),
        np.stack([item[1] for item in states]),
    )


def distance_matrix(points: np.ndarray) -> np.ndarray:
    values = np.asarray(points, dtype=float)
    if values.ndim != 2:
        raise ValueError("points must be a two-dimensional array")
    differences = values[:, None, :] - values[None, :, :]
    return np.linalg.norm(differences, axis=2)


def centered_gram(distances: np.ndarray) -> np.ndarray:
    values = np.asarray(distances, dtype=float)
    if values.ndim != 2 or values.shape[0] != values.shape[1]:
        raise ValueError("distance matrix must be square")
    count = values.shape[0]
    centering = np.eye(count) - np.ones((count, count)) / count
    return -0.5 * centering @ (values * values) @ centering


def observer_origin(time: float) -> np.ndarray:
    omega = 2.0 * math.pi / (7.0 * DAY)
    return np.array(
        (
            1.2e9 * math.cos(omega * time),
            1.2e9 * math.sin(omega * time),
            2.0e8 * math.sin(0.37 * omega * time),
        )
    )


def observer_rotation(time: float) -> np.ndarray:
    return rotation_z(7.2921150e-5 * time) @ rotation_x(
        0.17 * math.sin(2.0 * math.pi * time / DAY)
    )


def coframe(
    points: np.ndarray,
    center: np.ndarray,
    time: float,
) -> tuple[np.ndarray, np.ndarray]:
    rotation = observer_rotation(time)
    origin = observer_origin(time)
    transformed = (np.asarray(points) - origin) @ rotation
    transformed_center = (np.asarray(center) - origin) @ rotation
    return transformed, transformed_center


def segment_clearance(
    point_a: np.ndarray,
    point_b: np.ndarray,
    center: np.ndarray | None = None,
) -> float:
    center_value = np.zeros(3) if center is None else np.asarray(center, dtype=float)
    first = np.asarray(point_a, dtype=float) - center_value
    second = np.asarray(point_b, dtype=float) - center_value
    direction = second - first
    denominator = float(direction @ direction)
    if denominator == 0.0:
        return float(np.linalg.norm(first))
    parameter = float(np.clip(-(first @ direction) / denominator, 0.0, 1.0))
    return float(np.linalg.norm(first + parameter * direction))


def link_adjacency(
    points: np.ndarray,
    *,
    center: np.ndarray | None = None,
    occulting_radius: float = R_E + 100_000.0,
    link_range: float = 50_000_000.0,
) -> np.ndarray:
    values = np.asarray(points, dtype=float)
    count = values.shape[0]
    adjacency = np.zeros((count, count), dtype=int)
    for left in range(count):
        for right in range(left + 1, count):
            separation = float(np.linalg.norm(values[left] - values[right]))
            clearance = segment_clearance(
                values[left],
                values[right],
                center,
            )
            active = separation <= link_range and clearance > occulting_radius
            adjacency[left, right] = adjacency[right, left] = int(active)
    return adjacency


def laplacian_spectrum(adjacency: np.ndarray) -> np.ndarray:
    values = np.asarray(adjacency, dtype=float)
    if values.ndim != 2 or values.shape[0] != values.shape[1]:
        raise ValueError("adjacency matrix must be square")
    laplacian = np.diag(values.sum(axis=1)) - values
    return np.linalg.eigvalsh(laplacian)


def weak_clock_rate(radius: float, speed: float) -> float:
    if radius <= 0.0 or speed < 0.0:
        raise ValueError("radius must be positive and speed nonnegative")
    return 1.0 - MU_E / (radius * C_LIGHT**2) - speed**2 / (2.0 * C_LIGHT**2)


def circular_clock_offset(
    radius: float,
    reference_radius: float = R_E,
) -> float:
    if radius <= 0.0 or reference_radius <= 0.0:
        raise ValueError("radii must be positive")
    return MU_E / C_LIGHT**2 * (
        1.0 / reference_radius - 3.0 / (2.0 * radius)
    )


def retarded_time_static(
    reception_time: float,
    source_position: np.ndarray,
    observer_position: np.ndarray,
) -> float:
    distance = float(
        np.linalg.norm(
            np.asarray(source_position, dtype=float)
            - np.asarray(observer_position, dtype=float)
        )
    )
    return reception_time - distance / C_LIGHT


def shannon_entropy(probabilities: Iterable[float], base: float = 2.0) -> float:
    values = np.asarray(tuple(probabilities), dtype=float)
    if values.ndim != 1 or values.size == 0 or np.any(values < 0.0):
        raise ValueError("probabilities must be a nonempty nonnegative vector")
    total = float(values.sum())
    if total <= 0.0:
        raise ValueError("probability total must be positive")
    if base <= 0.0 or math.isclose(base, 1.0):
        raise ValueError("invalid logarithm base")
    values = values / total
    positive = values[values > 0.0]
    return float(-np.sum(positive * np.log(positive) / math.log(base)))


def earliest_arrival(
    vertex_count: int,
    events: Sequence[tuple[float, int, int, float]],
    source: int,
    start_time: float,
) -> np.ndarray:
    """Earliest arrivals for instantaneous undirected contacts."""
    if not 0 <= source < vertex_count:
        raise ValueError("source is outside the vertex set")
    arrivals = np.full(vertex_count, np.inf)
    arrivals[source] = float(start_time)
    for time, left, right, delay in sorted(events):
        if delay < 0.0:
            raise ValueError("contact delay must be nonnegative")
        previous_left = float(arrivals[left])
        previous_right = float(arrivals[right])
        if previous_left <= time:
            arrivals[right] = min(arrivals[right], time + delay)
        if previous_right <= time:
            arrivals[left] = min(arrivals[left], time + delay)
    return arrivals


def connected_components(adjacency: np.ndarray) -> int:
    values = np.asarray(adjacency, dtype=int)
    count = values.shape[0]
    unseen = set(range(count))
    components = 0
    while unseen:
        components += 1
        stack = [unseen.pop()]
        while stack:
            vertex = stack.pop()
            neighbors = {
                int(item) for item in np.flatnonzero(values[vertex])
            }
            new = neighbors & unseen
            unseen -= new
            stack.extend(new)
    return components


def build_benchmarks() -> tuple[list[dict[str, object]], dict[str, object]]:
    rows: list[dict[str, object]] = []
    errors: dict[str, list[float]] = {}

    def add(
        category: str,
        case: str,
        quantity: str,
        expected: float,
        computed: float,
        tolerance: float,
    ) -> None:
        error = abs(float(computed) - float(expected))
        errors.setdefault(category, []).append(error)
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

    sample_times = np.linspace(0.0, DAY, 8)
    permutation = np.array((3, 0, 5, 2, 1, 4))
    permutation_matrix = np.eye(len(ORBITS))[permutation]
    edge_counts: list[int] = []
    component_counts: list[int] = []

    initial_invariants: dict[str, tuple[float, float]] = {}
    for orbit in ORBITS:
        position, velocity = kepler_state(orbit, 0.0)
        energy = 0.5 * float(velocity @ velocity) - MU_E / float(
            np.linalg.norm(position)
        )
        angular_momentum = float(np.linalg.norm(np.cross(position, velocity)))
        initial_invariants[orbit.name] = (energy, angular_momentum)

    for time_index, time in enumerate(sample_times):
        positions, velocities = network_state(float(time))
        transformed, transformed_center = coframe(
            positions,
            np.zeros(3),
            float(time),
        )
        inertial_distances = distance_matrix(positions)
        transformed_distances = distance_matrix(transformed)

        for orbit_index, orbit in enumerate(ORBITS):
            position = positions[orbit_index]
            velocity = velocities[orbit_index]
            energy = 0.5 * float(velocity @ velocity) - MU_E / float(
                np.linalg.norm(position)
            )
            angular_momentum = float(
                np.linalg.norm(np.cross(position, velocity))
            )
            expected_energy, expected_momentum = initial_invariants[orbit.name]
            add(
                "two_body",
                f"{orbit.name}_t{time_index}",
                "specific_energy",
                expected_energy,
                energy,
                2e-8 * abs(expected_energy),
            )
            add(
                "two_body",
                f"{orbit.name}_t{time_index}",
                "specific_angular_momentum",
                expected_momentum,
                angular_momentum,
                2e-12 * abs(expected_momentum),
            )

        for left in range(len(ORBITS)):
            for right in range(left + 1, len(ORBITS)):
                case = f"t{time_index}_i{left}_j{right}"
                add(
                    "frame_distance",
                    case,
                    "pairwise_distance_m",
                    inertial_distances[left, right],
                    transformed_distances[left, right],
                    2e-6,
                )
                inertial_clearance = segment_clearance(
                    positions[left],
                    positions[right],
                )
                transformed_clearance = segment_clearance(
                    transformed[left],
                    transformed[right],
                    transformed_center,
                )
                add(
                    "frame_clearance",
                    case,
                    "segment_clearance_m",
                    inertial_clearance,
                    transformed_clearance,
                    2e-6,
                )

        direct_gram = (
            positions - positions.mean(axis=0, keepdims=True)
        ) @ (positions - positions.mean(axis=0, keepdims=True)).T
        reconstructed_gram = centered_gram(inertial_distances)
        gram_scale = max(float(np.linalg.norm(direct_gram)), 1.0)
        add(
            "EDM",
            f"t{time_index}",
            "relative_Gram_residual",
            0.0,
            float(np.linalg.norm(reconstructed_gram - direct_gram) / gram_scale),
            2e-14,
        )
        eigenvalues = np.linalg.eigvalsh(reconstructed_gram)
        add(
            "EDM",
            f"t{time_index}",
            "fourth_eigenvalue_over_trace",
            0.0,
            max(0.0, float(eigenvalues[-4]))
            / max(float(np.trace(reconstructed_gram)), 1.0),
            2e-15,
        )

        adjacency = link_adjacency(positions)
        transformed_adjacency = link_adjacency(
            transformed,
            center=transformed_center,
        )
        add(
            "graph_frame",
            f"t{time_index}",
            "adjacency_mismatch_count",
            0.0,
            float(np.count_nonzero(adjacency - transformed_adjacency)),
            0.0,
        )
        relabeled = permutation_matrix @ adjacency @ permutation_matrix.T
        original_spectrum = laplacian_spectrum(adjacency)
        relabeled_spectrum = laplacian_spectrum(relabeled)
        for eigen_index, (expected, computed) in enumerate(
            zip(original_spectrum, relabeled_spectrum, strict=True)
        ):
            add(
                "graph_relabel",
                f"t{time_index}",
                f"laplacian_eigenvalue_{eigen_index}",
                expected,
                computed,
                2e-12,
            )
        edge_counts.append(int(adjacency.sum() // 2))
        component_counts.append(connected_components(adjacency))

    delta_t = 37.0
    omega = 0.071
    aliased = omega + 2.0 * math.pi * 3.0 / delta_t
    for index in range(64):
        time = index * delta_t
        first = complex(np.exp(1j * omega * time))
        second = complex(np.exp(1j * aliased * time))
        add(
            "sampling_alias",
            f"m{index}",
            "real_part",
            first.real,
            second.real,
            2e-12,
        )
        add(
            "sampling_alias",
            f"m{index}",
            "imaginary_part",
            first.imag,
            second.imag,
            2e-12,
        )

    radii = {
        "zero_crossing": 1.5 * R_E,
        "LEO_7000km": 7_000_000.0,
        "GPS_like": 26_560_000.0,
        "GEO_like": 42_164_000.0,
    }
    clock_offsets: dict[str, float] = {}
    for name, radius in radii.items():
        offset = circular_clock_offset(radius)
        clock_offsets[name] = offset * DAY * 1e6
        expected = 0.0 if name == "zero_crossing" else offset
        add(
            "clock",
            name,
            "circular_rate_offset",
            expected,
            offset,
            1e-24 if name == "zero_crossing" else 0.0,
        )
        speed = math.sqrt(MU_E / radius)
        direct = weak_clock_rate(radius, speed) - weak_clock_rate(R_E, 0.0)
        add(
            "clock",
            name,
            "direct_minus_circular_offset",
            0.0,
            direct - offset,
            4e-16,
        )

    static_source = np.array((26_560_000.0, 0.0, 0.0))
    reception_time = 1000.0
    emission_time = retarded_time_static(
        reception_time,
        static_source,
        np.zeros(3),
    )
    add(
        "light_time",
        "static_source",
        "null_residual_s",
        0.0,
        reception_time
        - emission_time
        - float(np.linalg.norm(static_source)) / C_LIGHT,
        1e-13,
    )

    entropy_cases = {
        "delta": ([1.0, 0.0, 0.0, 0.0], 0.0),
        "uniform_four": ([1.0, 1.0, 1.0, 1.0], 2.0),
        "binary_half": ([0.5, 0.5], 1.0),
    }
    for name, (probabilities, expected) in entropy_cases.items():
        add(
            "entropy",
            name,
            "bits",
            expected,
            shannon_entropy(probabilities),
            2e-15,
        )

    events = (
        (1.0, 0, 1, 0.2),
        (1.1, 1, 2, 0.2),
        (1.3, 1, 2, 0.2),
        (1.6, 2, 3, 0.1),
        (2.0, 0, 4, 0.1),
        (2.2, 4, 3, 0.1),
    )
    arrivals = earliest_arrival(5, events, 0, 0.0)
    expected_arrivals = np.array((0.0, 1.2, 1.5, 1.7, 2.1))
    for vertex, (expected, computed) in enumerate(
        zip(expected_arrivals, arrivals, strict=True)
    ):
        add(
            "temporal_graph",
            f"vertex_{vertex}",
            "earliest_arrival_s",
            expected,
            computed,
            2e-15,
        )

    all_statuses = [str(row["status"]) for row in rows]
    metrics = {
        "schema": {
            "id": "go-p11-satellite-network-benchmark-metrics",
            "version": "1.2.0",
        },
        "date": "2026-07-28",
        "constants": {
            "mu_E_m3_s2": MU_E,
            "R_E_m": R_E,
            "c_m_s": C_LIGHT,
        },
        "satellites": [orbit.name for orbit in ORBITS],
        "sample_count": int(len(sample_times)),
        "benchmark_rows": len(rows),
        "failed_rows": all_statuses.count("FAIL"),
        "category_counts": {
            category: sum(row["category"] == category for row in rows)
            for category in sorted(errors)
        },
        "max_abs_error_by_category": {
            category: max(values) if values else 0.0
            for category, values in sorted(errors.items())
        },
        "snapshot_edge_counts": edge_counts,
        "snapshot_component_counts": component_counts,
        "clock_offsets_microseconds_per_day": clock_offsets,
        "alias": {
            "sampling_interval_s": delta_t,
            "base_angular_frequency_rad_s": omega,
            "aliased_angular_frequency_rad_s": aliased,
            "integer_shift": 3,
        },
        "temporal_earliest_arrivals_s": arrivals.tolist(),
    }
    return rows, metrics


def main() -> None:
    rows, metrics = build_benchmarks()
    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CSV_PATH.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=(
                "category",
                "case",
                "quantity",
                "expected",
                "computed",
                "abs_error",
                "tolerance",
                "status",
            ),
        )
        writer.writeheader()
        writer.writerows(rows)
    METRICS_PATH.write_text(
        json.dumps(metrics, indent=2) + "\n",
        encoding="utf-8",
    )
    if metrics["failed_rows"]:
        raise SystemExit(
            f"{metrics['failed_rows']} benchmark rows failed"
        )
    print(
        f"wrote {metrics['benchmark_rows']} PASS rows to "
        f"{CSV_PATH.relative_to(ROOT)}"
    )


if __name__ == "__main__":
    main()
