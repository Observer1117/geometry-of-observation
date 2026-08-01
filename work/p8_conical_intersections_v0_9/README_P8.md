# GO P8 Conical Intersections v0.9

This release replaces the legacy `conical-intersections-v1` critical
adapter with the strict reference
`conical-intersections-observation-v1-1`.

## Canonical artifact

- `src/conical_intersections_spectral_observation_v1_1.tex`
- `build/ci/conical_intersections_spectral_observation_v1_1.pdf`

## Normative dependencies

- GO Core v0.2
- Conical Intersections Observation contract v0.9

## Validation

Run from the workspace root:

```bash
python3 work/p8_conical_intersections_v0_9/scripts/generate_conical_intersections_benchmarks.py
latexmk -xelatex -interaction=nonstopmode -halt-on-error \
  -outdir=work/p8_conical_intersections_v0_9/build/ci \
  work/p8_conical_intersections_v0_9/src/conical_intersections_spectral_observation_v1_1.tex
pdftotext -layout \
  work/p8_conical_intersections_v0_9/build/ci/conical_intersections_spectral_observation_v1_1.pdf \
  work/p8_conical_intersections_v0_9/checks/ci/conical_intersections_spectral_observation_v1_1.txt
python3 work/p8_conical_intersections_v0_9/tests/build_corpus_ledger_v0_9.py
python3 work/go_core_v0_2/src/go_lint.py \
  --core-dir work/go_core_v0_2/core \
  --ledger work/p8_conical_intersections_v0_9/ledgers/conical_intersections_reference_ledger_v0_9.yaml \
  --mode strict
python3 -m unittest -v \
  work/p8_conical_intersections_v0_9/tests/test_conical_intersections_v0_9.py
python3 work/p8_conical_intersections_v0_9/tests/validate_p8_release.py
```

Expected results:

- reference ledger: 1 `PASS`, 36 expressions, 0 findings;
- corpus ledger: 15 `PASS`, 3 `FAIL`, 208 expressions;
- regression suite: 150 tests;
- benchmark table: 35 rows;
- rendered PDF: 8 pages.

The three corpus failures are retained legacy adapters, not failures
of the P8 conical-intersections reference.
