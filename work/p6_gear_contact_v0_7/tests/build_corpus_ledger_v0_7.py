#!/usr/bin/env python3
"""Replace the legacy gear-contact adapter with the P6 strict reference."""

from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[3]
P6 = ROOT / "work/p6_gear_contact_v0_7"
OLD_LEDGER = (
    ROOT / "work/p5_mechanics_frames_v0_6/ledgers/corpus_ledgers_v0_6.yaml"
)
REFERENCE_LEDGER = P6 / "ledgers/gear_contact_reference_ledger_v0_7.yaml"
OUTPUT_LEDGER = P6 / "ledgers/corpus_ledgers_v0_7.yaml"

OLD_ID = "gear-contact-v1"
NEW_ID = "gear-contact-v1-1"


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
    superseded = list(corpus["duplicate_or_superseded_sources"])
    superseded.append(
        {
            "status": "superseded",
            "path": old_document["source"]["pdf"],
            "sha256": old_document["source"]["sha256"],
            "canonical_document": NEW_ID,
        }
    )

    corpus["schema"]["version"] = "0.7.0"
    corpus["schema"]["date"] = "2026-07-28"
    corpus["schema"]["inherited_extension_contract"] = (
        "go-frame-force-dissipation-contract@0.6.0"
    )
    corpus["schema"]["extension_contract"] = "go-gear-contact-contract@0.7.0"
    corpus["documents"] = documents
    corpus["duplicate_or_superseded_sources"] = superseded

    ids = [item["id"] for item in documents]
    if len(ids) != 18 or len(set(ids)) != 18:
        raise RuntimeError("P6 corpus must contain 18 unique canonical documents")
    if OLD_ID in ids or NEW_ID not in ids:
        raise RuntimeError("gear-contact supersession failed")
    reference_count = sum(
        item["ledger_level"] == "reference" for item in documents
    )
    if reference_count != 13:
        raise RuntimeError(
            f"P6 corpus must contain 13 references, found {reference_count}"
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
