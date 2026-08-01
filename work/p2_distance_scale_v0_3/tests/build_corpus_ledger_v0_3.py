#!/usr/bin/env python3
"""Replace the distance and Mandelbrot adapters with P2 reference ledgers."""

from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[3]
OLD_LEDGER = ROOT / "work/p1_info_metric_v0_2/ledgers/corpus_ledgers_v0_2.yaml"
REFERENCE_LEDGER = (
    ROOT
    / "work/p2_distance_scale_v0_3/ledgers/"
    "distance_scale_mandelbrot_reference_ledgers_v0_3.yaml"
)
OUTPUT_LEDGER = (
    ROOT / "work/p2_distance_scale_v0_3/ledgers/corpus_ledgers_v0_3.yaml"
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
        "unit-distances-observation-v0-1": migrated[0],
        "mandelbrot-rulers-v1": migrated[1],
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

    corpus["schema"]["version"] = "0.3.0"
    corpus["schema"]["date"] = "2026-07-28"
    corpus["schema"]["extension_contract"] = "go-distance-scale-contract@0.3.0"
    corpus["documents"] = documents
    corpus["duplicate_or_superseded_sources"].extend(
        [
            {
                "status": "superseded",
                "path": "upload/Unit_Distances_under_Observation_Maps_v0_1(2).pdf",
                "sha256": "55d1e61f7bc6bd0454f8f166001611eb9e88f1f03a1142920a6fb3ade4a02678",
                "canonical_document": "distance-scale-interface-v0-2",
            },
            {
                "status": "superseded",
                "path": "upload/mandelbrot_rulers_observation_v1_bilingual(3).pdf",
                "sha256": "6678e0db4ebfb4be0b225f9ace41f87b60e74999adc3202bce9bd66248e7a87c",
                "canonical_document": "mandelbrot-rulers-v1-1",
            },
        ]
    )

    ids = [document["id"] for document in documents]
    if len(ids) != 17 or len(set(ids)) != 17:
        raise RuntimeError("the v0.3 corpus must retain 17 unique documents")

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
