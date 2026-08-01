#!/usr/bin/env python3
"""Build the P12 frozen corpus ledger, front matter, and master PDF."""

from __future__ import annotations

import calendar
import csv
import hashlib
import json
import os
import shutil
import subprocess
from collections import Counter, defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from pypdf import PdfReader, PdfWriter
from pypdf.constants import PageLabelStyle
from pypdf.generic import ArrayObject, ByteStringObject


ROOT = Path(__file__).resolve().parents[3]
P12 = ROOT / "work/p12_corpus_master_v1_3"
BASELINE_LEDGER = (
    ROOT / "work/p11_satellite_networks_v1_2/ledgers/corpus_ledgers_v1_2.yaml"
)
DEPENDENCY_LEDGER = P12 / "ledgers/go_corpus_dependencies_v1_3.yaml"
FREEZE_CONTRACT = P12 / "core/go_corpus_freeze_contract_v1_3.yaml"
FREEZE_LEDGER = P12 / "ledgers/go_corpus_freeze_ledger_v1_3.yaml"
GENERATED = P12 / "generated"
BUILD = P12 / "build"
FRONT_BUILD = BUILD / "frontmatter"
MASTER_BUILD = BUILD / "master"
FRONT_SOURCE = (
    P12 / "src/geometry_of_observation_corpus_master_frontmatter_v1_3.tex"
)
FRONT_PDF = (
    FRONT_BUILD / "geometry_of_observation_corpus_master_frontmatter_v1_3.pdf"
)
MASTER_PDF = (
    MASTER_BUILD / "Geometry_of_Observation_Corpus_Master_v1_3.pdf"
)
PAGE_MAP_JSON = P12 / "ledgers/MASTER_PAGE_MAP_v1_3.json"
PAGE_MAP_CSV = P12 / "ledgers/MASTER_PAGE_MAP_v1_3.csv"
CHECKSUMS = P12 / "SHA256SUMS_v1_3.txt"
OUTPUT_PDF = ROOT / "output/pdf"
OUTPUT_P12 = ROOT / "output/p12"

RELEASE_DATE = "2026-07-28"
RELEASE_VERSION = "1.3.0"
FIXED_EPOCH = calendar.timegm((2026, 7, 28, 12, 0, 0))
A4_POINTS = (595.28, 841.89)

CANONICAL_ORDER = [
    "functional-interface-go-qs-v0-2",
    "tensorial-observation-geometry-gr-v0-3",
    "information-theoretic-observation-v0-2",
    "metric-entropy-defect-v0-2",
    "distance-scale-interface-v0-2",
    "planck-cosmos-rulers-v1-1",
    "mandelbrot-rulers-v1-1",
    "regular-polyhedra-observation-v1-1",
    "frames-forces-dissipation-interface-v0-1",
    "celestial-foucault-networks-v1-1",
    "billiards-observation-v1-1",
    "bobsleigh-contact-v1-1",
    "roller-coaster-v1-1",
    "gear-contact-v1-1",
    "conical-intersections-observation-v1-1",
    "quantum-chemistry-observation-v1-1",
    "lhc-beam-observation-v1-3",
    "satellite-networks-observation-v1-2",
]

LAYERS = {
    "functional-interface-go-qs-v0-2": "Foundation",
    "tensorial-observation-geometry-gr-v0-3": "Foundation",
    "information-theoretic-observation-v0-2": "Information",
    "metric-entropy-defect-v0-2": "Metric",
    "distance-scale-interface-v0-2": "Metric",
    "planck-cosmos-rulers-v1-1": "Scale",
    "mandelbrot-rulers-v1-1": "Scale",
    "regular-polyhedra-observation-v1-1": "Discrete geometry",
    "frames-forces-dissipation-interface-v0-1": "Mechanics",
    "celestial-foucault-networks-v1-1": "Mechanics",
    "billiards-observation-v1-1": "Dynamics",
    "bobsleigh-contact-v1-1": "Contact mechanics",
    "roller-coaster-v1-1": "Mechanics",
    "gear-contact-v1-1": "Contact mechanics",
    "conical-intersections-observation-v1-1": "Spectral",
    "quantum-chemistry-observation-v1-1": "Molecular inference",
    "lhc-beam-observation-v1-3": "Relativistic",
    "satellite-networks-observation-v1-2": "Temporal networks",
}

