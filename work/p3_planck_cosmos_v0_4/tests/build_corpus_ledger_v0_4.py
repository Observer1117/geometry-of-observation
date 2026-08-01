#!/usr/bin/env python3
"""Replace the Planck-cosmos critical adapter with the P3 reference ledger."""

from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[3]
P3 = ROOT / "work/p3_planck_cosmos_v0_4"
OLD_LEDGER = ROOT / "work/p2_distance_scale_v0_3/ledgers/corpus_ledgers_v0_3.yaml"
REFERENCE_LEDGER = P3 / "ledgers/planck_cosmos_reference_ledger_v0_4.yaml"
OUTPUT_LEDGER = P3 / "ledgers/corpus_ledgers_v0_4.yaml"


def load(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as stream:
        data = yaml.safe_load(stream)
    if not isinstance(data, dict):
        raise TypeError(f"{path}: YAML root is not a mapping")
    return data


def main() -> None:
    corpus = load(OLD_LEDGER)
    reference_documents = load(REFERENCE_LEDGER)["documents"]
    if len(reference_documents) != 1:
        raise RuntimeError("P3 reference ledger must contain exactly one document")
    replacement = reference_documents[0]

    seen = False
    documents: list[dict] = []
    for document in corpus["documents"]:
        if document["id"] == "planck-cosmos-rulers-v1":
            documents.append(replacement)
            seen = True
        else:
            documents.append(document)
    if not seen:
        raise RuntimeError("old Planck-cosmos adapter was not found")

    corpus["schema"]["version"] = "0.4.0"
    corpus["schema"]["date"] = "2026-07-28"
    corpus["schema"]["inherited_extension_contract"] = (
        "go-distance-scale-contract@0.3.0"
    )
    corpus["schema"]["extension_contract"] = (
        "go-planck-cosmos-scale-contract@0.4.0"
    )
    corpus["documents"] = documents
    corpus["duplicate_or_superseded_sources"].append(
        {
            "status": "superseded",
            "path": "upload/planck_cosmos_observation_rulers_v1_bilingual(3).pdf",
            "sha256": "68a3051e593d6de7ed867d50b8c132ac6a6231ea711e76730101a0b6f24fa9d3",
            "canonical_document": "planck-cosmos-rulers-v1-1",
        }
    )

    ids = [document["id"] for document in documents]
    if len(ids) != 17 or len(set(ids)) != 17:
        raise RuntimeError("the v0.4 corpus must retain 17 unique documents")
    if sum(document["ledger_level"] == "reference" for document in documents) != 7:
        raise RuntimeError("the v0.4 corpus must contain seven reference ledgers")

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
