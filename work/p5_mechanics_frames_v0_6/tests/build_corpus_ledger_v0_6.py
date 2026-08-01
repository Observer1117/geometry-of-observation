#!/usr/bin/env python3
"""Replace three mechanics adapters and add the P5 mechanics interface."""

from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[3]
P5 = ROOT / "work/p5_mechanics_frames_v0_6"
OLD_LEDGER = ROOT / "work/p4_lhc_si_hep_v0_5/ledgers/corpus_ledgers_v0_5.yaml"
REFERENCE_LEDGER = P5 / "ledgers/mechanics_reference_ledgers_v0_6.yaml"
OUTPUT_LEDGER = P5 / "ledgers/corpus_ledgers_v0_6.yaml"

REPLACEMENTS = {
    "celestial-foucault-networks-v1": "celestial-foucault-networks-v1-1",
    "bobsleigh-contact-v1": "bobsleigh-contact-v1-1",
    "roller-coaster-v1": "roller-coaster-v1-1",
}


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

    interface = reference_documents["frames-forces-dissipation-interface-v0-1"]
    old_by_id = {item["id"]: item for item in corpus["documents"]}
    missing = set(REPLACEMENTS) - set(old_by_id)
    if missing:
        raise RuntimeError(f"missing old mechanics adapters: {sorted(missing)}")

    documents: list[dict] = []
    inserted_interface = False
    for document in corpus["documents"]:
        old_id = document["id"]
        if old_id in REPLACEMENTS:
            if not inserted_interface:
                documents.append(interface)
                inserted_interface = True
            documents.append(reference_documents[REPLACEMENTS[old_id]])
        else:
            documents.append(document)

    if not inserted_interface:
        raise RuntimeError("mechanics interface was not inserted")

    superseded = list(corpus["duplicate_or_superseded_sources"])
    for old_id, new_id in REPLACEMENTS.items():
        old = old_by_id[old_id]
        superseded.append(
            {
                "status": "superseded",
                "path": old["source"]["pdf"],
                "sha256": old["source"]["sha256"],
                "canonical_document": new_id,
            }
        )

    corpus["schema"]["version"] = "0.6.0"
    corpus["schema"]["date"] = "2026-07-28"
    corpus["schema"]["inherited_extension_contract"] = (
        "go-si-hep-quantity-passport@0.5.0"
    )
    corpus["schema"]["extension_contract"] = (
        "go-frame-force-dissipation-contract@0.6.0"
    )
    corpus["documents"] = documents
    corpus["duplicate_or_superseded_sources"] = superseded

    ids = [item["id"] for item in documents]
    if len(ids) != 18 or len(set(ids)) != 18:
        raise RuntimeError("P5 corpus must contain 18 unique canonical documents")
    reference_count = sum(
        item["ledger_level"] == "reference" for item in documents
    )
    if reference_count != 12:
        raise RuntimeError(
            f"P5 corpus must contain 12 references, found {reference_count}"
        )
    if set(REPLACEMENTS) & set(ids):
        raise RuntimeError("an old mechanics adapter remains canonical")

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
