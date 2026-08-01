# GO P7 Billiards v0.8

This release replaces the legacy `billiards-observation-v1` critical
adapter with the strict reference `billiards-observation-v1-1`.

## Canonical artifact

- `src/billiards_observation_laboratory_v1_1.tex`
- `build/billiards/billiards_observation_laboratory_v1_1.pdf`

## Normative dependencies

- GO Core v0.2
- Information-Theoretic Observation reference v0.2
- Frames--Forces--Constraints--Dissipation contract v0.6
- Billiards Observation contract v0.8

## Validation

Run from the workspace root:

```bash
python3 work/p7_billiards_v0_8/scripts/generate_billiards_benchmarks.py
python3 work/p7_billiards_v0_8/tests/build_corpus_ledger_v0_8.py
python3 work/go_core_v0_2/src/go_lint.py \
  --core-dir work/go_core_v0_2/core \
  --ledger work/p7_billiards_v0_8/ledgers/billiards_reference_ledger_v0_8.yaml \
  --mode strict
python3 -m unittest -v \
  work/p7_billiards_v0_8/tests/test_billiards_v0_8.py
python3 work/p7_billiards_v0_8/tests/validate_p7_release.py
```

Expected results:

- reference ledger: 1 `PASS`, 24 expressions, 0 findings;
- corpus ledger: 14 `PASS`, 4 `FAIL`, 173 expressions;
- regression suite: 95 tests;
- release validator: 18 checks.

The four corpus failures are retained legacy adapters, not failures of
the P7 Billiards reference.

