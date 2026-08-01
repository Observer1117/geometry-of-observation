#!/usr/bin/env python3
"""Release-level validation for the two GO P1 reference modules."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path

import yaml
from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[3]
P1 = ROOT / "work/p1_info_metric_v0_2"
REFERENCE_LEDGER = P1 / "ledgers/information_metric_reference_ledgers_v0_2.yaml"
CORPUS_LEDGER = P1 / "ledgers/corpus_ledgers_v0_2.yaml"
REFERENCE_REPORT = P1 / "reports/Information_Metric_Lint_Report_v0_2.json"
CORPUS_REPORT = P1 / "reports/GO_Corpus_Lint_Report_v0_2.json"
OUTPUT = P1 / "reports/P1_Validation_Summary_v0_2.json"


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


def main() -> None:
    ledger = load_yaml(REFERENCE_LEDGER)
    documents = ledger.get("documents", [])
    if len(documents) != 2:
        raise AssertionError("reference ledger must contain exactly two documents")

    required_source_fragments = {
        "information-theoretic-observation-v0-2": [
            r"\newcommand{\Hb}",
            r"\begin{theorem}[Information-unit change]",
            r"\Dinfo_{\lambda,b}(P_X)",
            r"h_{b,v_*}(X)",
            r"p_X(x)v_*",
            r"\begin{theorem}[Fano inequality]",
            "degenerate-source zero policy",
        ],
        "metric-entropy-defect-v0-2": [
            r"\begin{theorem}[Metric-unit covariance]",
            r"L_O\varepsilon_X\leq\varepsilon_Y",
            r"\begin{theorem}[Exact composition law]",
            r"\log_b(\ell_*/\varepsilon)",
            r"\tau=\frac{s}{\ell_*^2}",
            r"\Ccal^{\mathrm{heat}}",
            "one-cell zero policy",
        ],
    }
    prohibited_global = ["TODO", "TBD", "\ufffd"]

    document_results: list[dict] = []
    total_fonts = 0
    for document in documents:
        if document.get("ledger_level") != "reference":
            raise AssertionError(f"{document['id']}: ledger is not reference-level")
        if document.get("migration_status") != "p1_reference_pass":
            raise AssertionError(f"{document['id']}: migration is not marked pass")

        source = document["source"]
        pdf = ROOT / source["pdf"]
        tex = ROOT / source["tex"]
        text_path = ROOT / source["text"]
        log = (
            P1
            / "build"
            / ("information" if "information" in document["id"] else "metric")
            / f"{pdf.stem}.log"
        )
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
        if len(extracted.strip()) < 5000:
            raise AssertionError(f"{document['id']}: extracted PDF text is too short")

        font_count = assert_embedded_fonts(pdf)
        total_fonts += font_count
        document_results.append(
            {
                "id": document["id"],
                "pages": len(reader.pages),
                "sha256": actual_hash,
                "embedded_font_rows": font_count,
                "extracted_characters": len(extracted),
            }
        )

    reference_report = load_json(REFERENCE_REPORT)
    if reference_report["summary"]["findings_total"] != 0:
        raise AssertionError("reference lint report contains findings")
    if reference_report["summary"]["status_counts"] != {"PASS": 2}:
        raise AssertionError("reference lint status is not PASS/PASS")
    if reference_report["summary"]["expressions_checked"] != 22:
        raise AssertionError("reference expression count is not 22")

    corpus = load_yaml(CORPUS_LEDGER)
    if len(corpus.get("documents", [])) != 17:
        raise AssertionError("updated corpus does not contain 17 documents")
    corpus_report = load_json(CORPUS_REPORT)
    expected_statuses = {"BLOCKED": 2, "FAIL": 11, "PASS": 4}
    if corpus_report["summary"]["status_counts"] != expected_statuses:
        raise AssertionError(
            f"unexpected corpus statuses: {corpus_report['summary']['status_counts']}"
        )

    result = {
        "schema": {"id": "go-p1-validation-summary", "version": "0.2.0"},
        "status": "PASS",
        "documents": document_results,
        "reference_ledgers": 2,
        "typed_expressions": 22,
        "reference_lint_findings": 0,
        "regression_tests": 19,
        "total_pages": sum(item["pages"] for item in document_results),
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
