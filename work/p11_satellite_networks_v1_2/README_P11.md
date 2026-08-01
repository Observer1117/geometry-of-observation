# GO P11 — Satellite Networks v1.2 release workspace

This directory contains the reproducible source release for
`Satellite Networks under Typed Frames and Temporal Observation Channels v1.2`.

## Rebuild

From the repository root:

```bash
python3 work/p11_satellite_networks_v1_2/scripts/generate_satellite_network_benchmarks.py
latexmk -xelatex -interaction=nonstopmode -halt-on-error \
  -outdir=work/p11_satellite_networks_v1_2/build/satellite \
  work/p11_satellite_networks_v1_2/src/satellite_networks_typed_frames_v1_2.tex
pdftotext -layout \
  work/p11_satellite_networks_v1_2/build/satellite/satellite_networks_typed_frames_v1_2.pdf \
  work/p11_satellite_networks_v1_2/checks/satellite/satellite_networks_typed_frames_v1_2.txt
python3 work/p11_satellite_networks_v1_2/scripts/build_satellite_reference_ledger_v1_2.py
python3 work/p11_satellite_networks_v1_2/tests/build_corpus_ledger_v1_2.py
```

The ledger builders also regenerate the strict reference-lint and full
corpus-lint reports.

## Render and inspect

```bash
pdftoppm -png -r 150 \
  work/p11_satellite_networks_v1_2/build/satellite/satellite_networks_typed_frames_v1_2.pdf \
  work/p11_satellite_networks_v1_2/render/satellite/page
```

The release requires all eight pages to pass visual inspection and the
LaTeX log to contain no layout or reference warnings.

## Validate and package

```bash
python3 -m unittest -q \
  work/p11_satellite_networks_v1_2/tests/test_satellite_networks_v1_2.py
python3 work/p11_satellite_networks_v1_2/tests/validate_p11_release.py
python3 work/p11_satellite_networks_v1_2/tests/build_release_bundle.py
```

The expected corpus result is `18 PASS / 0 FAIL / 0 BLOCKED`, with 347
typed expressions and no findings.
