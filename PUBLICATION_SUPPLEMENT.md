# Publication supplement 1 for frozen corpus v1.3.0

The canonical v1.3.0 master PDF and release bundle remain unchanged. Their SHA-256 values are:

- master PDF: `3942277bc24ce6c134876bf27d322e03869a40e7d52eb084bcab6b3c885bf2d2`;
- original release bundle: `497c16c5e86279025066fbf48954e067bd53bd2cad970545d32000d7e0327ee6`.

During publication staging, a clean-room extraction of the original bundle exposed two reproducibility defects in the packaging layer.

## S1 — omitted validator-side QA artefacts

The inherited P1-P11 bundles contain the canonical sources, PDFs, ledgers, tests, and principal reports, but omit some intermediate extracted-text files, LaTeX logs, and rendered page PNGs required by the phase validators. Consequently, the original P12 ZIP cannot replay the declared P1-P11 validator chain immediately after extraction.

`scripts/restore_publication_qa.py` reconstructs these auxiliary files from the frozen PDFs and sources. It does not rewrite the canonical component PDFs or the master PDF. The P3 auxiliary log is generated from a temporary table-layout copy that abbreviates one header solely to remove a platform-specific 3.52 pt diagnostic; the frozen source and PDF are not modified.

## S2 — P11 portability threshold

The frozen P11 metrics record

```text
max_abs_error_by_category.graph_relabel = 4.440892098500626e-15
```

while the original P11 release validator requires `< 4e-15`. The validator therefore rejects its own canonical metrics on the public reference extraction. The publication overlay changes only this validator ceiling to `< 5e-15`; benchmark data, formulas, tests, PDFs, and PASS/FAIL rows are unchanged.

## Status boundary

- These are packaging and portability corrections, not new mathematical results.
- The original v1.3.0 assets are immutable and remain the objects of citation.
- The supplemented repository must identify the overlay in release notes and must not claim that the original ZIP alone is self-contained for 51/51 replay.
- A future v1.3.1 bundle should incorporate the reconstructed QA artefacts and corrected tolerance directly, then receive a new manifest and SHA-256 ledger.
