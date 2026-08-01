# GO P2 Distance-Scale Migration

This release contains two strict reference modules:

1. `Distance and Scale Interface under Observation Maps v0.2`;
2. `Mandelbrot Rulers as Observation-Scale Geometry v1.1`.

They extend `GO Core v0.2` with `GO Distance-Scale Contract v0.3`.

## Reproduce the checks

From the workspace root:

```bash
python3 work/go_core_v0_2/src/go_lint.py \
  --core-dir work/go_core_v0_2/core \
  --ledger work/p2_distance_scale_v0_3/ledgers/distance_scale_mandelbrot_reference_ledgers_v0_3.yaml \
  --mode strict

python3 -m unittest \
  work/p2_distance_scale_v0_3/tests/test_distance_scale_mandelbrot_v0_3.py -v

python3 work/p2_distance_scale_v0_3/tests/validate_p2_release.py
```

Rebuild the PDFs:

```bash
cd work/p2_distance_scale_v0_3/src
latexmk -xelatex -interaction=nonstopmode -halt-on-error \
  -outdir=../build/distance \
  distance_scale_interface_observation_maps_v0_2.tex
latexmk -xelatex -interaction=nonstopmode -halt-on-error \
  -outdir=../build/mandelbrot \
  mandelbrot_rulers_observation_scale_v1_1.tex
```

## Gate interpretation

- `PASS` means that every registered expression and protocol field in the
  reference ledger passes the executable contract.
- It is not a machine-checked proof of every statement in the LaTeX source.
- The full corpus remains intentionally non-passing until the remaining
  adapters are migrated.
