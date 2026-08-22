#!/usr/bin/env bash
set -euo pipefail

readonly EXPECTED_PLUGIN_SHA256="0d29a680f9aa478d2da3167b64bdbd0570839b2fd7cf9168159e8d4317e3e3d7"
readonly FORBIDDEN_PRODUCTION_HOST="theobserverofmultiverses.info"
readonly EXPECTED_STAGING_SUFFIX=".wpcomstaging.com"
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

plugin_zip=""
evidence_dir=""
expected_home=""
restore_proof_id=""
access_proof_id=""
execute=0

usage() {
  cat <<'EOF'
Usage:
  p1-7-wp-runner.sh --plugin-zip PATH --evidence-dir DIR --expected-home URL \
    [--restore-proof-id ID --access-proof-id ID --execute]

The default mode is read-only: it verifies staging guards, captures the
environment probe, and prints the mutation plan. --execute permits plugin
installation and two registry synchronizations only after every guard passes.
Mutation mode additionally requires evidence IDs for the demonstrated restore
and protected-access checks. It never publishes posts, changes DNS, or touches
the Gravatar domain.
EOF
}

while (($#)); do
  case "$1" in
    --plugin-zip)
      plugin_zip="${2:-}"
      shift 2
      ;;
    --evidence-dir)
      evidence_dir="${2:-}"
      shift 2
      ;;
    --expected-home)
      expected_home="${2:-}"
      shift 2
      ;;
    --restore-proof-id)
      restore_proof_id="${2:-}"
      shift 2
      ;;
    --access-proof-id)
      access_proof_id="${2:-}"
      shift 2
      ;;
    --execute)
      execute=1
      shift
      ;;
    --help|-h)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ -z "$plugin_zip" || -z "$evidence_dir" || -z "$expected_home" ]]; then
  usage >&2
  exit 2
fi

for command in wp sha256sum python3; do
  command -v "$command" >/dev/null 2>&1 || {
    echo "Required command is unavailable: $command" >&2
    exit 3
  }
done

[[ -f "$plugin_zip" ]] || {
  echo "Plugin ZIP not found." >&2
  exit 3
}

case "$expected_home" in
  https://*) ;;
  *)
    echo "Expected home URL must use HTTPS." >&2
    exit 4
    ;;
esac

expected_host="$(python3 - "$expected_home" <<'PY'
import sys
from urllib.parse import urlsplit

url = urlsplit(sys.argv[1])
if url.username or url.password or url.query or url.fragment or url.path not in ("", "/"):
    raise SystemExit(2)
print((url.hostname or "").lower())
PY
)" || {
  echo "Expected home URL must contain only an HTTPS origin." >&2
  exit 4
}

if [[ -z "$expected_host" || "$expected_host" == "$FORBIDDEN_PRODUCTION_HOST" || "$expected_host" == *."$FORBIDDEN_PRODUCTION_HOST" ]]; then
  echo "Refusing to target the production/Gravatar domain." >&2
  exit 4
fi
if [[ "$expected_host" != staging-*"$EXPECTED_STAGING_SUFFIX" ]]; then
  echo "Expected host is not a WordPress.com native staging hostname." >&2
  exit 4
fi

actual_plugin_sha="$(sha256sum "$plugin_zip" | awk '{print $1}')"
if [[ "$actual_plugin_sha" != "$EXPECTED_PLUGIN_SHA256" ]]; then
  echo "Plugin SHA-256 mismatch; refusing to continue." >&2
  exit 5
fi

wp core is-installed >/dev/null

environment_type="$(wp eval 'echo wp_get_environment_type();' --skip-themes --quiet)"
if [[ "$environment_type" != "staging" ]]; then
  echo "WP_ENVIRONMENT_TYPE is not staging; refusing to continue." >&2
  exit 6
fi

actual_home="$(wp option get home --format=plaintext --quiet)"
actual_siteurl="$(wp option get siteurl --format=plaintext --quiet)"
actual_host="$(python3 - "$actual_home" <<'PY'
import sys
from urllib.parse import urlsplit
print((urlsplit(sys.argv[1]).hostname or "").lower())
PY
)"
if [[ "$actual_home" != "${expected_home%/}" && "$actual_home" != "${expected_home%/}/" ]]; then
  echo "WordPress home URL does not match --expected-home." >&2
  exit 6
fi
if [[ "$actual_host" != "$expected_host" || "$actual_host" == "$FORBIDDEN_PRODUCTION_HOST" || "$actual_host" == *."$FORBIDDEN_PRODUCTION_HOST" ]]; then
  echo "WordPress home host failed the staging host guard." >&2
  exit 6
fi
case "$actual_siteurl" in
  https://"$expected_host"|https://"$expected_host"/) ;;
  *)
    echo "WordPress siteurl failed the staging HTTPS/host guard." >&2
    exit 6
    ;;
esac