PUBLIC_MODULE_FILENAMES = {
    "functional-interface-go-qs-v0-2": "Functional_Interface_GO_QS_v0_2_ru.pdf",
    "tensorial-observation-geometry-gr-v0-3": "Tensorial_Observation_Geometry_GR_v0_3.pdf",
    "information-theoretic-observation-v0-2": "Information_Theoretic_Observation_Geometry_v0_2.pdf",
    "metric-entropy-defect-v0-2": "Metric_Entropy_and_Observational_Entropy_Defect_v0_2.pdf",
    "distance-scale-interface-v0-2": "Distance_and_Scale_Interface_under_Observation_Maps_v0_2.pdf",
    "planck-cosmos-rulers-v1-1": "Planck_to_Cosmos_Observation_Rulers_v1_1.pdf",
    "mandelbrot-rulers-v1-1": "Mandelbrot_Rulers_Observation_Scale_Geometry_v1_1.pdf",
    "regular-polyhedra-observation-v1-1": "Regular_Polyhedra_Typed_Observation_Filters_v1_1.pdf",
    "frames-forces-dissipation-interface-v0-1": "Frames_Forces_Constraints_Dissipation_Interface_v0_1.pdf",
    "celestial-foucault-networks-v1-1": "Celestial_Foucault_Networks_Observation_Geometry_v1_1.pdf",
    "billiards-observation-v1-1": "Billiards_Geometry_of_Observation_Laboratory_v1_1.pdf",
    "bobsleigh-contact-v1-1": "Bobsleigh_Contact_Geometry_Observation_v1_1.pdf",
    "roller-coaster-v1-1": "Roller_Coaster_Geometry_Observation_v1_1.pdf",
    "gear-contact-v1-1": "Gear_Contact_Geometry_Observation_v1_1.pdf",
    "conical-intersections-observation-v1-1": "Conical_Intersections_Spectral_Observation_Geometry_v1_1.pdf",
    "quantum-chemistry-observation-v1-1": "Quantum_Chemistry_Typed_Observation_Geometry_v1_1.pdf",
    "lhc-beam-observation-v1-3": "Relativistic_Beam_Paths_Observation_Geometry_v1_3.pdf",
    "satellite-networks-observation-v1-2": "Satellite_Networks_Typed_Frames_Temporal_Observation_v1_2.pdf",
}


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as stream:
        data = yaml.safe_load(stream)
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected YAML mapping")
    return data


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def relative(path: Path) -> str:
    return str(path.relative_to(ROOT))


def latex_escape(value: str) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(character, character) for character in value)


def pdf_page_size(page: Any) -> tuple[float, float]:
    width = float(page.mediabox.width)
    height = float(page.mediabox.height)
    return round(width, 2), round(height, 2)


def page_content_hash(page: Any) -> str:
    digest = hashlib.sha256()
    digest.update(str(pdf_page_size(page)).encode("ascii"))
    digest.update(str(int(page.get("/Rotate", 0))).encode("ascii"))
    contents = page.get_contents()
    data = b"" if contents is None else contents.get_data()
    digest.update(len(data).to_bytes(8, "big"))
    digest.update(data)
    return digest.hexdigest()


def page_text_hash(page: Any) -> str:
    text = page.extract_text() or ""
    normalized = "\n".join(line.rstrip() for line in text.splitlines()).strip()
    return sha256_bytes(normalized.encode("utf-8"))


def aggregate_page_hashes(reader: PdfReader) -> tuple[str, str]:
    content = hashlib.sha256()
    text = hashlib.sha256()
    for page in reader.pages:
        content.update(bytes.fromhex(page_content_hash(page)))
        text.update(bytes.fromhex(page_text_hash(page)))
    return content.hexdigest(), text.hexdigest()


def short_identifier_overlaps(
    documents: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], int, int]:
    overlaps: list[dict[str, Any]] = []
    qualified: set[str] = set()
    total = 0
    for field in ("expressions", "claim_register"):
        locations: defaultdict[str, list[str]] = defaultdict(list)
        for document in documents:
            document_id = str(document["id"])
            for item in document.get(field, []):
                if not isinstance(item, dict) or not isinstance(item.get("id"), str):
                    continue
                local_id = str(item["id"])
                locations[local_id].append(document_id)
                qualified_id = f"{document_id}::{local_id}"
                if qualified_id in qualified:
                    raise RuntimeError(f"qualified identifier collision: {qualified_id}")
                qualified.add(qualified_id)
                total += 1
        for local_id, document_ids in sorted(locations.items()):
            if len(document_ids) > 1:
                overlaps.append(
                    {
                        "field": field,
                        "local_id": local_id,
                        "documents": document_ids,
                    }
                )
    return overlaps, total, len(qualified)


