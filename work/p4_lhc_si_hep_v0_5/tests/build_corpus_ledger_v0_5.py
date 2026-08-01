#!/usr/bin/env python3
"""Replace the blocked LHC adapter with the strict P4 reference ledger."""

from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[3]
P4 = ROOT / "work/p4_lhc_si_hep_v0_5"
OLD_LEDGER = ROOT / "work/p3_planck_cosmos_v0_4/ledgers/corpus_ledgers_v0_4.yaml"
REFERENCE_LEDGER = P4 / "ledgers/lhc_si_hep_reference_ledgers_v0_5.yaml"
OUTPUT_LEDGER = P4 / "ledgers/corpus_ledgers_v0_5.yaml"


def load(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as stream:
        data = yaml.safe_load(stream)
    if not isinstance(data, dict):
        raise TypeError(f"{path}: YAML root is not a mapping")
    return data


def main() -> None:
    corpus = load(OLD_LEDGER)
    references = load(REFERENCE_LEDGER)["documents"]
    lhc_documents = [
        document for document in references if document["id"] == "lhc-beam-observation-v1-3"
    ]
    if len(lhc_documents) != 1:
        raise RuntimeError("P4 reference ledger must contain exactly one LHC v1.3 document")
    replacement = lhc_documents[0]

    seen = False
    documents: list[dict] = []
    for document in corpus["documents"]:
        if document["id"] == "lhc-beam-observation-v1-2":
            documents.append(replacement)
            seen = True
        else:
            documents.append(document)
    if not seen:
        raise RuntimeError("old blocked LHC adapter was not found")

    corpus["schema"]["version"] = "0.5.0"
    corpus["schema"]["date"] = "2026-07-28"
    corpus["schema"]["inherited_extension_contract"] = (
        "go-planck-cosmos-scale-contract@0.4.0"
    )
    corpus["schema"]["extension_contract"] = (
        "go-si-hep-quantity-passport@0.5.0"
    )
    corpus["documents"] = documents
    corpus["duplicate_or_superseded_sources"].append(
        {
            "status": "superseded",
            "path": "upload/lhc_beam_geometry_observation_v12_terrell_bilingual.pdf",
            "sha256": "77ea946d19e6ef3050ec23bf7a270a070df6641a5bde3484e204fc71eb72f101",
            "canonical_document": "lhc-beam-observation-v1-3",
        }
    )

    ids = [document["id"] for document in documents]
    if len(ids) != 17 or len(set(ids)) != 17:
        raise RuntimeError("the v0.5 corpus must retain 17 unique documents")
    if sum(document["ledger_level"] == "reference" for document in documents) != 8:
        raise RuntimeError("the v0.5 corpus must contain eight reference ledgers")

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
