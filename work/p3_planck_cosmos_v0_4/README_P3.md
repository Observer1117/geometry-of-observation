# GO P3: Planck-to-Cosmos strict migration

This release migrates `Planck-to-Cosmos Observation Rulers v1.0` to the
GO Core distance-scale interface.

## Rebuild

From the repository root:

```bash
python3 work/p3_planck_cosmos_v0_4/scripts/generate_planck_cosmos_data.py
cd work/p3_planck_cosmos_v0_4/src
latexmk -xelatex -interaction=nonstopmode -halt-on-error \
  -file-line-error -outdir=../build/planck \
  planck_cosmos_observation_rulers_v1_1.tex
```

Return to the repository root before running validation:

```bash
python3 work/p3_planck_cosmos_v0_4/tests/build_corpus_ledger_v0_4.py
python3 work/go_core_v0_2/src/go_lint.py \
  --core-dir work/go_core_v0_2/core \
  --ledger work/p3_planck_cosmos_v0_4/ledgers/planck_cosmos_reference_ledger_v0_4.yaml \
  --mode strict \
  --output-json work/p3_planck_cosmos_v0_4/reports/Planck_Cosmos_Lint_Report_v0_4.json \
  --output-md work/p3_planck_cosmos_v0_4/reports/Planck_Cosmos_Lint_Report_v0_4_ru.md
python3 -m unittest -v \
  work/p3_planck_cosmos_v0_4/tests/test_planck_cosmos_v0_4.py
```

The rounded cosmological horizon and the Planck 2018 parameter subset
are an illustrative typed landmark ledger. They are not presented as a
current precision cosmological parameter fit.

