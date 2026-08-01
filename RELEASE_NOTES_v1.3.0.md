# Geometry of Observation Corpus v1.3.0 — Frozen Master Release

This is the first public frozen release of the strict Geometry of Observation research corpus.

## Contents

- 166-page master PDF;
- eighteen canonical component PDFs;
- exact source and phase bundles;
- typed expression and dependency ledgers;
- P12 validation and visual-QA records;
- deterministic full release bundle.

## Verification

- Master PDF SHA-256: `3942277bc24ce6c134876bf27d322e03869a40e7d52eb084bcab6b3c885bf2d2`
- Release bundle SHA-256: `497c16c5e86279025066fbf48954e067bd53bd2cad970545d32000d7e0327ee6`
- Corpus status: 18 PASS / 0 FAIL / 0 BLOCKED
- P12 tests: 259/259
- Independent page render: 166/166

## Publication audit qualification

The canonical assets retain their original hashes. Clean-room extraction found that the original ZIP omits several intermediate QA files required for immediate replay and that the P11 validator's `graph_relabel` ceiling is below the residual stored in its canonical metrics. The repository includes a transparent publication supplement that reconstructs the omitted auxiliaries and uses a portable `5e-15` ceiling. See `PUBLICATION_SUPPLEMENT.md`.

## Scientific status

Public research corpus/preprint; not peer reviewed. The release provides typed mathematical infrastructure and reproducibility evidence. It does not assert physical equivalence between application domains and is not a unified physical theory.
