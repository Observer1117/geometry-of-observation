#!/usr/bin/env python3
"""Mechanically replace the two migrated v0.1 adapters in the corpus ledger."""

from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[3]
OLD_LEDGER = ROOT / "work/go_core_v0_2/ledgers/corpus_ledgers_v0_1.yaml"
REFERENCE_LEDGER = (
    ROOT
    / "work/p1_info_metric_v0_2/ledgers/information_metric_reference_ledgers_v0_2.yaml"
)
OUTPUT_LEDGER = (
    ROOT / "work/p1_info_metric_v0_2/ledgers/corpus_ledgers_v0_2.yaml"
)


def load(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as stream:
        data = yaml.safe_load(stream)
    if not isinstance(data, dict):
        raise TypeError(f"{path} does not contain a YAML mapping")
    return data


def main() -> None:
    corpus = load(OLD_LEDGER)
    migrated = load(REFERENCE_LEDGER)["documents"]
    replacements = {
        "information-theoretic-observation-v0-1": migrated[0],
        "metric-entropy-defect-v0-1": migrated[1],
    }

    seen: set[str] = set()
    documents: list[dict] = []
    for document in corpus["documents"]:
        old_id = document["id"]
        if old_id in replacements:
            documents.append(replacements[old_id])
            seen.add(old_id)
        else:
            documents.append(document)

    if seen != set(replacements):
        missing = sorted(set(replacements) - seen)
        raise RuntimeError(f"old corpus documents not found: {missing}")

    corpus["schema"]["version"] = "0.2.0"
    corpus["schema"]["date"] = "2026-07-28"
    corpus["schema"]["audit_policy"] = (
        "reference_ledgers_are_p1_eligible_critical_adapters_are_not"
    )
    corpus["documents"] = documents
    corpus["duplicate_or_superseded_sources"].extend(
        [
            {
                "status": "superseded",
                "path": "upload/Information_Theoretic_Observation_Geometry_v0_1(1).pdf",
                "sha256": "24fd1228d382e1ed2e53924d93a2f8be42c25007d44f4b1f91a94dda7f5d890b",
                "canonical_document": "information-theoretic-observation-v0-2",
            },
            {
                "status": "superseded",
                "path": "upload/Metric_Entropy_and_Observational_Entropy_Defect_v0_1(1).pdf",
                "sha256": "508109e33da1186bc4cbc1ffa5a3355087515a7ba7296e584909ff3c1d1a4e95",
                "canonical_document": "metric-entropy-defect-v0-2",
            },
        ]
    )

    ids = [document["id"] for document in documents]
    if len(ids) != 17 or len(set(ids)) != 17:
        raise RuntimeError("the v0.2 corpus must retain 17 unique documents")

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
