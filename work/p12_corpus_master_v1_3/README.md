# Geometry of Observation P12 corpus master v1.3

This directory builds the frozen master release for the clean
eighteen-module GO Core corpus.

The master is a provenance and reproducibility object. It concatenates
the exact canonical component PDFs after a release front matter; it does
not rewrite component claims or promote the corpus into one physical
theory.

## Build

From the repository root:

```bash
python3 work/p12_corpus_master_v1_3/scripts/build_p12_master.py
```

The command generates the freeze ledger and TeX tables, compiles the
front matter with XeLaTeX, creates the bookmarked master PDF, and writes
the component page map and checksums.

## Validate

```bash
python3 -m unittest -q \
  work/p12_corpus_master_v1_3/tests/test_p12_corpus_master_v1_3.py
python3 work/p12_corpus_master_v1_3/tests/validate_p12_release.py
```

The final gate also replays every P1-P11 release validator and checks
all component PDF intervals inside the master.

## Package

```bash
python3 work/p12_corpus_master_v1_3/tests/build_release_bundle.py
python3 work/p12_corpus_master_v1_3/tests/validate_p12_release.py
python3 work/p12_corpus_master_v1_3/tests/build_release_bundle.py
```

The final bundle uses fixed timestamps and sorted members. A repeated
build must be byte-identical.
