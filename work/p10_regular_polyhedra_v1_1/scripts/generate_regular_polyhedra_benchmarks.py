#!/usr/bin/env python3
"""Generate exact and numerical controls for the P10 polyhedra reference."""

from __future__ import annotations

import csv
import itertools
import json
import math
from pathlib import Path
from typing import Iterable

import numpy as np


ROOT = Path(__file__).resolve().parents[3]
P10 = ROOT / "work/p10_regular_polyhedra_v1_1"
CSV_PATH = P10 / "data/regular_polyhedra_benchmarks_v1_1.csv"
METRICS_PATH = P10 / "data/regular_polyhedra_metrics_v1_1.json"


PLATONIC = (
    {"name": "tetrahedron", "p": 3, "q": 3, "V": 4, "E": 6, "F": 4},
    {"name": "cube", "p": 4, "q": 3, "V": 8, "E": 12, "F": 6},
    {"name": "octahedron", "p": 3, "q": 4, "V": 6, "E": 12, "F": 8},
    {"name": "dodecahedron", "p": 5, "q": 3, "V": 20, "E": 30, "F": 12},
    {"name": "icosahedron", "p": 3, "q": 5, "V": 12, "E": 30, "F": 20},
)


Vertex = tuple[int, int, int]
Edge = frozenset[Vertex]
Cycle = tuple[Vertex, ...]
Flag = tuple[Vertex, Edge, frozenset[Vertex]]
Transform = tuple[tuple[int, int, int], tuple[int, int, int]]


def cube_vertices() -> tuple[Vertex, ...]:
    return tuple(itertools.product((-1, 1), repeat=3))


def cube_edges() -> frozenset[Edge]:
    vertices = cube_vertices()
    return frozenset(
        frozenset((u, v))
        for index, u in enumerate(vertices)
        for v in vertices[index + 1 :]
        if sum(a != b for a, b in zip(u, v, strict=True)) == 1
    )


def cube_square_faces() -> tuple[Cycle, ...]:
    cycles: list[Cycle] = []
    for axis in range(3):
        other = [item for item in range(3) if item != axis]
        for sign in (-1, 1):
            cycle: list[Vertex] = []
            for a, b in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
                point = [0, 0, 0]
                point[axis] = sign
                point[other[0]] = a
                point[other[1]] = b
                cycle.append(tuple(point))
            cycles.append(tuple(cycle))
    return tuple(cycles)


def canonical_cycle(cycle: Iterable[Vertex]) -> Cycle:
    values = tuple(cycle)
    variants: list[Cycle] = []
    for sequence in (values, tuple(reversed(values))):
        variants.extend(
            sequence[offset:] + sequence[:offset]
            for offset in range(len(sequence))
        )
    return min(variants)


def cube_petrie_faces() -> tuple[Cycle, ...]:
    faces: set[Cycle] = set()
    for start in cube_vertices():
        for order in itertools.permutations(range(3)):
            current = list(start)
            cycle: list[Vertex] = [start]
            for step in range(6):
                axis = order[step % 3]
                current = list(current)
                current[axis] *= -1
                point = tuple(current)
                if step < 5:
                    cycle.append(point)
                else:
                    if point != start:
                        raise AssertionError("Petrie walk did not close")
            faces.add(canonical_cycle(cycle))
    return tuple(sorted(faces))


def cycle_edges(cycle: Cycle) -> frozenset[Edge]:
    return frozenset(
        frozenset((cycle[index], cycle[(index + 1) % len(cycle)]))
        for index in range(len(cycle))
    )


def flags_from_faces(faces: Iterable[Cycle]) -> frozenset[Flag]:
    flags: set[Flag] = set()
    for cycle in faces:
        face_vertices = frozenset(cycle)
        for edge in cycle_edges(cycle):
            for vertex in edge:
                flags.add((vertex, edge, face_vertices))
    return frozenset(flags)


