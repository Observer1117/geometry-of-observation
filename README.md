# Geometry of Observation

## Frozen typed corpus and reproducibility master — v1.3.0

**Author:** Stassis Stashkevichyus, Independent Researcher, Lithuania  
**ORCID:** [0009-0000-2294-705X](https://orcid.org/0009-0000-2294-705X)  
**Project website:** [theobserverofmultiverses.info](https://theobserverofmultiverses.info)  
**Release date:** 2026-07-28  
**Status:** public research corpus/preprint; not peer reviewed
**Corpus DOI:** [10.17605/OSF.IO/GE92J](https://doi.org/10.17605/OSF.IO/GE92J)  
**Immutable OSF Registration:** [osf.io/ge92j](https://osf.io/ge92j/)  

This repository contains the frozen P12 release of the Geometry of Observation corpus. It packages eighteen independently scoped reference modules, their exact sources, typed expression ledgers, dependency metadata, claim boundaries, component hashes, and executable release validation.

The shared architecture formalizes observation maps, information loss, invariance and covariance, identifiability, reconstruction limits, frame dependence, sampling, and operational comparison. It does **not** assert that the application domains are physically equivalent, and it does not constitute a unified physical theory.

## Canonical release objects

- [Master PDF (166 pages)](corpus/master/Geometry_of_Observation_Corpus_Master_v1_3.pdf)
- [Eighteen component PDFs](corpus/modules/)
- [Release manifest](metadata/RELEASE_MANIFEST_v1_3.yaml)
- [SHA-256 ledger](metadata/SHA256SUMS_v1_3.txt)
- [Validation summary](validation/P12_Validation_Summary_v1_3.json)
- [Cross-module audit](validation/P12_Cross_Module_Audit_v1_3.md)
- [Freeze contract](validation/GO_Corpus_Freeze_Contract_v1_3.yaml)
- [Publication supplement and reproducibility errata](PUBLICATION_SUPPLEMENT.md)
- [Immutable OSF corpus registration](https://osf.io/ge92j/) — DOI `10.17605/OSF.IO/GE92J`

The original P12 bundle is attached to GitHub release `v1.3.0`. The exact local release asset is retained in `release-assets/` for publication staging and is excluded from ordinary Git history. A clean-room publication audit found omitted validator-side QA artefacts and one P11 portability-threshold inconsistency; these are disclosed and repaired by [PUBLICATION_SUPPLEMENT.md](PUBLICATION_SUPPLEMENT.md). The original ZIP alone must not be described as self-contained for 51/51 replay.

## Release evidence

| Object | SHA-256 |
|---|---|
| Master PDF | `3942277bc24ce6c134876bf27d322e03869a40e7d52eb084bcab6b3c885bf2d2` |
| Full release bundle | `497c16c5e86279025066fbf48954e067bd53bd2cad970545d32000d7e0327ee6` |
| Publication supplement 1 | `d62d8eacd6b41e2951af7fab42e1b9506ef832c235844f5c83cbfc3db8adbae1` |

The frozen audit records:

- 18 `PASS`, 0 `FAIL`, 0 `BLOCKED` modules;
- 347 typed expressions and 0 recorded findings;
- 259/259 P12 tests and all eleven inherited phase validators passing;
- 166/166 master pages independently rendered and checked;
- an acyclic dependency graph with 29 nodes and 36 normative edges;
- a deterministic 101-entry release archive.

These checks establish internal consistency and reproducibility of the declared release contract. They are not a substitute for independent proof review, literature review, experimental validation, or journal peer review.

## Repository layout

```text
corpus/                 canonical master and component PDFs
work/                   exact sources, ledgers, tests, and build scripts
output/                 P0 canonical PDF outputs
inherited_phase_bundles/ frozen P1-P11 source bundles
metadata/               release, archive, and checksum metadata
validation/             freeze contract and P12 audit records
release-assets/          local release assets; excluded from Git history
```

## Reproduction

From the repository root:

```bash
python3 scripts/restore_publication_qa.py
python3 work/p12_corpus_master_v1_3/scripts/build_p12_master.py
python3 -m unittest -q work/p12_corpus_master_v1_3/tests/test_p12_corpus_master_v1_3.py
python3 work/p12_corpus_master_v1_3/tests/validate_p12_release.py
```

The full build requires the dependencies and executables used by the P1-P12 validators, including a compatible Python 3 environment, XeLaTeX, and PDF processing utilities. See the phase scripts and validation output for the exact invoked checks.

## Claim boundaries

Read [KNOWN_LIMITATIONS.md](KNOWN_LIMITATIONS.md) before citing or extending the corpus. Corrections to the frozen release are recorded in [ERRATA.md](ERRATA.md); files attached to `v1.3.0` must never be silently replaced.

## Citation

Use [CITATION.cff](CITATION.cff). The primary corpus identifier is [doi:10.17605/OSF.IO/GE92J](https://doi.org/10.17605/OSF.IO/GE92J), which resolves to the immutable Open-Ended Registration. The GitHub tag `v1.3.0` remains the canonical source identifier. The DOI and registration do not imply peer review.

## Licence

Original corpus content is distributed under [CC BY-NC-ND 4.0](LICENSE.md). Third-party works and references remain under their respective terms.

## Contact

`theobserver.of.multiverses@proton.me`
