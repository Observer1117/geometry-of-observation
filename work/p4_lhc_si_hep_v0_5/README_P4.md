# GO P4: SI--HEP quantity passport and LHC strict migration

This release adds a reversible dimensional passport between SI and the
mechanical HEP natural-unit chart and migrates the LHC beam-observation
module to that contract.

## Rebuild generated data

From the repository root:

```bash
python3 work/p4_lhc_si_hep_v0_5/scripts/generate_lhc_si_hep_data.py
```

## Rebuild the PDFs

```bash
cd work/p4_lhc_si_hep_v0_5/src
latexmk -xelatex -interaction=nonstopmode -halt-on-error \
  -file-line-error -outdir=../build/passport \
  si_hep_quantity_passport_v0_5.tex
latexmk -xelatex -interaction=nonstopmode -halt-on-error \
  -file-line-error -outdir=../build/lhc \
  lhc_beam_observation_geometry_v1_3.tex
```

Return to the repository root before running validation.

## Rebuild the ledgers and lint reports

```bash
python3 work/p4_lhc_si_hep_v0_5/tests/build_corpus_ledger_v0_5.py
python3 work/go_core_v0_2/src/go_lint.py \
  --core-dir work/go_core_v0_2/core \
  --ledger work/p4_lhc_si_hep_v0_5/ledgers/lhc_si_hep_reference_ledgers_v0_5.yaml \
  --mode strict \
  --output-json work/p4_lhc_si_hep_v0_5/reports/LHC_SI_HEP_Lint_Report_v0_5.json \
  --output-md work/p4_lhc_si_hep_v0_5/reports/LHC_SI_HEP_Lint_Report_v0_5_ru.md
python3 work/go_core_v0_2/src/go_lint.py \
  --core-dir work/go_core_v0_2/core \
  --ledger work/p4_lhc_si_hep_v0_5/ledgers/corpus_ledgers_v0_5.yaml \
  --mode audit \
  --output-json work/p4_lhc_si_hep_v0_5/reports/GO_Corpus_Lint_Report_v0_5.json \
  --output-md work/p4_lhc_si_hep_v0_5/reports/GO_Corpus_Lint_Report_v0_5_ru.md
```

## Run regression and release validation

```bash
python3 -m unittest -v \
  work.p4_lhc_si_hep_v0_5.tests.test_lhc_si_hep_v0_5
python3 work/p4_lhc_si_hep_v0_5/tests/validate_p4_release.py
```

The \(6.8\,\mathrm{TeV}\) beam energy is a Run 3 standard-operation
reference. On the document date, 2026-07-28, the LHC is in Long
Shutdown 3. Operational and rounded machine values are not promoted to
exact constants.