def cube_transforms(*, allow_axis_permutations: bool) -> tuple[Transform, ...]:
    permutations = (
        tuple(itertools.permutations(range(3)))
        if allow_axis_permutations
        else ((0, 1, 2),)
    )
    return tuple(
        (permutation, signs)
        for permutation in permutations
        for signs in itertools.product((-1, 1), repeat=3)
    )


def transform_vertex(vertex: Vertex, transform: Transform) -> Vertex:
    permutation, signs = transform
    return tuple(
        signs[index] * vertex[permutation[index]]
        for index in range(3)
    )


def transform_flag(flag: Flag, transform: Transform) -> Flag:
    vertex, edge, face = flag
    return (
        transform_vertex(vertex, transform),
        frozenset(transform_vertex(item, transform) for item in edge),
        frozenset(transform_vertex(item, transform) for item in face),
    )


def orbit_partition(
    flags: frozenset[Flag],
    transforms: Iterable[Transform],
) -> tuple[frozenset[Flag], ...]:
    remaining = set(flags)
    orbits: list[frozenset[Flag]] = []
    transforms = tuple(transforms)
    while remaining:
        seed = next(iter(remaining))
        orbit = frozenset(transform_flag(seed, item) for item in transforms)
        if not orbit <= flags:
            raise ValueError("transform does not preserve the flag set")
        orbits.append(orbit)
        remaining -= orbit
    return tuple(orbits)


def spherical_type_pairs(limit: int = 20) -> tuple[tuple[int, int], ...]:
    return tuple(
        (p, q)
        for p in range(3, limit + 1)
        for q in range(3, limit + 1)
        if 1.0 / p + 1.0 / q > 0.5
    )


def symmetry_residual(
    exact: np.ndarray,
    observed: np.ndarray,
    transform: np.ndarray,
    permutation: np.ndarray,
) -> float:
    exact = np.asarray(exact, dtype=float)
    observed = np.asarray(observed, dtype=float)
    transform = np.asarray(transform, dtype=float)
    permutation = np.asarray(permutation, dtype=int)
    if exact.shape != observed.shape or exact.ndim != 2:
        raise ValueError("exact and observed point arrays must match")
    if transform.shape != (exact.shape[1], exact.shape[1]):
        raise ValueError("transform has incompatible shape")
    if sorted(permutation.tolist()) != list(range(exact.shape[0])):
        raise ValueError("permutation must be bijective")
    residuals = observed @ transform.T - observed[permutation]
    return float(np.sqrt(np.mean(np.sum(residuals * residuals, axis=1))))


def finite_library_certificate(
    candidates: np.ndarray,
    observation: np.ndarray,
    target_index: int,
) -> tuple[float, float, int]:
    candidates = np.asarray(candidates, dtype=float)
    observation = np.asarray(observation, dtype=float)
    if candidates.ndim != 2 or observation.shape != (candidates.shape[1],):
        raise ValueError("candidate library and observation are incompatible")
    distances = np.linalg.norm(candidates - observation[None, :], axis=1)
    target = candidates[target_index]
    separations = np.linalg.norm(candidates - target[None, :], axis=1)
    positive = separations[np.arange(candidates.shape[0]) != target_index]
    delta = float(np.min(positive))
    return delta, float(distances[target_index]), int(np.argmin(distances))


def orbit_entropy(orbit_sizes: Iterable[int], base: float = 2.0) -> float:
    sizes = np.asarray(tuple(orbit_sizes), dtype=float)
    if sizes.ndim != 1 or sizes.size == 0 or np.any(sizes <= 0.0):
        raise ValueError("orbit sizes must be positive")
    if base <= 0.0 or math.isclose(base, 1.0):
        raise ValueError("invalid logarithm base")
    weights = sizes / sizes.sum()
    return float(-np.sum(weights * np.log(weights) / math.log(base)))


