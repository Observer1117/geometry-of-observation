#!/usr/bin/env python3
"""Replace the final satellite critical adapter with the P11 reference."""

from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[3]
P11 = ROOT / "work/p11_satellite_networks_v1_2"
OLD_LEDGER = (
    ROOT / "work/p10_regular_polyhedra_v1_1/ledgers/corpus_ledgers_v1_1.yaml"
)
REFERENCE_LEDGER = (
    P11 / "ledgers/satellite_networks_reference_ledger_v1_2.yaml"
)
OUTPUT_LEDGER = P11 / "ledgers/corpus_ledgers_v1_2.yaml"

OLD_ID = "satellite-networks-v1-1"
NEW_ID = "satellite-networks-observation-v1-2"


def load(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as stream:
        value = yaml.safe_load(stream)
    if not isinstance(value, dict):
        raise TypeError(f"{path}: YAML root must be a mapping")
    return value


def main() -> None:
    corpus = load(OLD_LEDGER)
    reference_documents = {
        item["id"]: item for item in load(REFERENCE_LEDGER)["documents"]
    }
    new_document = reference_documents[NEW_ID]

    old_matches = [
        item for item in corpus["documents"] if item.get("id") == OLD_ID
    ]
    if len(old_matches) != 1:
        raise RuntimeError(
            f"expected one {OLD_ID!r} adapter, found {len(old_matches)}"
        )
    old_document = old_matches[0]

    documents = [
        new_document if item.get("id") == OLD_ID else item
        for item in corpus["documents"]
    ]

    legacy_sources = list(corpus["duplicate_or_superseded_sources"])
    old_pdf = old_document["source"]["pdf"]
    if not any(item.get("path") == old_pdf for item in legacy_sources):
        legacy_sources.append(
            {
                "status": "superseded",
                "path": old_pdf,
                "sha256": old_document["source"]["sha256"],
                "canonical_document": NEW_ID,
            }
        )

    corpus["schema"]["version"] = "1.2.0"
    corpus["schema"]["date"] = "2026-07-28"
    corpus["schema"]["canonical_documents"] = 18
    corpus["schema"]["inherited_extension_contract"] = (
        "go-regular-polyhedra-observation-contract@1.1.0"
    )
    corpus["schema"]["extension_contract"] = (
        "go-satellite-networks-observation-contract@1.2.0"
    )
    corpus["documents"] = documents
    corpus["duplicate_or_superseded_sources"] = legacy_sources

    ids = [item["id"] for item in documents]
    if len(ids) != 18 or len(set(ids)) != 18:
        raise RuntimeError("P11 corpus must contain 18 unique documents")
    if OLD_ID in ids or NEW_ID not in ids:
        raise RuntimeError("satellite-network supersession failed")
    reference_count = sum(
        item["ledger_level"] == "reference" for item in documents
    )
    if reference_count != 18:
        raise RuntimeError(
            f"P11 corpus must contain 18 references, found {reference_count}"
        )
    critical_count = sum(
        item["ledger_level"] == "critical_adapter" for item in documents
    )
    if critical_count != 0:
        raise RuntimeError(
            f"P11 corpus must contain no critical adapters, found {critical_count}"
        )

    OUTPUT_LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_LEDGER.open("w", encoding="utf-8") as stream:
        yaml.safe_dump(
            corpus,
            stream,
            sort_keys=False,
            allow_unicode=True,
            width=100,
        )
    print(OUTPUT_LEDGER.relative_to(ROOT))


if __name__ == "__main__":
    main()
