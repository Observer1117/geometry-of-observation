#!/usr/bin/env python3
"""Independent regressions for the P10 regular-polyhedra release."""

from __future__ import annotations

import csv
import hashlib
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
P10 = ROOT / "work/p10_regular_polyhedra_v1_1"
sys.path.insert(0, str(P10 / "scripts"))

from generate_regular_polyhedra_benchmarks import (  # noqa: E402
    PLATONIC,
    canonical_cycle,
    cube_edges,
    cube_petrie_faces,
    cube_square_faces,
    cube_transforms,
    cube_vertices,
    cycle_edges,
    finite_library_certificate,
    flags_from_faces,
    orbit_entropy,
    orbit_partition,
    spherical_type_pairs,
    symmetry_residual,
)


PDF = P10 / "build/polyhedra/regular_polyhedra_observation_filters_v1_1.pdf"
TEX = P10 / "src/regular_polyhedra_observation_filters_v1_1.tex"
TEXT = P10 / "checks/polyhedra/regular_polyhedra_observation_filters_v1_1.txt"
LOG = P10 / "build/polyhedra/regular_polyhedra_observation_filters_v1_1.log"
CONTRACT = P10 / "core/regular_polyhedra_observation_contract_v1_1.yaml"
REFERENCE_LEDGER = (
    P10 / "ledgers/regular_polyhedra_reference_ledger_v1_1.yaml"
)
CORPUS_LEDGER = P10 / "ledgers/corpus_ledgers_v1_1.yaml"
REFERENCE_LINT = (
    P10 / "reports/Regular_Polyhedra_Reference_Lint_Report_v1_1.json"
)
CORPUS_LINT = P10 / "reports/GO_Corpus_Lint_Report_v1_1.json"
BENCHMARKS = P10 / "data/regular_polyhedra_benchmarks_v1_1.csv"
METRICS = P10 / "data/regular_polyhedra_metrics_v1_1.json"


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


class PlatonicIncidenceTests(unittest.TestCase):
    def test_reference_table_has_five_objects(self) -> None:
        self.assertEqual(len(PLATONIC), 5)

    def test_spherical_pairs_are_exact(self) -> None:
        self.assertEqual(
            set(spherical_type_pairs(20)),
            {(3, 3), (4, 3), (3, 4), (5, 3), (3, 5)},
        )

    def test_all_reference_objects_satisfy_double_counting(self) -> None:
        for item in PLATONIC:
            with self.subTest(item=item["name"]):
                self.assertEqual(item["p"] * item["F"], 2 * item["E"])
                self.assertEqual(item["q"] * item["V"], 2 * item["E"])

    def test_all_reference_objects_are_spherical(self) -> None:
        for item in PLATONIC:
            with self.subTest(item=item["name"]):
                self.assertEqual(item["V"] - item["E"] + item["F"], 2)

    def test_spherical_identity(self) -> None:
        for item in PLATONIC:
            with self.subTest(item=item["name"]):
                self.assertAlmostEqual(
                    1.0 / item["p"] + 1.0 / item["q"] - 0.5,
                    1.0 / item["E"],
                )

    def test_flag_counts(self) -> None:
        expected = {
            "tetrahedron": 24,
            "cube": 48,
            "octahedron": 48,
            "dodecahedron": 120,
            "icosahedron": 120,
        }
        self.assertEqual(
            {item["name"]: 4 * item["E"] for item in PLATONIC},
            expected,
        )

    def test_dual_pairs(self) -> None:
        by_type = {(item["p"], item["q"]): item for item in PLATONIC}
        for item in PLATONIC:
            dual = by_type[(item["q"], item["p"])]
            self.assertEqual((dual["V"], dual["E"], dual["F"]), (item["F"], item["E"], item["V"]))

    def test_no_other_pair_below_twenty_is_spherical(self) -> None:
        accepted = set(spherical_type_pairs(20))
        for p in range(3, 21):
            for q in range(3, 21):
                self.assertEqual(
                    (p, q) in accepted,
                    1.0 / p + 1.0 / q > 0.5,
                )

    def test_type_symbol_not_registered_as_complete_identifier(self) -> None:
        prohibitions = load_yaml(CONTRACT)["string_C_group_layer"]["prohibitions"]
        self.assertIn(
            "Schlafli_type_is_not_a_complete_global_identifier",
            prohibitions,
        )


class CubePetrialTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.vertices = cube_vertices()
        cls.edges = cube_edges()
        cls.square_faces = cube_square_faces()
        cls.petrie_faces = cube_petrie_faces()
        cls.square_flags = flags_from_faces(cls.square_faces)
        cls.petrie_flags = flags_from_faces(cls.petrie_faces)

    def test_cube_inventory(self) -> None:
        self.assertEqual((len(self.vertices), len(self.edges)), (8, 12))

    def test_square_face_inventory(self) -> None:
        self.assertEqual(len(self.square_faces), 6)
        self.assertEqual({len(face) for face in self.square_faces}, {4})

    def test_Petrie_face_inventory(self) -> None:
        self.assertEqual(len(self.petrie_faces), 4)
        self.assertEqual({len(face) for face in self.petrie_faces}, {6})

    def test_all_face_edges_belong_to_cube_skeleton(self) -> None:
        for face in self.square_faces + self.petrie_faces:
            self.assertTrue(cycle_edges(face) <= self.edges)

    def test_each_cube_edge_has_two_square_faces(self) -> None:
        counts = {
            edge: sum(edge in cycle_edges(face) for face in self.square_faces)
            for edge in self.edges
        }
        self.assertEqual(set(counts.values()), {2})

    def test_each_cube_edge_has_two_Petrie_faces(self) -> None:
        counts = {
            edge: sum(edge in cycle_edges(face) for face in self.petrie_faces)
            for edge in self.edges
        }
        self.assertEqual(set(counts.values()), {2})

    def test_square_and_Petrie_flag_counts(self) -> None:
        self.assertEqual(len(self.square_flags), 48)
        self.assertEqual(len(self.petrie_flags), 48)

    def test_face_systems_are_distinct(self) -> None:
        square_sets = {frozenset(face) for face in self.square_faces}
        petrie_sets = {frozenset(face) for face in self.petrie_faces}
        self.assertTrue(square_sets.isdisjoint(petrie_sets))

    def test_Euler_characteristics_differ(self) -> None:
        self.assertEqual(8 - 12 + len(self.square_faces), 2)
        self.assertEqual(8 - 12 + len(self.petrie_faces), 0)

    def test_canonical_cycle_is_rotation_and_reversal_invariant(self) -> None:
        cycle = self.petrie_faces[0]
        for offset in range(len(cycle)):
            rotated = cycle[offset:] + cycle[:offset]
            self.assertEqual(canonical_cycle(rotated), canonical_cycle(cycle))
            self.assertEqual(
                canonical_cycle(tuple(reversed(rotated))),
                canonical_cycle(cycle),
            )

    def test_contract_registers_skeleton_noninjectivity(self) -> None:
        layer = load_yaml(CONTRACT)["duality_and_Petrial"]
        self.assertEqual(layer["cube_control"]["cube_f_vector"], [8, 12, 6])
        self.assertEqual(layer["cube_control"]["cube_Petrial_f_vector"], [8, 12, 4])


class FlagOrbitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.square_flags = flags_from_faces(cube_square_faces())
        cls.petrie_flags = flags_from_faces(cube_petrie_faces())
        cls.cube_group = cube_transforms(allow_axis_permutations=True)
        cls.cuboid_group = cube_transforms(allow_axis_permutations=False)

    def test_group_orders(self) -> None:
        self.assertEqual(len(self.cube_group), 48)
        self.assertEqual(len(self.cuboid_group), 8)

    def test_cube_is_geometrically_flag_transitive(self) -> None:
        orbits = orbit_partition(self.square_flags, self.cube_group)
        self.assertEqual([len(orbit) for orbit in orbits], [48])

    def test_Petrial_is_flag_transitive_under_cube_group(self) -> None:
        orbits = orbit_partition(self.petrie_flags, self.cube_group)
        self.assertEqual([len(orbit) for orbit in orbits], [48])

    def test_generic_cuboid_has_six_flag_orbits(self) -> None:
        orbits = orbit_partition(self.square_flags, self.cuboid_group)
        self.assertEqual(sorted(len(orbit) for orbit in orbits), [8] * 6)

    def test_regular_orbit_entropy_is_zero(self) -> None:
        self.assertEqual(orbit_entropy([48]), 0.0)

    def test_cuboid_orbit_entropy_is_log_two_six(self) -> None:
        self.assertAlmostEqual(
            orbit_entropy([8, 8, 8, 8, 8, 8]),
            math.log2(6.0),
        )

    def test_entropy_rejects_empty_orbits(self) -> None:
        with self.assertRaises(ValueError):
            orbit_entropy([])

    def test_entropy_rejects_nonpositive_orbits(self) -> None:
        with self.assertRaises(ValueError):
            orbit_entropy([2, 0])

    def test_entropy_rejects_unit_base(self) -> None:
        with self.assertRaises(ValueError):
            orbit_entropy([1, 1], base=1.0)

    def test_contract_separates_abstract_and_geometric_groups(self) -> None:
        layer = load_yaml(CONTRACT)["symmetry_layer"]
        self.assertEqual(layer["abstract_group"]["definition"], "Aut(P)")
        self.assertFalse(
            layer["implication"]["abstract_regular_implies_given_realization_geometric_regular"]
        )
        self.assertEqual(layer["counterexample"]["geometric_flag_orbits"], 6)