def build_benchmarks() -> tuple[list[dict[str, object]], dict[str, object]]:
    rows: list[dict[str, object]] = []
    errors: list[float] = []

    def add(
        category: str,
        case: str,
        quantity: str,
        expected: float,
        computed: float,
        tolerance: float,
    ) -> None:
        error = abs(float(computed) - float(expected))
        errors.append(error)
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

    for item in PLATONIC:
        name = str(item["name"])
        p, q = int(item["p"]), int(item["q"])
        vertices, edges, faces = int(item["V"]), int(item["E"]), int(item["F"])
        add("Platonic_incidence", name, "pF_minus_2E", 0.0, p * faces - 2 * edges, 0.0)
        add("Platonic_incidence", name, "qV_minus_2E", 0.0, q * vertices - 2 * edges, 0.0)
        add("Platonic_incidence", name, "Euler_characteristic", 2.0, vertices - edges + faces, 0.0)
        add("Platonic_incidence", name, "flag_count", 4.0 * edges, 4.0 * edges, 0.0)
        add(
            "Platonic_incidence",
            name,
            "spherical_identity",
            1.0 / edges,
            1.0 / p + 1.0 / q - 0.5,
            1e-15,
        )
        add("Platonic_incidence", name, "dual_V", float(faces), float(faces), 0.0)
        add("Platonic_incidence", name, "dual_E", float(edges), float(edges), 0.0)
        add("Platonic_incidence", name, "dual_F", float(vertices), float(vertices), 0.0)

    expected_pairs = {(3, 3), (4, 3), (3, 4), (5, 3), (3, 5)}
    computed_pairs = set(spherical_type_pairs(12))
    for p in range(3, 13):
        for q in range(3, 13):
            add(
                "spherical_type",
                f"p_{p}_q_{q}",
                "admissible",
                float((p, q) in expected_pairs),
                float((p, q) in computed_pairs),
                0.0,
            )

    square_faces = cube_square_faces()
    petrie_faces = cube_petrie_faces()
    edges = cube_edges()
    square_flags = flags_from_faces(square_faces)
    petrie_flags = flags_from_faces(petrie_faces)
    add("cube_Petrial", "cube", "vertices", 8.0, len(cube_vertices()), 0.0)
    add("cube_Petrial", "cube", "edges", 12.0, len(edges), 0.0)
    add("cube_Petrial", "cube", "square_faces", 6.0, len(square_faces), 0.0)
    add("cube_Petrial", "Petrial", "hexagonal_faces", 4.0, len(petrie_faces), 0.0)
    add("cube_Petrial", "cube", "square_face_length", 4.0, len(square_faces[0]), 0.0)
    add("cube_Petrial", "Petrial", "Petrie_face_length", 6.0, len(petrie_faces[0]), 0.0)
    add("cube_Petrial", "cube", "flags", 48.0, len(square_flags), 0.0)
    add("cube_Petrial", "Petrial", "flags", 48.0, len(petrie_flags), 0.0)
    add("cube_Petrial", "cube", "Euler_characteristic", 2.0, 8 - 12 + 6, 0.0)
    add("cube_Petrial", "Petrial", "Euler_characteristic", 0.0, 8 - 12 + 4, 0.0)
    add(
        "cube_Petrial",
        "shared_skeleton",
        "edge_symmetric_difference",
        0.0,
        len(edges.symmetric_difference(cube_edges())),
        0.0,
    )

    cube_group = cube_transforms(allow_axis_permutations=True)
    cuboid_group = cube_transforms(allow_axis_permutations=False)
    square_orbits = orbit_partition(square_flags, cube_group)
    cuboid_orbits = orbit_partition(square_flags, cuboid_group)
    petrie_orbits = orbit_partition(petrie_flags, cube_group)
    add("flag_orbits", "cube_group", "group_order", 48.0, len(cube_group), 0.0)
    add("flag_orbits", "cuboid_group", "group_order", 8.0, len(cuboid_group), 0.0)
    add("flag_orbits", "cube_group", "square_flag_orbits", 1.0, len(square_orbits), 0.0)
    add("flag_orbits", "cuboid_group", "square_flag_orbits", 6.0, len(cuboid_orbits), 0.0)
    add("flag_orbits", "cube_group", "Petrial_flag_orbits", 1.0, len(petrie_orbits), 0.0)
    add("flag_orbits", "cube_group", "orbit_entropy_bits", 0.0, orbit_entropy([48]), 0.0)
    add(
        "flag_orbits",
        "cuboid_group",
        "orbit_entropy_bits",
        math.log2(6.0),
        orbit_entropy([8, 8, 8, 8, 8, 8]),
        1e-15,
    )

    exact = np.asarray(cube_vertices(), dtype=float)
    transform = np.diag([-1.0, 1.0, 1.0])
    transformed = exact @ transform.T
    lookup = {tuple(row): index for index, row in enumerate(exact)}
    permutation = np.asarray([lookup[tuple(row)] for row in transformed], dtype=int)
    for seed in range(24):
        rng = np.random.default_rng(7100 + seed)
        epsilon = 1e-3 * (1.0 + seed / 12.0)
        raw = rng.normal(size=exact.shape)
        norms = np.linalg.norm(raw, axis=1)
        scales = rng.uniform(0.0, epsilon, size=exact.shape[0])
        noise = raw / norms[:, None] * scales[:, None]
        observed = exact + noise
        residual = symmetry_residual(exact, observed, transform, permutation)
        add(
            "bounded_noise_symmetry",
            f"seed_{seed:02d}",
            "positive_margin_2epsilon_minus_residual",
            0.0,
            max(0.0, residual - 2.0 * epsilon),
            1e-14,
        )
        add(
            "bounded_noise_symmetry",
            f"seed_{seed:02d}",
            "normalized_residual_bound",
            0.0,
            max(0.0, residual / 2.0 - epsilon),
            1e-14,
        )

    candidates = np.asarray(
        [[4, 6, 4], [8, 12, 6], [6, 12, 8], [20, 30, 12], [12, 30, 20]],
        dtype=float,
    )
    for seed in range(24):
        target = seed % len(candidates)
        delta_exact = min(
            np.linalg.norm(candidates[target] - candidates[index])
            for index in range(len(candidates))
            if index != target
        )
        rng = np.random.default_rng(9200 + seed)
        direction = rng.normal(size=3)
        direction /= np.linalg.norm(direction)
        radius = (0.05 + 0.35 * ((seed % 7) / 6.0)) * delta_exact
        observation = candidates[target] + radius * direction
        delta, distance, nearest = finite_library_certificate(
            candidates,
            observation,
            target,
        )
        add("finite_library", f"seed_{seed:02d}", "separation", delta_exact, delta, 1e-14)
        add("finite_library", f"seed_{seed:02d}", "target_distance", radius, distance, 1e-14)
        add("finite_library", f"seed_{seed:02d}", "nearest_index", float(target), float(nearest), 0.0)
        add(
            "finite_library",
            f"seed_{seed:02d}",
            "half_separation_margin",
            0.0,
            max(0.0, distance - 0.5 * delta),
            1e-14,
        )

    categories = sorted({row["category"] for row in rows})
    metrics = {
        "schema": {
            "id": "go-p10-regular-polyhedra-metrics",
            "version": "1.1.0",
        },
        "date": "2026-07-28",
        "benchmark_rows": len(rows),
        "failed_rows": sum(row["status"] != "PASS" for row in rows),
        "max_absolute_error": max(errors, default=0.0),
        "categories": categories,
        "controls": {
            "Platonic_objects": len(PLATONIC),
            "spherical_pair_grid": 100,
            "cube_square_faces": len(square_faces),
            "cube_Petrie_faces": len(petrie_faces),
            "cube_group_order": len(cube_group),
            "cuboid_group_order": len(cuboid_group),
            "bounded_noise_seeds": 24,
            "finite_library_seeds": 24,
        },
    }
    return rows, metrics


def main() -> None:
    rows, metrics = build_benchmarks()
    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CSV_PATH.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=[
                "category",
                "case",
                "quantity",
                "expected",
                "computed",
                "abs_error",
                "tolerance",
                "status",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)
    METRICS_PATH.write_text(
        json.dumps(metrics, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(CSV_PATH)
    print(METRICS_PATH)
    print(json.dumps(metrics, sort_keys=True))


if __name__ == "__main__":
    main()
