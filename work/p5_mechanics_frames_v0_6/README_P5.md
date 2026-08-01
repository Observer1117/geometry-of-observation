# GO P5: frames, forces, constraints, and dissipation

This release adds a common typed mechanics interface and migrates the
Foucault, bobsleigh, and roller-coaster modules to it.

## Rebuild the PDFs

From the repository root:

```bash
latexmk -g -xelatex -interaction=nonstopmode -halt-on-error \
  -outdir=work/p5_mechanics_frames_v0_6/build/interface \
  work/p5_mechanics_frames_v0_6/src/frame_force_dissipation_interface_v0_1.tex
latexmk -g -xelatex -interaction=nonstopmode -halt-on-error \
  -outdir=work/p5_mechanics_frames_v0_6/build/foucault \
  work/p5_mechanics_frames_v0_6/src/celestial_foucault_networks_v1_1.tex
latexmk -g -xelatex -interaction=nonstopmode -halt-on-error \
  -outdir=work/p5_mechanics_frames_v0_6/build/bobsleigh \
  work/p5_mechanics_frames_v0_6/src/bobsleigh_contact_geometry_v1_1.tex
latexmk -g -xelatex -interaction=nonstopmode -halt-on-error \
  -outdir=work/p5_mechanics_frames_v0_6/build/roller \
  work/p5_mechanics_frames_v0_6/src/roller_coaster_geometry_v1_1.tex
```

## Rebuild ledgers and lint reports

```bash
python3 work/p5_mechanics_frames_v0_6/tests/build_corpus_ledger_v0_6.py
python3 work/go_core_v0_2/src/go_lint.py \
  --core-dir work/go_core_v0_2/core \
  --ledger work/p5_mechanics_frames_v0_6/ledgers/mechanics_reference_ledgers_v0_6.yaml \
  --mode strict \
  --output-json work/p5_mechanics_frames_v0_6/reports/Mechanics_Reference_Lint_Report_v0_6.json \
  --output-md work/p5_mechanics_frames_v0_6/reports/Mechanics_Reference_Lint_Report_v0_6_ru.md
python3 work/go_core_v0_2/src/go_lint.py \
  --core-dir work/go_core_v0_2/core \
  --ledger work/p5_mechanics_frames_v0_6/ledgers/corpus_ledgers_v0_6.yaml \
  --mode audit \
  --output-json work/p5_mechanics_frames_v0_6/reports/GO_Corpus_Lint_Report_v0_6.json \
  --output-md work/p5_mechanics_frames_v0_6/reports/GO_Corpus_Lint_Report_v0_6_ru.md
```

## Run validation

```bash
python3 -m unittest -v \
  work.p5_mechanics_frames_v0_6.tests.test_mechanics_frames_v0_6
python3 work/p5_mechanics_frames_v0_6/tests/validate_p5_release.py
python3 work/p5_mechanics_frames_v0_6/tests/build_release_bundle.py
```

The full corpus strict run is expected to return a nonzero exit code
until the six remaining critical adapters are migrated.