if [[ "$(wp eval 'echo is_multisite() ? "1" : "0";' --skip-themes --quiet)" != "0" ]]; then
  echo "Multisite is outside the P1.7 contract." >&2
  exit 6
fi

if [[ "$(wp option get blog_public --format=plaintext --quiet)" != "0" ]]; then
  echo "Search-engine visibility is not disabled on staging." >&2
  exit 6
fi

if wp plugin is-installed observer-research-registry >/dev/null 2>&1; then
  echo "Observer Research Registry is already installed; use a documented clean checkpoint." >&2
  exit 6
fi

if [[ "$execute" == 1 ]]; then
  for proof_id in "$restore_proof_id" "$access_proof_id"; do
    if [[ ! "$proof_id" =~ ^[A-Za-z0-9][A-Za-z0-9._:-]{2,127}$ ]]; then
      echo "Mutation mode requires sanitized restore/access evidence IDs." >&2
      exit 7
    fi
  done
fi

umask 077
mkdir -p "$evidence_dir"
environment_output="$evidence_dir/environment.json"
wp eval-file "$SCRIPT_DIR/p1-7-environment-probe.php" --skip-themes --quiet >"$environment_output"
python3 -m json.tool "$environment_output" >/dev/null

cat >"$evidence_dir/artifact.json" <<EOF
{
  "plugin_file": "observer-research-registry-0.1.0.zip",
  "sha256": "$actual_plugin_sha",
  "expected_home": "$expected_home",
  "environment_type": "$environment_type",
  "restore_proof_id": "$restore_proof_id",
  "access_proof_id": "$access_proof_id",
  "mode": "$([[ "$execute" == 1 ]] && echo execute || echo read-only)"
}
EOF

if [[ "$execute" != 1 ]]; then
  cat <<'EOF'
All immutable staging guards passed. Read-only evidence was captured.
No plugin installation or registry synchronization was performed.

Planned mutation sequence for a later explicit --execute run:
  1. install and activate the exact hash-bound plugin ZIP;
  2. validate bundled registry and inspect preflight status;
  3. synchronize once (expected: 5 created drafts);
  4. synchronize again (expected: 5 unchanged);
  5. capture record identities and statuses.
EOF
  exit 0
fi

assert_status_actions() {
  local file="$1"
  local expected_action="$2"
  python3 - "$file" "$expected_action" <<'PY'
import json
import sys

payload = json.load(open(sys.argv[1], encoding="utf-8"))
operations = payload.get("preview", {}).get("operations", [])
actions = [operation.get("action") for operation in operations]
if len(actions) != 5 or any(action != sys.argv[2] for action in actions):
    raise SystemExit(f"Unexpected registry plan: {actions!r}")
PY
}

assert_sync_counts() {
  local file="$1"
  local expected_created="$2"
  local expected_updated="$3"
  local expected_unchanged="$4"
  python3 - "$file" "$expected_created" "$expected_updated" "$expected_unchanged" <<'PY'
import json
import re
import sys

text = open(sys.argv[1], encoding="utf-8").read()
match = re.search(r"Registry synchronized:\s*(\{[^\n]+\})", text)
if match is None:
    raise SystemExit("Registry synchronization counts were not found")
observed = json.loads(match.group(1))
expected = {
    "created": int(sys.argv[2]),
    "updated": int(sys.argv[3]),
    "unchanged": int(sys.argv[4]),
}
if observed != expected:
    raise SystemExit(f"Unexpected synchronization counts: {observed!r}")
PY
}

wp plugin install "$plugin_zip" --force --activate --no-color >"$evidence_dir/plugin-install.log"
wp observer registry validate --no-color >"$evidence_dir/registry-validate.log"
wp observer registry status --no-color >"$evidence_dir/registry-status-before.json"
assert_status_actions "$evidence_dir/registry-status-before.json" create
wp observer registry sync --no-color >"$evidence_dir/registry-sync-first.log" 2>&1
assert_sync_counts "$evidence_dir/registry-sync-first.log" 5 0 0
wp observer registry status --no-color >"$evidence_dir/registry-status-after-first.json"
assert_status_actions "$evidence_dir/registry-status-after-first.json" noop
wp observer registry sync --no-color >"$evidence_dir/registry-sync-second.log" 2>&1
assert_sync_counts "$evidence_dir/registry-sync-second.log" 0 0 5
wp observer registry status --no-color >"$evidence_dir/registry-status-after-second.json"
assert_status_actions "$evidence_dir/registry-status-after-second.json" noop
wp post list \
  --post_type=research_output \
  --post_status=any \
  --fields=ID,post_name,post_status \
  --orderby=ID \
  --order=ASC \
  --format=json \
  >"$evidence_dir/research-records.json"

python3 -m json.tool "$evidence_dir/research-records.json" >/dev/null
echo "P1.7 guarded staging installation and double synchronization completed."
