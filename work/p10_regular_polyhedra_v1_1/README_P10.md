# GO P10 — Regular Polyhedra v1.1 release workspace

This directory contains the reproducible source release for
`Regular Polyhedra under Typed Observation Filters v1.1`.

## Rebuild

From the repository root:

```bash
python3 work/p10_regular_polyhedra_v1_1/scripts/generate_regular_polyhedra_benchmarks.py
latexmk -xelatex -interaction=nonstopmode -halt-on-error \
  -outdir=work/p10_regular_polyhedra_v1_1/build/polyhedra \
  work/p10_regular_polyhedra_v1_1/src/regular_polyhedra_observation_filters_v1_1.tex
pdftotext -layout \
  work/p10_regular_polyhedra_v1_1/build/polyhedra/regular_polyhedra_observation_filters_v1_1.pdf \
  work/p10_regular_polyhedra_v1_1/checks/polyhedra/regular_polyhedra_observation_filters_v1_1.txt
python3 work/p10_regular_polyhedra_v1_1/tests/build_corpus_ledger_v1_1.py
```

After rebuilding the PDF, update its page count and SHA-256 in the
reference ledger, then regenerate the reference and corpus lint reports.

```bash
python3 work/go_core_v0_2/src/go_lint.py \
  --core-dir work/go_core_v0_2/core \
  --ledger work/p10_regular_polyhedra_v1_1/ledgers/regular_polyhedra_reference_ledger_v1_1.yaml \
  --mode strict \
  --output-json work/p10_regular_polyhedra_v1_1/reports/Regular_Polyhedra_Reference_Lint_Report_v1_1.json \
  --output-md work/p10_regular_polyhedra_v1_1/reports/Regular_Polyhedra_Reference_Lint_Report_v1_1.md

python3 work/go_core_v0_2/src/go_lint.py \
  --core-dir work/go_core_v0_2/core \
  --ledger work/p10_regular_polyhedra_v1_1/ledgers/corpus_ledgers_v1_1.yaml \
  --mode audit \
  --output-json work/p10_regular_polyhedra_v1_1/reports/GO_Corpus_Lint_Report_v1_1.json \
  --output-md work/p10_regular_polyhedra_v1_1/reports/GO_Corpus_Lint_Report_v1_1.md
```

## Validate and package

```bash
python3 -m unittest -q \
  work/p10_regular_polyhedra_v1_1/tests/test_regular_polyhedra_v1_1.py
python3 work/p10_regular_polyhedra_v1_1/tests/validate_p10_release.py
python3 work/p10_regular_polyhedra_v1_1/tests/build_release_bundle.py
```

The full corpus strict run is expected to exit with status 1 until
`Satellite Networks` is migrated. The P10 validator treats the exact
expected status `17 PASS / 1 FAIL / 0 BLOCKED` as a controlled corpus
condition, not as a failure of the P10 reference.