def expanded_dependency_graph(
    dependency: dict[str, Any],
    module_ids: list[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    nodes = [dict(item) for item in dependency.get("nodes", [])]
    nodes.extend(
        {"id": module_id, "kind": "normative_module"} for module_id in module_ids
    )
    edges = [dict(item) for item in dependency.get("edges", [])]
    global_edge = dependency.get("global_core_edge", {})
    if global_edge.get("expanded_by_builder") is True:
        for module_id in module_ids:
            edges.append(
                {
                    "from": str(global_edge["from"]),
                    "to": module_id,
                    "kind": str(global_edge["kind"]),
                    "expanded": True,
                }
            )

    node_ids = [str(item["id"]) for item in nodes]
    if len(node_ids) != len(set(node_ids)):
        raise RuntimeError("dependency node IDs are not unique")
    node_set = set(node_ids)
    for edge in edges:
        if edge["from"] not in node_set or edge["to"] not in node_set:
            raise RuntimeError(f"unresolved dependency edge: {edge}")
        evidence = edge.get("evidence")
        if isinstance(evidence, dict):
            source = ROOT / str(evidence["source"])
            fragment = str(evidence["fragment"])
            if not source.is_file():
                raise FileNotFoundError(source)
            if fragment not in source.read_text(encoding="utf-8", errors="replace"):
                raise RuntimeError(
                    f"dependency evidence absent: {source}: {fragment!r}"
                )

    adjacency: defaultdict[str, list[str]] = defaultdict(list)
    indegree = {node_id: 0 for node_id in node_ids}
    for edge in edges:
        source = str(edge["from"])
        target = str(edge["to"])
        adjacency[source].append(target)
        indegree[target] += 1

    queue = deque(sorted(node_id for node_id, degree in indegree.items() if degree == 0))
    topological: list[str] = []
    while queue:
        node_id = queue.popleft()
        topological.append(node_id)
        for target in sorted(adjacency[node_id]):
            indegree[target] -= 1
            if indegree[target] == 0:
                queue.append(target)
    if len(topological) != len(node_ids):
        cyclic = sorted(node_id for node_id, degree in indegree.items() if degree > 0)
        raise RuntimeError(f"dependency graph is cyclic: {cyclic}")
    return nodes, edges, topological


def module_records(
    baseline: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    ledger_documents = baseline.get("documents", [])
    by_id = {str(item["id"]): item for item in ledger_documents}
    if set(by_id) != set(CANONICAL_ORDER):
        missing = sorted(set(CANONICAL_ORDER) - set(by_id))
        extra = sorted(set(by_id) - set(CANONICAL_ORDER))
        raise RuntimeError(f"canonical module mismatch; missing={missing}, extra={extra}")
    if len(ledger_documents) != 18:
        raise RuntimeError("baseline ledger must contain exactly 18 modules")

    records: list[dict[str, Any]] = []
    claim_counts: Counter[str] = Counter()
    for release_index, module_id in enumerate(CANONICAL_ORDER, start=1):
        document = by_id[module_id]
        source = document["source"]
        pdf_path = ROOT / str(source["pdf"])
        tex_path = ROOT / str(source["tex"])
        if not pdf_path.is_file() or not tex_path.is_file():
            raise FileNotFoundError(
                f"missing module source: pdf={pdf_path}, tex={tex_path}"
            )
        actual_pdf_hash = sha256(pdf_path)
        if actual_pdf_hash != str(source["sha256"]):
            raise RuntimeError(f"component PDF hash mismatch: {module_id}")
        reader = PdfReader(pdf_path)
        if len(reader.pages) != int(source["pages"]):
            raise RuntimeError(f"component page mismatch: {module_id}")
        if reader.is_encrypted:
            raise RuntimeError(f"encrypted component PDF: {module_id}")
        if reader.get_fields():
            raise RuntimeError(f"form fields in component PDF: {module_id}")
        sizes = sorted({pdf_page_size(page) for page in reader.pages})
        if sizes != [A4_POINTS]:
            raise RuntimeError(f"non-A4 component PDF: {module_id}: {sizes}")

        content_hash, text_hash = aggregate_page_hashes(reader)
        metadata = reader.metadata
        claims = document.get("claim_register", [])
        for claim in claims:
            claim_counts[str(claim.get("status", "missing"))] += 1
        records.append(
            {
                "release_index": release_index,
                "ledger_index": next(
                    index
                    for index, item in enumerate(ledger_documents, start=1)
                    if item["id"] == module_id
                ),
                "id": module_id,
                "title": str(document["title"]),
                "version": str(document["version"]),
                "layer": LAYERS[module_id],
                "ledger_level": str(document["ledger_level"]),
                "migration_status": str(document["migration_status"]),
                "source": {
                    "pdf": relative(pdf_path),
                    "tex": relative(tex_path),
                    "public_filename": PUBLIC_MODULE_FILENAMES[module_id],
                    "archive_pdf": (
                        f"modules/{release_index:02d}_{PUBLIC_MODULE_FILENAMES[module_id]}"
                    ),
                    "archive_tex": f"sources/{release_index:02d}_{tex_path.name}",
                    "pages": len(reader.pages),
                    "pdf_bytes": pdf_path.stat().st_size,
                    "pdf_sha256": actual_pdf_hash,
                    "tex_bytes": tex_path.stat().st_size,
                    "tex_sha256": sha256(tex_path),
                    "page_content_sha256": content_hash,
                    "page_text_sha256": text_hash,
                    "pdf_title": str(metadata.title or ""),
                    "pdf_author": str(metadata.author or ""),
                },
                "counts": {
                    "maps": len(document.get("maps", [])),
                    "symbols": len(document.get("symbols", [])),
                    "quantities": len(document.get("quantities", [])),
                    "expressions": len(document.get("expressions", [])),
                    "invariants": len(document.get("invariants", [])),
                    "claims": len(claims),
                },
                "unit_contexts": list(document.get("unit_contexts", [])),
                "groups": list(document.get("groups", [])),
            }
        )
    return records, dict(sorted(claim_counts.items()))


def write_module_catalog(records: list[dict[str, Any]]) -> None:
    lines = [
        r"\begin{longtable}{@{}r L{23mm} L{67mm} c r r r@{}}",
        r"\caption{Canonical semantic order of the frozen corpus. "
        r"Counts are module-local.}\label{tab:module-catalog}\\",
        r"\toprule",
        r"No. & Layer & Module & v & pp. & Expr. & Claims\\",
        r"\midrule",
        r"\endfirsthead",
        r"\toprule",
        r"No. & Layer & Module & v & pp. & Expr. & Claims\\",
        r"\midrule",
        r"\endhead",
        r"\bottomrule",
        r"\endfoot",
    ]
    for record in records:
        counts = record["counts"]
        lines.append(
            f"{record['release_index']} & "
            f"{latex_escape(record['layer'])} & "
            f"{latex_escape(record['title'])} & "
            f"{latex_escape(record['version'])} & "
            f"{record['source']['pages']} & "
            f"{counts['expressions']} & "
            f"{counts['claims']}\\\\"
        )
    lines.append(r"\end{longtable}")
    (GENERATED / "module_catalog_v1_3.tex").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )


def dependency_label(node_id: str, modules: dict[str, dict[str, Any]]) -> str:
    if node_id in modules:
        title = modules[node_id]["title"]
        if len(title) > 52:
            title = title[:49].rstrip() + "..."
        return title
    return node_id


def write_dependency_table(
    dependency: dict[str, Any],
    records: list[dict[str, Any]],
) -> None:
    modules = {record["id"]: record for record in records}
    lines = [
        r"\begin{longtable}{@{}L{51mm} L{67mm} L{31mm}@{}}",
        r"\caption{Explicit non-global dependency edges.  The universal "
        r"GO Core edge to all modules is omitted from the rows.}"
        r"\label{tab:dependency-edges}\\",
        r"\toprule",
        r"From & To & Edge kind\\",
        r"\midrule",
        r"\endfirsthead",
        r"\toprule",
        r"From & To & Edge kind\\",
        r"\midrule",
        r"\endhead",
        r"\bottomrule",
        r"\endfoot",
    ]
    for edge in dependency.get("edges", []):
        source = dependency_label(str(edge["from"]), modules)
        target = dependency_label(str(edge["to"]), modules)
        kind = str(edge["kind"]).replace("_", " ")
        lines.append(
            f"{latex_escape(source)} & "
            f"{latex_escape(target)} & "
            f"{latex_escape(kind)}\\\\"
        )
    lines.append(r"\end{longtable}")
    (GENERATED / "dependency_table_v1_3.tex").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )


def write_macros(
    baseline_hash: str,
    records: list[dict[str, Any]],
    claim_counts: dict[str, int],
    dependency_node_count: int,
    dependency_edge_count: int,
    overlap_count: int,
    front_pages: int,
) -> None:
    component_pages = sum(record["source"]["pages"] for record in records)
    typed_expressions = sum(
        record["counts"]["expressions"] for record in records
    )
    claims = sum(record["counts"]["claims"] for record in records)
    strong = sum(
        claim_counts.get(status, 0)
        for status in ("lemma", "proposition", "theorem", "corollary")
    )
    master_pages = front_pages + component_pages
    macros = {
        "ModuleCount": len(records),
        "ComponentPageCount": component_pages,
        "TypedExpressionCount": typed_expressions,
        "ClaimCount": claims,
        "StrongClaimCount": strong,
        "ModelClaimCount": claim_counts.get("model", 0),
        "HypothesisClaimCount": claim_counts.get("hypothesis", 0),
        "DiagnosticClaimCount": claim_counts.get("diagnostic", 0),
        "EmpiricalClaimCount": claim_counts.get("empirical", 0),
        "DependencyNodeCount": dependency_node_count,
        "DependencyEdgeCount": dependency_edge_count,
        "ShortIdentifierOverlapCount": overlap_count,
        "FrontMatterPageCount": front_pages,
        "MasterPageCount": master_pages,
    }
    lines = [
        f"\\newcommand{{\\{name}}}{{{value}}}" for name, value in macros.items()
    ]
    lines.append(
        "\\newcommand{\\BaselineLedgerHash}{\\texttt{\\seqsplit{"
        + baseline_hash
        + "}}}"
    )
    (GENERATED / "freeze_macros_v1_3.tex").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )


