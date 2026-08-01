#!/usr/bin/env python3
"""Release-level validation for the GO P2 distance-scale migration."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path

import yaml
from PIL import Image
from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[3]
P2 = ROOT / "work/p2_distance_scale_v0_3"
REFERENCE_LEDGER = P2 / "ledgers/distance_scale_mandelbrot_reference_ledgers_v0_3.yaml"
CORPUS_LEDGER = P2 / "ledgers/corpus_ledgers_v0_3.yaml"
CONTRACT = P2 / "core/distance_scale_contract_v0_3.yaml"
REFERENCE_REPORT = P2 / "reports/Distance_Scale_Mandelbrot_Lint_Report_v0_3.json"
CORPUS_REPORT = P2 / "reports/GO_Corpus_Lint_Report_v0_3.json"
OUTPUT = P2 / "reports/P2_Validation_Summary_v0_3.json"


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


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def assert_embedded_fonts(pdf: Path) -> int:
    result = subprocess.run(
        ["pdffonts", str(pdf)],
        check=True,
        capture_output=True,
        text=True,
    )
    checked = 0
    row_pattern = re.compile(
        r"\s+(yes|no)\s+(yes|no)\s+(yes|no)\s+\d+\s+\d+\s*$"
    )
    for line in result.stdout.splitlines():
        match = row_pattern.search(line)
        if not match:
            continue
        checked += 1
        if match.group(1) != "yes":
            raise AssertionError(f"{pdf}: unembedded font row: {line}")
    if checked == 0:
        raise AssertionError(f"{pdf}: pdffonts returned no font rows")
    return checked


def assert_rendered_pages(directory: Path, expected_pages: int) -> int:
    pages = sorted(directory.glob("page-*.png"))
    if len(pages) != expected_pages:
        raise AssertionError(
            f"{directory}: {len(pages)} rendered pages, expected {expected_pages}"
        )
    for page in pages:
        with Image.open(page) as image:
            image.verify()
    contact = directory / "contact.png"
    if not contact.is_file():
        raise FileNotFoundError(contact)
    with Image.open(contact) as image:
        image.verify()
    return len(pages)


def main() -> None:
    ledger = load_yaml(REFERENCE_LEDGER)
    documents = ledger.get("documents", [])
    if len(documents) != 2:
        raise AssertionError("reference ledger must contain exactly two documents")

    required_source_fragments = {
        "distance-scale-interface-v0-2": [
            r"\begin{theorem}[Pseudometric and separation criterion]",
            r"d_O(x,x'):=d_Y",
            r"\begin{theorem}[Canonical quotient metric]",
            r"g_O:=O^*g_Y",
            r"\begin{theorem}[Unit covariance of shells and graphs]",
            r"L_O\varepsilon_X\leq\varepsilon_Y",
            r"\begin{theorem}[Rational-step factorization]",
            r"\Delta d=P/2",
            "Erdos firewall",
        ],
        "mandelbrot-rulers-v1-1": [
            r"\log_b\frac{\ell_*}{\varepsilon}",
            r"\underline{\dim}_{B}A",
            r"\begin{theorem}[Reference and base independence]",
            r"\begin{theorem}[Matched Lipschitz cover]",
            r"\begin{theorem}[Protocol-comparison criterion]",
            r"\widehat D_{\Wcal,w}",
            r"I_{\Wcal}^{\mathrm{pair}}",
            r"\Cov(\bm\eta)=\bm\Sigma",
            "generator-aligned",
            "carries no coverage probability",
        ],
    }
    prohibited_global = ["TODO", "TBD", "\ufffd"]

    document_results: list[dict] = []
    total_fonts = 0
    total_rendered = 0
    for document in documents:
        if document.get("ledger_level") != "reference":
            raise AssertionError(f"{document['id']}: ledger is not reference-level")
        if document.get("migration_status") != "p2_reference_pass":
            raise AssertionError(f"{document['id']}: migration is not marked pass")

        source = document["source"]
        pdf = ROOT / source["pdf"]
        tex = ROOT / source["tex"]
        text_path = ROOT / source["text"]
        branch = "distance" if document["id"].startswith("distance") else "mandelbrot"
        log = P2 / "build" / branch / f"{pdf.stem}.log"
        render_dir = P2 / "checks" / branch
        for path in (pdf, tex, text_path, log):
            if not path.is_file():
                raise FileNotFoundError(path)

        actual_hash = sha256(pdf)
        if actual_hash != source["sha256"]:
            raise AssertionError(
                f"{document['id']}: hash {actual_hash} != {source['sha256']}"
            )

        reader = PdfReader(str(pdf))
        if len(reader.pages) != source["pages"]:
            raise AssertionError(f"{document['id']}: page-count mismatch")
        title = (reader.metadata or {}).get("/Title", "")
        if title != document["title"]:
            raise AssertionError(
                f"{document['id']}: PDF title {title!r} != {document['title']!r}"
            )

        tex_text = tex.read_text(encoding="utf-8")
        extracted = text_path.read_text(encoding="utf-8")
        log_text = log.read_text(encoding="utf-8", errors="replace")
        for token in prohibited_global:
            if token in tex_text or token in extracted:
                raise AssertionError(f"{document['id']}: prohibited token {token!r}")
        for fragment in required_source_fragments[document["id"]]:
            if fragment not in tex_text:
                raise AssertionError(
                    f"{document['id']}: missing required source fragment {fragment}"
                )
        for bad_log_token in (
            "Overfull",
            "LaTeX Warning",
            "undefined references",
            "multiply defined",
            "Fatal error",
        ):
            if bad_log_token in log_text:
                raise AssertionError(
                    f"{document['id']}: build log contains {bad_log_token}"
                )
        if len(extracted.strip()) < 10000:
            raise AssertionError(f"{document['id']}: extracted PDF text is too short")

        font_count = assert_embedded_fonts(pdf)
        rendered_count = assert_rendered_pages(render_dir, source["pages"])
        total_fonts += font_count
        total_rendered += rendered_count
        document_results.append(
            {
                "id": document["id"],
                "pages": len(reader.pages),
                "sha256": actual_hash,
                "embedded_font_rows": font_count,
                "rendered_pages_verified": rendered_count,
                "extracted_characters": len(extracted),
            }
        )

    contract = load_yaml(CONTRACT)
    if contract.get("schema", {}).get("version") != "0.3.0":
        raise AssertionError("distance-scale contract has the wrong version")
    if len(contract.get("scale_roles", {})) != 10:
        raise AssertionError("distance-scale contract must define ten physical scale roles")
    if len(contract.get("claim_firewalls", [])) < 5:
        raise AssertionError("distance-scale contract has incomplete claim firewalls")

    reference_report = load_json(REFERENCE_REPORT)
    if reference_report["summary"]["findings_total"] != 0:
        raise AssertionError("reference lint report contains findings")
    if reference_report["summary"]["status_counts"] != {"PASS": 2}:
        raise AssertionError("reference lint status is not PASS/PASS")
    if reference_report["summary"]["expressions_checked"] != 24:
        raise AssertionError("reference expression count is not 24")

    corpus = load_yaml(CORPUS_LEDGER)
    if len(corpus.get("documents", [])) != 17:
        raise AssertionError("updated corpus does not contain 17 documents")
    corpus_report = load_json(CORPUS_REPORT)
    expected_statuses = {"BLOCKED": 2, "FAIL": 9, "PASS": 6}
    if corpus_report["summary"]["status_counts"] != expected_statuses:
        raise AssertionError(
            f"unexpected corpus statuses: {corpus_report['summary']['status_counts']}"
        )

    result = {
        "schema": {"id": "go-p2-validation-summary", "version": "0.3.0"},
        "status": "PASS",
        "documents": document_results,
        "reference_ledgers": 2,
        "typed_expressions": 24,
        "reference_lint_findings": 0,
        "regression_tests": 27,
        "total_pages": sum(item["pages"] for item in document_results),
        "rendered_pages_verified": total_rendered,
        "embedded_font_rows_checked": total_fonts,
        "corpus_statuses": expected_statuses,
    }
    OUTPUT.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
