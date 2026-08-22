# P1.7 target-staging kit

This directory defines the execution and evidence contract for **P1.7**, the
target-host compatibility gate for the Observer Research Registry. It does not
deploy a site, purchase a plan, merge code, change DNS, or authorize production.

## Current checkpoint

| Item | Frozen state |
| --- | --- |
| Hosting route | WordPress.com Business selected |
| Business purchase | **Deferred; plan not activated** |
| Bootstrap-site address | `https://observermultiversesresearch.wordpress.com/` (planned, not provisioned) |
| Native staging instance | Not created |
| Public domain | `https://theobserverofmultiverses.info/` remains the Gravatar profile |
| Production/DNS mutation | Prohibited |
| P1.7 verdict | **NO-GO until target-host execution is complete** |

The purchase deferral is an infrastructure state, not a plugin defect. Every
E/A/I/R/T/C/S/Q result remains `NOT_RUN` until the selected Business plan,
bootstrap site, and isolated native staging instance actually exist.

## Immutable P1.6 input

P1.7 is stacked on the already validated P1.6 implementation candidate. It is
not a replacement release and it does not imply that PR #3 should be merged.

| Binding | Exact value |
| --- | --- |
| Repository | `Observer1117/geometry-of-observation` |
| Candidate pull request | [Draft PR #3](https://github.com/Observer1117/geometry-of-observation/pull/3) |
| PR head | `4e7dff23bb53056d559fe44fc43a74c55eb27b10` |
| PR base at preflight | `bab4480e50f8abe32087da765a145575a4519f8a` |
| Plugin | `observer-research-registry` version `0.1.0` |
| Installation artifact | `observer-research-registry-0.1.0.zip` |
| Artifact SHA-256 | `0d29a680f9aa478d2da3167b64bdbd0570839b2fd7cf9168159e8d4317e3e3d7` |
| Bundled registry source | `bab4480e50f8abe32087da765a145575a4519f8a` |
| Expected first import | five `research_output` drafts |

The ZIP hash must be recomputed **after transfer to the target staging stack**.
Any changed byte, new plugin build, new commit, or changed registry input breaks
this binding and requires a new version, hash, review record, and evidence run.
Local and WordPress Playground results may be cited as P1.6 provenance, but they
cannot be substituted for target-host results.

## Files

- `p1-7-environment-probe.php` emits a sanitized target inventory and proves
  connection-owned MySQL/MariaDB advisory-lock semantics. It must run only with
  WP-CLI on the native staging instance.
- `p1-7-wp-runner.sh` is read-only by default. Its mutation mode is hash-bound,
  accepts only a native `staging-*.wpcomstaging.com` host, refuses the public
  domain, requires external restore/access evidence IDs, and asserts the exact
  `5/0/0` then `0/0/5` synchronization results.
- `p1-7-http-audit.py` is an anonymous, GET-only, offline-by-default auditor for
  routes, redirects, REST, noindex/robots/sitemap suppression, canonical and
  social metadata, JSON-LD identities, cache signals, and scientific boundary
  markers. Network access requires the explicit `--allow-network` flag.
- `p1-7-evidence.schema.json` is the machine-readable, strict, versioned
  evidence contract.
- `P1.7_EXECUTION_LEDGER_TEMPLATE.md` is the operator-facing runbook and gate
  ledger.

The canonical prior preflight is
`artifacts/P1.7_TARGET_STAGING_PREFLIGHT_2026-08-12.md`. The P1.6 implementation
boundary and recovery model are documented in
`website/wordpress-plugin/observer-research-registry/README.md` and
`website/wordpress-plugin/observer-research-registry/P1.6_IMPLEMENTATION_AUDIT.md`.

## Execution order

P1.7 may resume only after the Business plan and isolated staging environment
exist. Execute the families in this order:

| Family | Purpose | Blocking scope |
| --- | --- | --- |
| E | Environment, isolation, inventory, backup and demonstrated restore | Must precede plugin upload |
| A | Artifact provenance, installation and activation | Exact hash-bound ZIP only |
| I | Import, idempotence, locking, crash recovery and authority protection | No ambiguous or partial state |
| R | Permalinks, routes, canonical behavior and REST | Protected staging only |
| T | Exact target theme and accessibility | Exact intended theme stack |
| C | Object/page cache, CDN, proxy and invalidation | Exact intended cache stack |
| S | Canonical/JSON-LD/SEO graph and claim boundaries | No duplicate or elevated claims |
| Q | Capabilities, lifecycle and clean logs | Includes disposable uninstall test |

The execution sequence is:

1. Provision the WordPress.com Business bootstrap site at the planned temporary
   address and create its native isolated staging instance.
2. Confirm access controls and search-engine exclusion before adding content.
3. Record E1-E3 and create a provider backup.
4. Demonstrate restoration to a disposable clone or equivalent isolated
   checkpoint (E4). A provider promise or dashboard label is not evidence.
5. Complete E5, transfer the frozen ZIP, and verify its SHA-256 on target.
6. Execute A, I, R, T, C, S, and Q in order from the ledger.
7. Store only sanitized evidence summaries and references, validate the evidence
   JSON against the schema, and assign `GO` or `NO-GO`.
8. Even after a P1.7 `GO`, prepare a separate production-activation plan and
   obtain separate approval. P1.7 never authorizes production by itself.

## Status vocabulary

Each gate has exactly one status:

- `PASS` — the required result was observed on the actual target staging stack;
- `FAIL` — the target result contradicts the required result or is unsafe;
- `SKIP` — the gate is proven inapplicable, with a written reason and evidence;
- `NOT_RUN` — the gate has not been executed on the target stack.

A local test, documentation review, Playground run, or provider feature list
does not change a target-host gate from `NOT_RUN` to `PASS`. For this selected
route, a P1.7 `GO` requires all 37 named gates to be `PASS`; `SKIP` is retained
in the schema for truthful partial/NO-GO records, not as a shortcut to GO.

## Backup, restore and abort contract

Before activation, record the provider backup/checkpoint identifier and prove a
restore into an isolated target. Do not place database dumps or credentials in
this directory or in the evidence archive.

Immediately stop writes, preserve the current journal and diagnostic state, and
assign `NO-GO` if any of the following occurs:

- artifact hash mismatch or provenance drift;
- any request resolves to or mutates the public domain;
- any domain assignment, nameserver, DNS, Gravatar, or production change;
- staging is public/indexable or access controls are ineffective;
- backup creation or demonstrated restoration is unavailable;
- MySQL/MariaDB connection-owned advisory locks are blocked or unreliable;
- a concurrent/failure-injection run leaves partial or ambiguous state;
- rollback proposes deleting a record whose conservative fingerprint changed;
- scientific machine metadata accepts an unauthorized write;
- a resync overwrites editorial content, media, author, status, or layout;
- PHP fatal/warning, runtime external fetch, or security-control regression;
- evidence contains a secret, credential, cookie, token, private key, payment
  detail, `wp-config.php`, database dump, or unsanitized private log.

After an abort, do not improvise cleanup. Capture sanitized evidence, retain any
unresolved importer journal, restore the disposable checkpoint when safe, and
open a corrective change separately. A rerun must start from a documented clean
checkpoint and use a new evidence record.

## Production preservation boundary

Throughout P1.7 all of the following are immutable prohibitions:

- do not assign `theobserverofmultiverses.info` to the bootstrap or staging site;
- do not change nameservers, DNS records, DNSSEC, redirects, SSL routing, or
  Gravatar domain configuration;
- do not install or activate the plugin on the public domain;
- do not publish the five records outside protected staging;
- do not merge PR #3 merely to make a deployment artifact;
- do not treat a P1.7 `GO` as production approval.

## Evidence policy

Evidence is an audit index, not a secret-bearing archive. Store concise command
or HTTP summaries, version inventories, sanitized screenshots, content hashes,
and provider evidence references. Every evidence item must state that it
contains no secret material. Raw logs stay in an access-controlled operational
location and enter the ledger only through redacted counts and summaries.

Never store or commit:

- usernames paired with authentication details;
- passwords, application passwords, API keys, OAuth tokens, cookies, nonces,
  private keys, SSH material, or recovery codes;
- payment details or checkout screenshots containing them;
- `wp-config.php`, environment-variable dumps, database exports, or full backup
  archives;
- raw request headers carrying authorization/session data;
- personal data not necessary to prove a gate.

Use opaque evidence IDs from the JSON record in the Markdown ledger. Hash local
evidence files before storage and redact first, hash second. A secret scan must
pass before a P1.7 `GO`.

## Machine validation

Validate every offline contract and reproduce the staging-kit bytes with:

```bash
python3 website/scripts/validate_registry.py
python3 website/scripts/validate_wordpress_plugin.py
python3 website/scripts/validate_p1_7_staging_kit.py
python3 -m unittest discover -s website/staging/tests -p 'test_*.py' -v
python3 website/scripts/build_p1_7_staging_kit.py /tmp/p1-7-staging-kit-0.1.0.zip
```

After Business activation, complete E1-E5 and record the provider restore and
access-control evidence IDs. Then run the immutable staging guards first, with
no mutation:

```bash
bash staging/p1-7-wp-runner.sh \
  --plugin-zip observer-research-registry-0.1.0.zip \
  --evidence-dir ./evidence-read-only \
  --expected-home https://staging-XXXX-example.wpcomstaging.com
```

Only after the read-only result and E1-E5 evidence are independently reviewed,
repeat against a documented clean checkpoint with `--restore-proof-id`,
`--access-proof-id`, and `--execute`. The runner does not publish records,
change permalinks, or exercise destructive failure/lifecycle gates; finish
those controlled cases manually from the ledger on disposable checkpoints.

Run the external HTTP auditor only if the protected staging policy permits this
anonymous auditor to see the test pages (for example, through an allowlisted
source). Never disable access protection merely to make the tool pass. If the
provider protection returns a login/Coming Soon page, keep it enabled and
capture R/S/C content evidence through the authenticated manual path instead.

```bash
python3 staging/p1-7-http-audit.py \
  --base-url https://staging-XXXX-example.wpcomstaging.com \
  --expected-host staging-XXXX-example.wpcomstaging.com \
  --output ./evidence-http.json \
  --allow-network
```

The schema itself can be checked with:

```bash
python3 -m json.tool website/staging/p1-7-evidence.schema.json >/dev/null
```

With the Python `jsonschema` package installed, validate the schema and an
evidence instance with:

```bash
python3 - <<'PY'
import json
from pathlib import Path
from jsonschema import Draft202012Validator

schema = json.loads(Path("website/staging/p1-7-evidence.schema.json").read_text())
record = json.loads(Path("p1-7-evidence.json").read_text())
Draft202012Validator.check_schema(schema)
Draft202012Validator(schema).validate(record)
PY
```

The final decision is binary. `GO` means only that the exact P1.6 candidate
passed the complete matrix on the selected target staging environment with a
demonstrated restore path. Every incomplete, skipped, failed, drifted, or
unsafe run is `NO-GO`.
