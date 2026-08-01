#!/usr/bin/env python3
"""Replace the legacy conical-intersections adapter with the P8 reference."""

from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[3]
P8 = ROOT / "work/p8_conical_intersections_v0_9"
OLD_LEDGER = (
    ROOT / "work/p7_billiards_v0_8/ledgers/corpus_ledgers_v0_8.yaml"
)
REFERENCE_LEDGER = (
    P8 / "ledgers/conical_intersections_reference_ledger_v0_9.yaml"
)
OUTPUT_LEDGER = P8 / "ledgers/corpus_ledgers_v0_9.yaml"

OLD_ID = "conical-intersections-v1"
NEW_ID = "conical-intersections-observation-v1-1"
LEGACY_DUPLICATE = (
    "upload/conical_intersections_observation_caustics_v1_bilingual "
    "(1)(2).pdf"
)


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

    legacy_sources: list[dict] = []
    duplicate_converted = False
    for item in corpus["duplicate_or_superseded_sources"]:
        record = dict(item)
        if record.get("path") == LEGACY_DUPLICATE:
            record["status"] = "superseded"
            record["canonical_document"] = NEW_ID
            record.pop("canonical_path", None)
            duplicate_converted = True
        legacy_sources.append(record)
    if not duplicate_converted:
        raise RuntimeError("legacy conical duplicate record was not found")

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

    corpus["schema"]["version"] = "0.9.0"
    corpus["schema"]["date"] = "2026-07-28"
    corpus["schema"]["canonical_documents"] = 18
    corpus["schema"]["inherited_extension_contract"] = (
        "go-billiards-observation-contract@0.8.0"
    )
    corpus["schema"]["extension_contract"] = (
        "go-conical-intersections-observation-contract@0.9.0"
    )
    corpus["documents"] = documents
    corpus["duplicate_or_superseded_sources"] = legacy_sources

    ids = [item["id"] for item in documents]
    if len(ids) != 18 or len(set(ids)) != 18:
        raise RuntimeError("P8 corpus must contain 18 unique documents")
    if OLD_ID in ids or NEW_ID not in ids:
        raise RuntimeError("conical-intersections supersession failed")
    reference_count = sum(
        item["ledger_level"] == "reference" for item in documents
    )
    if reference_count != 15:
        raise RuntimeError(
            f"P8 corpus must contain 15 references, found {reference_count}"
        )
    critical_count = sum(
        item["ledger_level"] == "critical_adapter" for item in documents
    )
    if critical_count != 3:
        raise RuntimeError(
            f"P8 corpus must contain 3 critical adapters, found {critical_count}"
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
    print(OUTPUT_LEDGER)


if __name__ == "__main__":
    main()
