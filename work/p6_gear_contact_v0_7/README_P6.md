# GO P6 Gear Contact v0.7

This release replaces the legacy `gear-contact-v1` critical adapter
with the strict reference `gear-contact-v1-1`.

## Canonical artifact

- `src/gear_contact_geometry_v1_1.tex`
- `build/gear/gear_contact_geometry_v1_1.pdf`

## Normative dependencies

- GO Core v0.2
- Frames--Forces--Constraints--Dissipation contract v0.6
- Gear Contact contract v0.7

## Validation

Run from the workspace root:

```bash
python3 work/p6_gear_contact_v0_7/tests/build_corpus_ledger_v0_7.py
python3 work/go_core_v0_2/src/go_lint.py \
  --core-dir work/go_core_v0_2/core \
  --ledger work/p6_gear_contact_v0_7/ledgers/gear_contact_reference_ledger_v0_7.yaml \
  --mode strict
python3 -m unittest -v \
  work/p6_gear_contact_v0_7/tests/test_gear_contact_v0_7.py
python3 work/p6_gear_contact_v0_7/tests/validate_p6_release.py
```

Expected results:

- reference ledger: 1 `PASS`, 20 expressions, 0 findings;
- corpus ledger: 13 `PASS`, 5 `FAIL`, 151 expressions;
- regression suite: 55 tests;
- release validator: 16 checks.

The five corpus failures are retained legacy adapters, not failures of
the P6 gear-contact reference.
