#!/usr/bin/env python3
"""Independent P12 corpus-freeze and master-page regression tests."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import unittest
from collections import Counter, defaultdict, deque
from pathlib import Path
from typing import Any

import yaml
from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[3]
P12 = ROOT / "work/p12_corpus_master_v1_3"
BASELINE = (
    ROOT / "work/p11_satellite_networks_v1_2/ledgers/corpus_ledgers_v1_2.yaml"
)
FREEZE = P12 / "ledgers/go_corpus_freeze_ledger_v1_3.yaml"
CONTRACT = P12 / "core/go_corpus_freeze_contract_v1_3.yaml"
DEPENDENCIES = P12 / "ledgers/go_corpus_dependencies_v1_3.yaml"
PAGE_MAP = P12 / "ledgers/MASTER_PAGE_MAP_v1_3.json"
MASTER = (
    P12 / "build/master/Geometry_of_Observation_Corpus_Master_v1_3.pdf"
)
FRONT = (
    P12
    / "build/frontmatter/"
    "geometry_of_observation_corpus_master_frontmatter_v1_3.pdf"
)
CHECKSUMS = P12 / "SHA256SUMS_v1_3.txt"
GO_LINT = ROOT / "work/go_core_v0_2/src/go_lint.py"
GO_CORE = ROOT / "work/go_core_v0_2/core"
A4 = (595.28, 841.89)


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as stream:
        data = yaml.safe_load(stream)
    if not isinstance(data, dict):
        raise ValueError(path)
    return data


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def page_size(page: Any) -> tuple[float, float]:
    return round(float(page.mediabox.width), 2), round(
        float(page.mediabox.height), 2
    )


def page_content_hash(page: Any) -> str:
    digest = hashlib.sha256()
    digest.update(str(page_size(page)).encode("ascii"))
    digest.update(str(int(page.get("/Rotate", 0))).encode("ascii"))
    contents = page.get_contents()
    data = b"" if contents is None else contents.get_data()
    digest.update(len(data).to_bytes(8, "big"))
    digest.update(data)
    return digest.hexdigest()


def page_text_hash(page: Any) -> str:
    text = page.extract_text() or ""
    normalized = "\n".join(line.rstrip() for line in text.splitlines()).strip()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


class P12CorpusMasterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.baseline = load_yaml(BASELINE)
        cls.freeze = load_yaml(FREEZE)
        cls.contract = load_yaml(CONTRACT)
        cls.dependencies = load_yaml(DEPENDENCIES)
        cls.page_map = json.loads(PAGE_MAP.read_text(encoding="utf-8"))
        cls.master_reader = PdfReader(MASTER)
        cls.front_reader = PdfReader(FRONT)
        cls.modules = {
            item["id"]: item for item in cls.freeze.get("modules", [])
        }
        cls.page_entries = {
            item["id"]: item
            for item in cls.page_map.get("entries", [])
            if item.get("kind") == "normative_module"
        }

        module_ids = list(cls.modules)
        cls.expanded_nodes = {
            str(item["id"]) for item in cls.dependencies.get("nodes", [])
        }
        cls.expanded_nodes.update(module_ids)
        cls.expanded_edges = [
            dict(item) for item in cls.dependencies.get("edges", [])
        ]
        global_edge = cls.dependencies["global_core_edge"]
        cls.expanded_edges.extend(
            {
                "from": global_edge["from"],
                "to": module_id,
                "kind": global_edge["kind"],
                "expanded": True,
            }
            for module_id in module_ids
        )

    def test_001_baseline_schema(self) -> None:
        self.assertEqual(self.baseline["schema"]["id"], "go-corpus-ledgers")
        self.assertEqual(self.baseline["schema"]["version"], "1.2.0")
        self.assertEqual(self.baseline["schema"]["canonical_documents"], 18)

    def test_002_baseline_document_count_and_ids(self) -> None:
        ids = [item["id"] for item in self.baseline["documents"]]
        self.assertEqual(len(ids), 18)
        self.assertEqual(len(set(ids)), 18)

    def test_003_freeze_schema_and_status(self) -> None:
        self.assertEqual(
            self.freeze["schema"],
            {
                "id": "go-corpus-freeze-ledger",
                "version": "1.3.0",
                "date": "2026-07-28",
                "phase": "P12",
            },
        )
        self.assertEqual(self.freeze["status"], "CORPUS_FREEZE")

    def test_004_freeze_baseline_hash(self) -> None:
        record = self.freeze["baseline"]
        self.assertEqual(record["path"], str(BASELINE.relative_to(ROOT)))
        self.assertEqual(record["bytes"], BASELINE.stat().st_size)
        self.assertEqual(record["sha256"], sha256(BASELINE))

    def test_005_exact_corpus_totals(self) -> None:
        totals = self.freeze["corpus_totals"]
        self.assertEqual(totals["modules"], 18)
        self.assertEqual(totals["component_pages"], 158)
        self.assertEqual(totals["front_matter_pages"], 8)
        self.assertEqual(totals["master_pages"], 166)
        self.assertEqual(totals["maps"], 131)
        self.assertEqual(totals["symbols"], 132)
        self.assertEqual(totals["quantities"], 559)
        self.assertEqual(totals["expressions"], 347)
        self.assertEqual(totals["invariants"], 45)
        self.assertEqual(totals["claims"], 136)
        self.assertEqual(
            totals["corpus_statuses"],
            {"PASS": 18, "FAIL": 0, "BLOCKED": 0},
        )
        self.assertEqual(totals["findings"], 0)

    def test_006_claim_status_distribution(self) -> None:
        self.assertEqual(
            self.freeze["corpus_totals"]["claim_statuses"],
            {
                "corollary": 5,
                "diagnostic": 7,
                "empirical": 1,
                "hypothesis": 11,
                "model": 14,
                "proposition": 53,
                "theorem": 45,
            },
        )

    def test_007_strong_claim_count(self) -> None:
        statuses = self.freeze["corpus_totals"]["claim_statuses"]
        strong = sum(
            statuses.get(status, 0)
            for status in ("lemma", "proposition", "theorem", "corollary")
        )
        self.assertEqual(strong, 103)

    def test_008_canonical_release_order(self) -> None:
        indices = [item["release_index"] for item in self.freeze["modules"]]
        self.assertEqual(indices, list(range(1, 19)))
        self.assertEqual(
            self.freeze["modules"][-1]["id"],
            "satellite-networks-observation-v1-2",
        )

    def test_009_ledger_order_is_recorded_separately(self) -> None:
        ledger_indices = {
            item["id"]: item["ledger_index"] for item in self.freeze["modules"]
        }
        self.assertEqual(ledger_indices["satellite-networks-observation-v1-2"], 9)
        self.assertEqual(ledger_indices["lhc-beam-observation-v1-3"], 18)

    def test_010_namespace_totals_and_collisions(self) -> None:
        audit = self.freeze["namespace_audit"]
        self.assertEqual(audit["qualified_expression_and_claim_ids"], 483)
        self.assertEqual(audit["short_identifier_overlap_count"], 7)
        self.assertEqual(audit["qualified_collisions"], 0)
        self.assertEqual(audit["map_id_collisions"], 0)
        self.assertEqual(audit["quantity_id_collisions"], 0)

    def test_011_map_ids_are_globally_unique(self) -> None:
        identifiers = [
            item["id"]
            for document in self.baseline["documents"]
            for item in document.get("maps", [])
        ]
        self.assertEqual(len(identifiers), 131)
        self.assertEqual(len(set(identifiers)), 131)

    def test_012_quantity_ids_are_globally_unique(self) -> None:
        identifiers = [
            item["id"]
            for document in self.baseline["documents"]
            for item in document.get("quantities", [])
        ]
        self.assertEqual(len(identifiers), 559)
        self.assertEqual(len(set(identifiers)), 559)

    def test_013_fully_qualified_local_ids_are_unique(self) -> None:
        qualified = []
        for document in self.baseline["documents"]:
            for field in ("expressions", "claim_register"):
                qualified.extend(
                    f"{document['id']}::{item['id']}"
                    for item in document.get(field, [])
                )
        self.assertEqual(len(qualified), 483)
        self.assertEqual(len(qualified), len(set(qualified)))

    def test_014_dependency_counts(self) -> None:
        audit = self.freeze["dependency_audit"]
        self.assertEqual(audit["nodes"], 29)
        self.assertEqual(audit["edges"], 36)
        self.assertTrue(audit["acyclic"])
        self.assertEqual(audit["contextual_relations_excluded"], 3)

    def test_015_dependency_endpoint_completeness(self) -> None:
        for edge in self.expanded_edges:
            self.assertIn(edge["from"], self.expanded_nodes)
            self.assertIn(edge["to"], self.expanded_nodes)

    def test_016_dependency_dag(self) -> None:
        adjacency: defaultdict[str, list[str]] = defaultdict(list)
        indegree = {node_id: 0 for node_id in self.expanded_nodes}
        for edge in self.expanded_edges:
            adjacency[edge["from"]].append(edge["to"])
            indegree[edge["to"]] += 1
        queue = deque(sorted(node for node, degree in indegree.items() if degree == 0))
        visited = []
        while queue:
            node = queue.popleft()
            visited.append(node)
            for target in sorted(adjacency[node]):
                indegree[target] -= 1
                if indegree[target] == 0:
                    queue.append(target)
        self.assertEqual(len(visited), 29)
        self.assertEqual(set(visited), self.expanded_nodes)

    def test_017_dependency_topological_record(self) -> None:
        topological = self.freeze["dependency_audit"]["topological_order"]
        self.assertEqual(len(topological), 29)
        positions = {node_id: index for index, node_id in enumerate(topological)}
        for edge in self.expanded_edges:
            self.assertLess(positions[edge["from"]], positions[edge["to"]])

    def test_018_contextual_relations_are_excluded(self) -> None:
        normative_pairs = {
            (edge["from"], edge["to"]) for edge in self.expanded_edges
        }
        for relation in self.dependencies[
            "contextual_relations_not_in_normative_graph"
        ]:
            self.assertNotIn(
                (relation["from"], relation["to"]),
                normative_pairs,
            )

    def test_019_master_logical_properties(self) -> None:
        reader = self.master_reader
        self.assertEqual(len(reader.pages), 166)
        self.assertFalse(reader.is_encrypted)
        self.assertEqual(reader.get_fields() or {}, {})
        self.assertEqual(reader.metadata.title, self.freeze["release_identity"]["title"])
        self.assertEqual(reader.metadata.author, "Stassis Stashkevichyus")

    def test_020_master_a4_geometry(self) -> None:
        self.assertEqual(
            {page_size(page) for page in self.master_reader.pages},
            {A4},
        )

    def test_021_frontmatter_properties(self) -> None:
        self.assertEqual(len(self.front_reader.pages), 8)
        self.assertEqual(
            {page_size(page) for page in self.front_reader.pages},
            {A4},
        )
        self.assertEqual(
            self.front_reader.metadata.author,
            "Stassis Stashkevichyus",
        )

    def test_022_master_outline_and_labels(self) -> None:
        self.assertEqual(len(self.master_reader.outline), 19)
        labels = self.master_reader.page_labels
        self.assertEqual(len(labels), 166)
        self.assertEqual(labels[:8], ["i", "ii", "iii", "iv", "v", "vi", "vii", "viii"])
        self.assertEqual(labels[8], "M01-1")
        self.assertEqual(labels[-1], "M18-8")

    def test_023_master_eof_and_header(self) -> None:
        content = MASTER.read_bytes()
        self.assertTrue(content.startswith(b"%PDF-"))
        self.assertTrue(content.rstrip().endswith(b"%%EOF"))

    def test_024_page_map_contiguity(self) -> None:
        entries = self.page_map["entries"]
        self.assertEqual(len(entries), 19)
        cursor = 1
        for entry in entries:
            self.assertEqual(entry["master_page_start"], cursor)
            self.assertEqual(
                entry["master_page_end"] - entry["master_page_start"] + 1,
                entry["component_pages"],
            )
            cursor = entry["master_page_end"] + 1
        self.assertEqual(cursor, 167)

    def test_025_page_map_master_hash(self) -> None:
        self.assertEqual(self.page_map["master_pdf_sha256"], sha256(MASTER))
        self.assertEqual(self.page_map["master_pages"], 166)

    def test_026_freeze_master_record(self) -> None:
        record = self.freeze["master_artifact"]
        self.assertEqual(record["pages"], 166)
        self.assertEqual(record["bytes"], MASTER.stat().st_size)
        self.assertEqual(record["sha256"], sha256(MASTER))
        self.assertEqual(
            record["component_embedding_policy"],
            "unchanged_page_content_streams",
        )

    def test_027_auxiliary_passport_not_counted(self) -> None:
        auxiliaries = self.freeze["auxiliary_documents"]
        self.assertEqual(len(auxiliaries), 1)
        self.assertEqual(auxiliaries[0]["id"], "si-hep-quantity-passport-v0-5")
        self.assertFalse(auxiliaries[0]["module_counted"])

    def test_028_author_identity_across_metadata(self) -> None:
        release = self.freeze["release_identity"]
        self.assertEqual(release["author"], "Stassis Stashkevichyus")
        self.assertEqual(release["orcid"], "0009-0000-2294-705X")
        self.assertIsNone(release["doi"])
        self.assertEqual(
            set(release["component_pdf_author_variants"]),
            {"Stas, Independent Research Program", "Stassis Research Program"},
        )

    def test_029_citation_cff(self) -> None:
        citation = load_yaml(P12 / "metadata/CITATION.cff")
        self.assertEqual(citation["cff-version"], "1.2.0")
        self.assertEqual(citation["version"], "1.3.0")
        self.assertEqual(citation["type"], "dataset")
        author = citation["authors"][0]
        self.assertEqual(author["family-names"], "Stashkevichyus")
        self.assertEqual(author["given-names"], "Stassis")
        self.assertEqual(
            author["orcid"],
            "https://orcid.org/0009-0000-2294-705X",
        )
        self.assertNotIn("identifiers", citation)

    def test_030_zenodo_metadata(self) -> None:
        zenodo = json.loads(
            (P12 / "metadata/.zenodo.json").read_text(encoding="utf-8")
        )
        self.assertEqual(zenodo["upload_type"], "publication")
        self.assertEqual(zenodo["publication_type"], "preprint")
        self.assertEqual(zenodo["version"], "1.3.0")
        self.assertEqual(zenodo["license"], "cc-by-nc-nd-4.0")
        self.assertEqual(zenodo["creators"][0]["orcid"], "0009-0000-2294-705X")
        self.assertNotIn("doi", zenodo)

    def test_031_osf_metadata(self) -> None:
        osf = load_yaml(P12 / "metadata/OSF_RELEASE_METADATA_v1_3.yaml")
        self.assertEqual(osf["version"], "1.3.0")
        self.assertEqual(
            osf["creator"]["orcid"],
            "https://orcid.org/0009-0000-2294-705X",
        )
        self.assertIsNone(osf["doi"])
        self.assertIn("no placeholder component DOIs", osf["doi_policy"])

    def test_032_metadata_has_no_placeholders(self) -> None:
        paths = [
            P12 / "metadata/CITATION.cff",
            P12 / "metadata/.zenodo.json",
            P12 / "metadata/OSF_RELEASE_METADATA_v1_3.yaml",
        ]
        prohibited = [
            "TODO",
            "TBD",
            "example.com",
            "10.5281/zenodo.",
            "0000-0000-0000-0000",
        ]
        text = "\n".join(path.read_text(encoding="utf-8") for path in paths)
        for token in prohibited:
            self.assertNotIn(token, text)

    def test_033_license_record(self) -> None:
        text = (P12 / "LICENSE.md").read_text(encoding="utf-8")
        self.assertIn("CC BY-NC-ND 4.0", text)
        self.assertIn(
            "https://creativecommons.org/licenses/by-nc-nd/4.0/",
            text,
        )
        self.assertIn("Stassis Stashkevichyus", text)

    def test_034_freeze_contract_identity(self) -> None:
        identity = self.contract["release_identity"]
        self.assertEqual(identity["author"]["name"], "Stassis Stashkevichyus")
        self.assertEqual(identity["author"]["orcid"], "0009-0000-2294-705X")
        self.assertIsNone(identity["doi"])
        self.assertEqual(identity["license"]["id"], "CC-BY-NC-ND-4.0")

    def test_035_freeze_contract_gates(self) -> None:
        gate_ids = {
            item["id"] for item in self.contract["validation_gates"]
        }
        self.assertEqual(
            gate_ids,
            {
                "FREEZE-PATHS",
                "FREEZE-HASHES",
                "FREEZE-PAGES",
                "CORE-REPLAY",
                "NAMESPACE-QUALIFICATION",
                "DEPENDENCY-DAG",
                "DEPENDENCY-EVIDENCE",
                "PHASE-REPLAY",
                "PDF-LOGICAL",
                "PDF-FONTS",
                "MASTER-PAGE-PRESERVATION",
                "METADATA",
                "ARCHIVE",
            },
        )

    def test_036_claim_firewall(self) -> None:
        firewall = set(self.contract["claim_firewall"])
        self.assertIn("not_a_theory_of_everything", firewall)
        self.assertIn("not_a_cross_domain_physical_equivalence_proof", firewall)
        self.assertIn("not_a_new_quantum_chemistry_method", firewall)
        self.assertIn("not_a_new_astrodynamics_method", firewall)

    def test_037_checksums_are_sorted_and_exact(self) -> None:
        lines = [
            line
            for line in CHECKSUMS.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        paths = [line.split("  ", 1)[1] for line in lines]
        self.assertEqual(paths, sorted(paths))
        self.assertEqual(len(paths), len(set(paths)))
        for line in lines:
            expected, path_text = line.split("  ", 1)
            path = ROOT / path_text
            self.assertTrue(path.is_file(), path_text)
            self.assertEqual(sha256(path), expected, path_text)

    def test_038_frontmatter_log_has_no_layout_warnings(self) -> None:
        log = (
            P12
            / "build/frontmatter/"
            "geometry_of_observation_corpus_master_frontmatter_v1_3.log"
        ).read_text(encoding="utf-8", errors="replace")
        pattern = re.compile(
            r"Overfull|Underfull|undefined references|multiply defined|"
            r"Missing character|LaTeX Warning"
        )
        self.assertIsNone(pattern.search(log))

    def test_039_frontmatter_required_text(self) -> None:
        text = "\n".join(page.extract_text() or "" for page in self.front_reader.pages)
        required = [
            "The frozen release object",
            "Common typed architecture",
            "Inter-module dependency audit",
            "Namespaces and symbol discipline",
            "Metadata normalization and provenance",
            "Validation and reproducibility",
            "Master claim firewall",
            "Stassis Stashkevichyus",
            "0009-0000-2294-705X",
        ]
        for fragment in required:
            self.assertIn(fragment, text)

    def test_040_go_core_strict_replay(self) -> None:
        process = subprocess.run(
            [
                "python3",
                str(GO_LINT),
                "--core-dir",
                str(GO_CORE),
                "--ledger",
                str(BASELINE),
                "--only-level",
                "reference",
                "--mode",
                "strict",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(process.returncode, 0, process.stdout + process.stderr)
        self.assertIn("documents=18", process.stdout)
        self.assertIn("expressions=347", process.stdout)
        self.assertIn("findings=0", process.stdout)


def make_module_test(module_id: str):
    def test(self: P12CorpusMasterTests) -> None:
        record = self.modules[module_id]
        source = record["source"]
        pdf = ROOT / source["pdf"]
        tex = ROOT / source["tex"]
        self.assertTrue(pdf.is_file())
        self.assertTrue(tex.is_file())
        self.assertEqual(pdf.stat().st_size, source["pdf_bytes"])
        self.assertEqual(tex.stat().st_size, source["tex_bytes"])
        self.assertEqual(sha256(pdf), source["pdf_sha256"])
        self.assertEqual(sha256(tex), source["tex_sha256"])
        reader = PdfReader(pdf)
        self.assertEqual(len(reader.pages), source["pages"])
        self.assertFalse(reader.is_encrypted)
        self.assertEqual(reader.get_fields() or {}, {})
        self.assertEqual({page_size(page) for page in reader.pages}, {A4})
        self.assertEqual(reader.metadata.title, source["pdf_title"])
        self.assertEqual(reader.metadata.author, source["pdf_author"])
        self.assertEqual(self.page_entries[module_id]["pdf_sha256"], sha256(pdf))

    return test


def make_page_preservation_test(module_id: str, component_page: int):
    def test(self: P12CorpusMasterTests) -> None:
        record = self.modules[module_id]
        source_reader = PdfReader(ROOT / record["source"]["pdf"])
        entry = self.page_entries[module_id]
        master_index = entry["master_page_start"] - 1 + component_page
        source_page = source_reader.pages[component_page]
        master_page = self.master_reader.pages[master_index]
        self.assertEqual(page_size(master_page), page_size(source_page))
        self.assertEqual(
            int(master_page.get("/Rotate", 0)),
            int(source_page.get("/Rotate", 0)),
        )
        self.assertEqual(
            page_content_hash(master_page),
            page_content_hash(source_page),
        )
        self.assertEqual(
            page_text_hash(master_page),
            page_text_hash(source_page),
        )

    return test


def make_dependency_edge_test(edge_index: int):
    def test(self: P12CorpusMasterTests) -> None:
        edge = self.expanded_edges[edge_index]
        self.assertIn(edge["kind"], {"core_contract", "extension_contract", "documented_interface"})
        self.assertIn(edge["from"], self.expanded_nodes)
        self.assertIn(edge["to"], self.expanded_nodes)
        evidence = edge.get("evidence")
        if isinstance(evidence, dict):
            source = ROOT / evidence["source"]
            self.assertTrue(source.is_file())
            self.assertIn(
                evidence["fragment"],
                source.read_text(encoding="utf-8", errors="replace"),
            )
        if edge["kind"] == "documented_interface":
            self.assertIsInstance(evidence, dict)

    return test


def make_overlap_test(overlap_index: int):
    def test(self: P12CorpusMasterTests) -> None:
        overlap = self.freeze["namespace_audit"]["short_identifier_overlaps"][
            overlap_index
        ]
        self.assertIn(overlap["field"], {"expressions", "claim_register"})
        self.assertGreaterEqual(len(overlap["documents"]), 2)
        qualified = {
            f"{document_id}::{overlap['local_id']}"
            for document_id in overlap["documents"]
        }
        self.assertEqual(len(qualified), len(overlap["documents"]))

    return test


_freeze_for_generation = load_yaml(FREEZE)
for _module in _freeze_for_generation["modules"]:
    _safe_id = re.sub(r"[^a-zA-Z0-9]+", "_", _module["id"]).strip("_")
    setattr(
        P12CorpusMasterTests,
        f"test_module_{_module['release_index']:02d}_{_safe_id}",
        make_module_test(_module["id"]),
    )
    for _page_index in range(_module["source"]["pages"]):
        setattr(
            P12CorpusMasterTests,
            (
                f"test_page_{_module['release_index']:02d}_"
                f"{_page_index + 1:02d}_{_safe_id}"
            ),
            make_page_preservation_test(_module["id"], _page_index),
        )

_dependency_for_generation = load_yaml(DEPENDENCIES)
_edge_count = len(_dependency_for_generation["edges"]) + 18
for _edge_index in range(_edge_count):
    setattr(
        P12CorpusMasterTests,
        f"test_dependency_edge_{_edge_index + 1:02d}",
        make_dependency_edge_test(_edge_index),
    )

for _overlap_index in range(
    _freeze_for_generation["namespace_audit"]["short_identifier_overlap_count"]
):
    setattr(
        P12CorpusMasterTests,
        f"test_namespace_overlap_{_overlap_index + 1:02d}",
        make_overlap_test(_overlap_index),
    )


if __name__ == "__main__":
    unittest.main()
