# GO P1 Information + Metric Entropy v0.2

This directory contains the two P1 reference migrations built on GO Core v0.2.

## Documents

- `information_theoretic_observation_geometry_v0_2.tex`
- `metric_entropy_observational_defect_v0_2.tex`

## Build

From `src/`:

```bash
latexmk -xelatex -interaction=nonstopmode -halt-on-error \
  -outdir=../build/information \
  information_theoretic_observation_geometry_v0_2.tex

latexmk -xelatex -interaction=nonstopmode -halt-on-error \
  -outdir=../build/metric \
  metric_entropy_observational_defect_v0_2.tex
```

## Verify

From the workspace root:

```bash
python3 work/go_core_v0_2/src/go_lint.py \
  --core-dir work/go_core_v0_2/core \
  --ledger work/p1_info_metric_v0_2/ledgers/information_metric_reference_ledgers_v0_2.yaml \
  --mode strict

python3 -m unittest -v \
  work/p1_info_metric_v0_2/tests/test_information_metric_v0_2.py
```

The complete corpus ledger is `ledgers/corpus_ledgers_v0_2.yaml`. Its full
strict run is expected to fail until the remaining critical adapters are
migrated. A strict run restricted to `reference` ledgers must pass.