class ObservationOrderTests(unittest.TestCase):
    def test_admissibility_and_information_orders_are_distinct(self) -> None:
        layer = load_yaml(CONTRACT)["observation_specification"]
        self.assertIn("full_subgroupoid", layer["admissibility_preorder"]["formula"])
        self.assertIn("kappa", layer["information_preorder"]["formula"])
        self.assertTrue(
            layer["independence"]["admission_does_not_imply_information_refinement"]
        )

    def test_historical_filters_are_not_forced_to_a_chain(self) -> None:
        layer = load_yaml(CONTRACT)["observation_specification"]
        self.assertFalse(layer["independence"]["historical_relaxations_form_total_chain"])

    def test_kernel_variance_is_correct(self) -> None:
        layer = load_yaml(CONTRACT)["observation_specification"]
        self.assertEqual(
            layer["information_preorder"]["kernel_law"],
            "kernel_Q_fine_subset_kernel_Q_coarse",
        )

    def test_count_firewall(self) -> None:
        counts = load_yaml(CONTRACT)["count_firewall"]
        self.assertEqual(counts["Platonic"]["count"], 5)
        self.assertEqual(counts["Kepler_Poinsot"]["count"], 4)
        self.assertEqual(counts["Schulte_skeletal_R3"]["count"], 48)
        self.assertEqual(
            counts["Schulte_skeletal_R3"]["finite"]
            + counts["Schulte_skeletal_R3"]["infinite"],
            48,
        )


class FiniteResolutionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.exact = np.asarray(cube_vertices(), dtype=float)
        cls.transform = np.diag([-1.0, 1.0, 1.0])
        transformed = cls.exact @ cls.transform.T
        lookup = {tuple(row): index for index, row in enumerate(cls.exact)}
        cls.permutation = np.asarray(
            [lookup[tuple(row)] for row in transformed],
            dtype=int,
        )

    def test_exact_symmetry_has_zero_residual(self) -> None:
        self.assertEqual(
            symmetry_residual(
                self.exact,
                self.exact,
                self.transform,
                self.permutation,
            ),
            0.0,
        )

    def test_uniform_translation_noise_respects_bound(self) -> None:
        epsilon = 0.03
        noise = np.tile(np.array([epsilon, 0.0, 0.0]), (8, 1))
        residual = symmetry_residual(
            self.exact,
            self.exact + noise,
            self.transform,
            self.permutation,
        )
        self.assertLessEqual(residual, 2.0 * epsilon + 1e-14)

    def test_residual_rejects_shape_mismatch(self) -> None:
        with self.assertRaises(ValueError):
            symmetry_residual(
                self.exact,
                self.exact[:, :2],
                self.transform,
                self.permutation,
            )

    def test_residual_rejects_nonbijective_permutation(self) -> None:
        with self.assertRaises(ValueError):
            symmetry_residual(
                self.exact,
                self.exact,
                self.transform,
                np.zeros(8, dtype=int),
            )

    def test_half_separation_certificate(self) -> None:
        candidates = np.asarray([[0.0, 0.0], [3.0, 0.0], [0.0, 4.0]])
        delta, distance, nearest = finite_library_certificate(
            candidates,
            np.asarray([0.4, 0.2]),
            0,
        )
        self.assertEqual(delta, 3.0)
        self.assertLess(distance, delta / 2.0)
        self.assertEqual(nearest, 0)

    def test_finite_library_rejects_bad_observation_shape(self) -> None:
        with self.assertRaises(ValueError):
            finite_library_certificate(
                np.eye(3),
                np.zeros(2),
                0,
            )

    def test_contract_forbids_exactness_from_tolerance(self) -> None:
        prohibitions = load_yaml(CONTRACT)["finite_resolution_layer"]["prohibitions"]
        self.assertIn(
            "approximate_residual_does_not_prove_exact_symmetry",
            prohibitions,
        )