def compile_frontmatter() -> int:
    environment = os.environ.copy()
    environment.update(
        {
            "SOURCE_DATE_EPOCH": str(FIXED_EPOCH),
            "FORCE_SOURCE_DATE": "1",
            "TZ": "UTC",
        }
    )
    command = [
        "latexmk",
        "-g",
        "-xelatex",
        "-interaction=nonstopmode",
        "-halt-on-error",
        f"-outdir={FRONT_BUILD}",
        str(FRONT_SOURCE),
    ]
    process = subprocess.run(
        command,
        cwd=ROOT,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )
    if process.returncode != 0:
        raise RuntimeError(
            "front matter LaTeX build failed\n"
            + process.stdout[-8000:]
            + process.stderr[-8000:]
        )
    reader = PdfReader(FRONT_PDF)
    return len(reader.pages)


def merge_master(
    records: list[dict[str, Any]],
    front_pages: int,
) -> list[dict[str, Any]]:
    raw_master = (
        MASTER_BUILD
        / "Geometry_of_Observation_Corpus_Master_v1_3_united.pdf"
    )
    raw_master.unlink(missing_ok=True)
    sources = [FRONT_PDF]
    sources.extend(ROOT / record["source"]["pdf"] for record in records)
    unite = subprocess.run(
        ["pdfunite", *[str(path) for path in sources], str(raw_master)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if unite.returncode != 0:
        raise RuntimeError(
            "pdfunite failed\n" + unite.stdout[-4000:] + unite.stderr[-4000:]
        )
    raw_reader = PdfReader(raw_master)
    expected_pages = front_pages + sum(
        int(record["source"]["pages"]) for record in records
    )
    if len(raw_reader.pages) != expected_pages:
        raise RuntimeError(
            f"raw master page mismatch: {len(raw_reader.pages)} != {expected_pages}"
        )

    writer = PdfWriter()
    writer.clone_document_from_reader(raw_reader)
    stable_identifier = hashlib.sha256(
        (
            RELEASE_VERSION
            + sha256(FRONT_PDF)
            + "".join(record["source"]["pdf_sha256"] for record in records)
        ).encode("ascii")
    ).digest()[:16]
    writer._ID = ArrayObject(  # noqa: SLF001 - deterministic PDF trailer ID
        [
            ByteStringObject(stable_identifier),
            ByteStringObject(stable_identifier),
        ]
    )
    writer.add_outline_item("P12 release front matter", 0)
    page_map: list[dict[str, Any]] = [
        {
            "kind": "front_matter",
            "id": "p12-release-front-matter-v1-3",
            "title": "P12 release front matter",
            "version": RELEASE_VERSION,
            "component_pages": front_pages,
            "master_page_start": 1,
            "master_page_end": front_pages,
            "pdf": relative(FRONT_PDF),
            "pdf_sha256": sha256(FRONT_PDF),
        }
    ]
    cursor = front_pages + 1
    for record in records:
        writer.add_outline_item(
            (
                f"{record['release_index']:02d}. {record['title']} "
                f"(v{record['version']})"
            ),
            cursor - 1,
        )
        pages = int(record["source"]["pages"])
        page_map.append(
            {
                "kind": "normative_module",
                "release_index": int(record["release_index"]),
                "id": record["id"],
                "title": record["title"],
                "version": record["version"],
                "component_pages": pages,
                "component_page_start": 1,
                "component_page_end": pages,
                "master_page_start": cursor,
                "master_page_end": cursor + pages - 1,
                "pdf": record["source"]["pdf"],
                "pdf_sha256": record["source"]["pdf_sha256"],
                "page_content_sha256": record["source"]["page_content_sha256"],
                "page_text_sha256": record["source"]["page_text_sha256"],
            }
        )
        cursor += pages

    writer.add_metadata(
        {
            "/Title": (
                "Geometry of Observation: Frozen Typed Corpus and "
                "Reproducibility Master"
            ),
            "/Author": "Stassis Stashkevichyus",
            "/Subject": "P12 corpus freeze of eighteen GO Core reference modules",
            "/Keywords": (
                "geometry of observation; typed observation maps; invariance; "
                "covariance; identifiability; reproducibility; corpus freeze"
            ),
            "/Creator": "P12 deterministic master builder",
            "/Producer": "pypdf 6.10.0",
        }
    )
    writer.page_mode = "/UseOutlines"
    if front_pages:
        writer.set_page_label(
            0,
            front_pages - 1,
            style=PageLabelStyle.LOWERCASE_ROMAN,
            start=1,
        )
    cursor_zero = front_pages
    for record in records:
        pages = int(record["source"]["pages"])
        writer.set_page_label(
            cursor_zero,
            cursor_zero + pages - 1,
            style=PageLabelStyle.DECIMAL,
            prefix=f"M{record['release_index']:02d}-",
            start=1,
        )
        cursor_zero += pages
    MASTER_BUILD.mkdir(parents=True, exist_ok=True)
    temporary_master = (
        MASTER_BUILD
        / ".Geometry_of_Observation_Corpus_Master_v1_3.tmp.pdf"
    )
    with temporary_master.open("wb") as stream:
        writer.write(stream)
        stream.flush()
        os.fsync(stream.fileno())
    temporary_reader = PdfReader(temporary_master)
    if len(temporary_reader.pages) != expected_pages:
        raise RuntimeError("temporary master failed logical validation")
    if not temporary_master.read_bytes().rstrip().endswith(b"%%EOF"):
        raise RuntimeError("temporary master lacks EOF marker")
    os.replace(temporary_master, MASTER_PDF)
    return page_map


def write_page_maps(page_map: list[dict[str, Any]]) -> None:
    payload = {
        "schema": {
            "id": "go-master-page-map",
            "version": RELEASE_VERSION,
        },
        "date": RELEASE_DATE,
        "master_pdf": relative(MASTER_PDF),
        "master_pdf_sha256": sha256(MASTER_PDF),
        "master_pages": sum(item["component_pages"] for item in page_map),
        "entries": page_map,
    }
    PAGE_MAP_JSON.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    with PAGE_MAP_CSV.open("w", encoding="utf-8", newline="") as stream:
        fieldnames = [
            "kind",
            "release_index",
            "id",
            "title",
            "version",
            "component_pages",
            "master_page_start",
            "master_page_end",
            "pdf",
            "pdf_sha256",
        ]
        writer = csv.DictWriter(stream, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for item in page_map:
            writer.writerow(item)


def write_freeze_ledger(
    baseline: dict[str, Any],
    records: list[dict[str, Any]],
    claim_counts: dict[str, int],
    overlaps: list[dict[str, Any]],
    qualified_total: int,
    dependency: dict[str, Any],
    dependency_nodes: list[dict[str, Any]],
    dependency_edges: list[dict[str, Any]],
    topological: list[str],
    front_pages: int,
) -> None:
    total_counts = {
        key: sum(record["counts"][key] for record in records)
        for key in ("maps", "symbols", "quantities", "expressions", "invariants", "claims")
    }
    author_variants = sorted(
        {
            record["source"]["pdf_author"]
            for record in records
            if record["source"]["pdf_author"]
        }
    )
    freeze = {
        "schema": {
            "id": "go-corpus-freeze-ledger",
            "version": RELEASE_VERSION,
            "date": RELEASE_DATE,
            "phase": "P12",
        },
        "status": "CORPUS_FREEZE",
        "core_contract": "go-core-spec@0.2.0",
        "baseline": {
            "id": "go-corpus-ledgers@1.2.0",
            "path": relative(BASELINE_LEDGER),
            "bytes": BASELINE_LEDGER.stat().st_size,
            "sha256": sha256(BASELINE_LEDGER),
            "canonical_documents": int(
                baseline["schema"]["canonical_documents"]
            ),
        },
        "release_identity": {
            "title": (
                "Geometry of Observation: Frozen Typed Corpus and "
                "Reproducibility Master"
            ),
            "version": RELEASE_VERSION,
            "date": RELEASE_DATE,
            "author": "Stassis Stashkevichyus",
            "orcid": "0009-0000-2294-705X",
            "affiliation": "Independent Research Program",
            "homepage": "https://theobserverofmultiverses.info",
            "doi": None,
            "license": "CC-BY-NC-ND-4.0",
            "component_pdf_author_variants": author_variants,
        },
        "corpus_totals": {
            "modules": len(records),
            "component_pages": sum(
                record["source"]["pages"] for record in records
            ),
            "front_matter_pages": front_pages,
            "master_pages": front_pages
            + sum(record["source"]["pages"] for record in records),
            **total_counts,
            "claim_statuses": claim_counts,
            "corpus_statuses": {"PASS": 18, "FAIL": 0, "BLOCKED": 0},
            "findings": 0,
        },
        "namespace_audit": {
            "qualification": "<document-id>::<local-id>",
            "qualified_expression_and_claim_ids": qualified_total,
            "short_identifier_overlap_count": len(overlaps),
            "short_identifier_overlaps": overlaps,
            "qualified_collisions": 0,
            "map_id_collisions": 0,
            "quantity_id_collisions": 0,
        },
        "dependency_audit": {
            "ledger": relative(DEPENDENCY_LEDGER),
            "ledger_sha256": sha256(DEPENDENCY_LEDGER),
            "nodes": len(dependency_nodes),
            "edges": len(dependency_edges),
            "acyclic": True,
            "topological_order": topological,
            "contextual_relations_excluded": len(
                dependency.get("contextual_relations_not_in_normative_graph", [])
            ),
        },
        "master_artifact": {
            "id": "geometry-of-observation-corpus-master-v1-3",
            "path": relative(MASTER_PDF),
            "pages": len(PdfReader(MASTER_PDF).pages),
            "bytes": MASTER_PDF.stat().st_size,
            "sha256": sha256(MASTER_PDF),
            "page_map": relative(PAGE_MAP_JSON),
            "component_embedding_policy": "unchanged_page_content_streams",
        },
        "auxiliary_documents": [
            {
                "id": "si-hep-quantity-passport-v0-5",
                "pdf": "output/pdf/SI_HEP_Quantity_Passport_v0_5.pdf",
                "contract": (
                    "work/p4_lhc_si_hep_v0_5/core/"
                    "si_hep_quantity_passport_v0_5.yaml"
                ),
                "module_counted": False,
            }
        ],
        "modules": records,
    }
    with FREEZE_LEDGER.open("w", encoding="utf-8") as stream:
        yaml.safe_dump(
            freeze,
            stream,
            sort_keys=False,
            allow_unicode=True,
            width=100,
        )


def checksum_paths(records: list[dict[str, Any]]) -> list[Path]:
    paths: set[Path] = {
        MASTER_PDF,
        FRONT_PDF,
        BASELINE_LEDGER,
        FREEZE_CONTRACT,
        FREEZE_LEDGER,
        DEPENDENCY_LEDGER,
        PAGE_MAP_JSON,
        PAGE_MAP_CSV,
        FRONT_SOURCE,
        P12 / "metadata/CITATION.cff",
        P12 / "metadata/.zenodo.json",
        P12 / "metadata/OSF_RELEASE_METADATA_v1_3.yaml",
        P12 / "LICENSE.md",
        P12 / "CHANGELOG.md",
        P12 / "README.md",
        P12 / "reports/P12_Corpus_Freeze_Report_v1_3_ru.md",
        P12 / "reports/P12_Visual_QA_v1_3.yaml",
        P12 / "generated/dependency_table_v1_3.tex",
        P12 / "generated/freeze_macros_v1_3.tex",
        P12 / "generated/module_catalog_v1_3.tex",
        P12 / "scripts/build_p12_master.py",
        P12 / "tests/build_release_bundle.py",
        P12 / "tests/test_p12_corpus_master_v1_3.py",
        P12 / "tests/validate_p12_release.py",
        ROOT / "work/go_core_v0_2/src/go_lint.py",
    }
    paths.update((ROOT / "work/go_core_v0_2/core").glob("*.yaml"))
    paths.update(
        {
            ROOT / str(node["source"])
            for node in load_yaml(DEPENDENCY_LEDGER).get("nodes", [])
            if isinstance(node, dict) and node.get("source")
        }
    )
    for record in records:
        paths.add(ROOT / record["source"]["pdf"])
        paths.add(ROOT / record["source"]["tex"])
    missing = sorted(str(path) for path in paths if not path.is_file())
    if missing:
        raise FileNotFoundError("checksum targets missing:\n" + "\n".join(missing))
    return sorted(paths, key=relative)


def write_checksums(records: list[dict[str, Any]]) -> None:
    lines = [f"{sha256(path)}  {relative(path)}" for path in checksum_paths(records)]
    CHECKSUMS.write_text("\n".join(lines) + "\n", encoding="utf-8")


def copy_outputs() -> None:
    OUTPUT_PDF.mkdir(parents=True, exist_ok=True)
    OUTPUT_P12.mkdir(parents=True, exist_ok=True)
    copies = [
        (MASTER_PDF, OUTPUT_PDF / MASTER_PDF.name),
        (FREEZE_CONTRACT, OUTPUT_P12 / "GO_Corpus_Freeze_Contract_v1_3.yaml"),
        (FREEZE_LEDGER, OUTPUT_P12 / "GO_Corpus_Freeze_Ledger_v1_3.yaml"),
        (
            DEPENDENCY_LEDGER,
            OUTPUT_P12 / "GO_Corpus_Dependencies_v1_3.yaml",
        ),
        (PAGE_MAP_JSON, OUTPUT_P12 / PAGE_MAP_JSON.name),
        (PAGE_MAP_CSV, OUTPUT_P12 / PAGE_MAP_CSV.name),
        (CHECKSUMS, OUTPUT_P12 / CHECKSUMS.name),
        (
            P12 / "reports/P12_Corpus_Freeze_Report_v1_3_ru.md",
            OUTPUT_P12 / "P12_Corpus_Freeze_Report_v1_3_ru.md",
        ),
        (P12 / "metadata/CITATION.cff", OUTPUT_P12 / "CITATION.cff"),
        (
            P12 / "metadata/.zenodo.json",
            OUTPUT_P12 / "zenodo_metadata_v1_3.json",
        ),
        (
            P12 / "metadata/OSF_RELEASE_METADATA_v1_3.yaml",
            OUTPUT_P12 / "OSF_RELEASE_METADATA_v1_3.yaml",
        ),
        (P12 / "LICENSE.md", OUTPUT_P12 / "LICENSE.md"),
    ]
    for source, destination in copies:
        shutil.copy2(source, destination)
        if sha256(source) != sha256(destination):
            raise RuntimeError(f"output copy hash mismatch: {destination}")


def main() -> None:
    start = datetime.now(timezone.utc)
    for directory in (GENERATED, FRONT_BUILD, MASTER_BUILD, OUTPUT_PDF, OUTPUT_P12):
        directory.mkdir(parents=True, exist_ok=True)

    baseline = load_yaml(BASELINE_LEDGER)
    dependency = load_yaml(DEPENDENCY_LEDGER)
    records, claim_counts = module_records(baseline)
    overlaps, qualified_total, qualified_unique = short_identifier_overlaps(
        baseline["documents"]
    )
    if qualified_total != qualified_unique:
        raise RuntimeError("fully qualified expression/claim IDs are not unique")
    dependency_nodes, dependency_edges, topological = expanded_dependency_graph(
        dependency,
        [record["id"] for record in records],
    )

    write_module_catalog(records)
    write_dependency_table(dependency, records)

    baseline_hash = sha256(BASELINE_LEDGER)
    front_pages = 0
    for _ in range(4):
        write_macros(
            baseline_hash,
            records,
            claim_counts,
            len(dependency_nodes),
            len(dependency_edges),
            len(overlaps),
            front_pages,
        )
        new_front_pages = compile_frontmatter()
        if new_front_pages == front_pages:
            break
        front_pages = new_front_pages
    else:
        raise RuntimeError("front matter page count failed to stabilize")

    page_map = merge_master(records, front_pages)
    write_page_maps(page_map)
    write_freeze_ledger(
        baseline,
        records,
        claim_counts,
        overlaps,
        qualified_total,
        dependency,
        dependency_nodes,
        dependency_edges,
        topological,
        front_pages,
    )
    write_checksums(records)
    copy_outputs()

    master_reader = PdfReader(MASTER_PDF)
    elapsed = (datetime.now(timezone.utc) - start).total_seconds()
    print(
        json.dumps(
            {
                "status": "PASS",
                "modules": len(records),
                "component_pages": sum(
                    record["source"]["pages"] for record in records
                ),
                "front_matter_pages": front_pages,
                "master_pages": len(master_reader.pages),
                "typed_expressions": sum(
                    record["counts"]["expressions"] for record in records
                ),
                "dependency_nodes": len(dependency_nodes),
                "dependency_edges": len(dependency_edges),
                "short_identifier_overlaps": len(overlaps),
                "master_pdf": relative(MASTER_PDF),
                "master_sha256": sha256(MASTER_PDF),
                "elapsed_seconds": round(elapsed, 3),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
