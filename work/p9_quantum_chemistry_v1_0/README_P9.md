# GO P9 — Quantum Chemistry v1.0 release workspace

This directory contains the reproducible source release for
`Quantum Chemistry as a Typed Inference Stack under Observation Maps
v1.1`.

## Rebuild

From the repository root:

```bash
python3 work/p9_quantum_chemistry_v1_0/scripts/generate_quantum_chemistry_benchmarks.py
latexmk -xelatex -interaction=nonstopmode -halt-on-error \
  -outdir=work/p9_quantum_chemistry_v1_0/build/qchem \
  work/p9_quantum_chemistry_v1_0/src/quantum_chemistry_observation_geometry_v1_1.tex
pdftotext -layout \
  work/p9_quantum_chemistry_v1_0/build/qchem/quantum_chemistry_observation_geometry_v1_1.pdf \
  work/p9_quantum_chemistry_v1_0/checks/qchem/quantum_chemistry_observation_geometry_v1_1.txt
python3 work/p9_quantum_chemistry_v1_0/tests/build_corpus_ledger_v1_0.py
```

After rebuilding the PDF, update its page count and SHA-256 in the
reference ledger, then regenerate the two lint reports:

```bash
python3 work/go_core_v0_2/src/go_lint.py \
  --core-dir work/go_core_v0_2/core \
  --ledger work/p9_quantum_chemistry_v1_0/ledgers/quantum_chemistry_reference_ledger_v1_0.yaml \
  --mode strict \
  --output-json work/p9_quantum_chemistry_v1_0/reports/Quantum_Chemistry_Reference_Lint_Report_v1_0.json \
  --output-md work/p9_quantum_chemistry_v1_0/reports/Quantum_Chemistry_Reference_Lint_Report_v1_0.md

python3 work/go_core_v0_2/src/go_lint.py \
  --core-dir work/go_core_v0_2/core \
  --ledger work/p9_quantum_chemistry_v1_0/ledgers/corpus_ledgers_v1_0.yaml \
  --mode audit \
  --output-json work/p9_quantum_chemistry_v1_0/reports/GO_Corpus_Lint_Report_v1_0.json \
  --output-md work/p9_quantum_chemistry_v1_0/reports/GO_Corpus_Lint_Report_v1_0.md
```

## Validate and package

```bash
python3 -m unittest -q \
  work/p9_quantum_chemistry_v1_0/tests/test_quantum_chemistry_v1_0.py
python3 work/p9_quantum_chemistry_v1_0/tests/validate_p9_release.py
python3 work/p9_quantum_chemistry_v1_0/tests/build_release_bundle.py
```

The full corpus strict run is expected to exit with status 1 until
`Regular Polyhedra` and `Satellite Networks` are migrated. The P9
validator treats the exact expected status
`16 PASS / 2 FAIL / 0 BLOCKED` as a controlled corpus condition, not as
a failure of the P9 reference.