class ReleaseArtifactTests(unittest.TestCase):
    def test_required_files_exist(self) -> None:
        for path in (
            PDF,
            TEX,
            TEXT,
            LOG,
            CONTRACT,
            REFERENCE_LEDGER,
            CORPUS_LEDGER,
            REFERENCE_LINT,
            CORPUS_LINT,
            BENCHMARKS,
            METRICS,
        ):
            self.assertTrue(path.is_file(), path)

    def test_PDF_hash_matches_reference_ledger(self) -> None:
        document = load_yaml(REFERENCE_LEDGER)["documents"][0]
        self.assertEqual(document["source"]["sha256"], sha256(PDF))

    def test_PDF_metadata_and_pages(self) -> None:
        reader = PdfReader(PDF)
        metadata = reader.metadata or {}
        self.assertEqual(len(reader.pages), 7)
        self.assertEqual(
            metadata.get("/Title"),
            "Regular Polyhedra under Typed Observation Filters",
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
        rows = [line.split() for line in result.stdout.splitlines()[2:] if line.strip()]
        self.assertTrue(rows)
        self.assertTrue(all(len(row) >= 7 and row[-5].lower() == "yes" for row in rows))

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
        self.assertGreater(len(content), 19_000)
        self.assertEqual(content.count("\f"), 7)
        self.assertIn("Half-separation certificate", content)
        self.assertEqual(
            sum(line.strip() == "References" for line in content.splitlines()),
            1,
        )

    def test_source_contains_required_fragments(self) -> None:
        content = TEX.read_text(encoding="utf-8")
        for fragment in (
            r"\section{Scope and the category of objects}",
            r"\section{Flags, abstract regularity, and string C-groups}",
            r"\section{Abstract symmetry versus realization symmetry}",
            r"\section{Observation specifications and two preorders}",
            r"\section{Skeleton non-identifiability and the Petrial control}",
            r"\section{Finite-resolution symmetry and identifiability}",
            r"\Ocal_1\preceq_{\rm adm}\Ocal_2",
            r"Q_{\rm coarse}=\kappa\circ Q_{\rm fine}",
            r"(\rho_0\rho_2,\rho_1,\rho_2)",
            r"r_Y(g)\le2\epsilon",
        ):
            self.assertIn(fragment, content)

    def test_no_prohibited_tokens(self) -> None:
        for path in (TEX, TEXT, CONTRACT, REFERENCE_LEDGER):
            content = path.read_text(encoding="utf-8", errors="replace")
            for token in ("TODO", "TBD", "PENDING", "\ufffd"):
                self.assertNotIn(token, content)

    def test_reference_lint_is_clean(self) -> None:
        summary = load_json(REFERENCE_LINT)["summary"]
        self.assertEqual(summary["canonical_documents"], 1)
        self.assertEqual(summary["reference_documents"], 1)
        self.assertEqual(summary["expressions_checked"], 42)
        self.assertEqual(summary["findings_total"], 0)
        self.assertEqual(summary["status_counts"], {"PASS": 1})

    def test_corpus_lint_has_only_satellite_failure(self) -> None:
        report = load_json(CORPUS_LINT)
        summary = report["summary"]
        self.assertEqual(summary["canonical_documents"], 18)
        self.assertEqual(summary["reference_documents"], 17)
        self.assertEqual(summary["critical_adapters"], 1)
        self.assertEqual(summary["expressions_checked"], 295)
        self.assertEqual(summary["findings_total"], 3)
        self.assertEqual(summary["status_counts"], {"FAIL": 1, "PASS": 17})
        failing = [
            item["id"] for item in report["documents"] if item["status"] != "PASS"
        ]
        self.assertEqual(failing, ["satellite-networks-v1-1"])

    def test_legacy_source_is_superseded_once(self) -> None:
        corpus = load_yaml(CORPUS_LEDGER)
        records = [
            item
            for item in corpus["duplicate_or_superseded_sources"]
            if "regular_polyhedra_observation" in item.get("path", "")
        ]
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["status"], "superseded")
        self.assertEqual(
            records[0]["canonical_document"],
            "regular-polyhedra-observation-v1-1",
        )

    def test_metrics_and_benchmarks_are_clean(self) -> None:
        metrics = load_json(METRICS)
        self.assertEqual(metrics["benchmark_rows"], 302)
        self.assertEqual(metrics["failed_rows"], 0)
        with BENCHMARKS.open("r", encoding="utf-8", newline="") as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual(len(rows), 302)
        self.assertTrue(all(row["status"] == "PASS" for row in rows))

    def test_contract_has_fifteen_reference_gates(self) -> None:
        contract = load_yaml(CONTRACT)
        self.assertEqual(contract["schema"]["version"], "1.1.0")
        self.assertEqual(len(contract["reference_gates"]), 15)


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
