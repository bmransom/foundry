#!/usr/bin/env bash
# Headless update eval (Layer 2): take an already-bootstrapped scratch repo,
# prepare a v-next plugin copy with bumped template + seed versions, run
# /foundry:update headless, then grade by harness-owned invariants.
#
# Usage:
#   evals/harness/update-eval.sh [--keep] [--prepare-only] <bootstrapped-tree>
#
# --keep          retain scratch dirs (always retained on FAIL)
# --prepare-only  run steps 1–3 only (prepare vnext + customize), then exit 0;
#                 use for dry-run validation without a full headless run
#
# <bootstrapped-tree> must already have .foundry-manifest.json (i.e., been
# bootstrapped with /foundry:bootstrap or had legacy backfill applied).
#
# Results: evals/results/update-<epoch>.ndjson + matching .log
set -euo pipefail

HARNESS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FOUNDRY_REPO="$(cd "$HARNESS/../.." && pwd)"
RESULTS_DIR="$FOUNDRY_REPO/evals/results"

KEEP=0
PREPARE_ONLY=0
results=""

usage() { sed -n '2,16p' "${BASH_SOURCE[0]}"; exit 2; }

emit() { # fixture case_name verdict detail — append one NDJSON record
  local fixture="$1" case_name="$2" verdict="$3" detail="$4"
  printf '{"event":"eval_case","fixture":"%s","case":"%s","verdict":"%s","detail":"%s"}\n' \
    "$fixture" "$case_name" "$verdict" "$detail" | tee -a "$results"
}

# ── version helpers ──────────────────────────────────────────────────────────

semver_patch_bump() { # "0.2.0" -> "0.2.1"
  python3 -c "
v = '${1}'.split('.')
v[2] = str(int(v[2]) + 1)
print('.'.join(v))
"
}

json_get() { # file key -> value (string)
  python3 -c "import json,sys; print(json.load(open(sys.argv[1]))[sys.argv[2]])" "$1" "$2"
}

json_get_nested() { # file key1 key2 -> value
  python3 -c "import json,sys; print(json.load(open(sys.argv[1]))[sys.argv[2]][sys.argv[3]])" \
    "$1" "$2" "$3"
}

marker_version() { # path "foundry-template:" -> integer
  # Extracts the vN integer from "# foundry-template: name vN"
  grep -oE 'v[0-9]+' <(grep -m1 'foundry-template:' "$1") | grep -oE '[0-9]+'
}

seed_version() { # path "foundry-seed:" -> integer
  # Extracts the vN integer from "<!-- foundry-seed: name vN -->"
  grep -oE 'v[0-9]+' <(grep -m1 'foundry-seed:' "$1") | grep -oE '[0-9]+'
}

manifest_template_version() { # manifest_path relative_path -> integer
  python3 -c "
import json, sys
m = json.load(open(sys.argv[1]))
print(m['files'][sys.argv[2]]['version'])
" "$1" "$2"
}

max_plus1() { # int int -> int
  python3 -c "print(max($1, $2) + 1)"
}

sha256_file() { # path -> hex
  shasum -a 256 "$1" | awk '{print $1}'
}

# ── main ─────────────────────────────────────────────────────────────────────

while [ "$#" -gt 0 ]; do
  case "$1" in
    --keep)         KEEP=1; shift ;;
    --prepare-only) PREPARE_ONLY=1; shift ;;
    -h|--help)      usage ;;
    *)              break ;;
  esac
done

[ "$#" -eq 1 ] || usage
TREE="$(cd "$1" && pwd)"

manifest_path="$TREE/.foundry-manifest.json"
[ -f "$manifest_path" ] || {
  echo "update-eval: $manifest_path not found — tree must be bootstrapped (with manifest)" >&2
  exit 2
}

stamp="$(date +%s)"
mkdir -p "$RESULTS_DIR"
results="$RESULTS_DIR/update-$stamp.ndjson"
log="$RESULTS_DIR/update-$stamp.log"
SCRATCH="$(mktemp -d "${TMPDIR:-/tmp}/foundry-update-eval.XXXXXX")"
vnext="$SCRATCH/plugin-vnext"
eval_failed=0

echo "update-eval: tree=$TREE"
echo "update-eval: scratch=$SCRATCH"
echo "update-eval: log=$log"
echo "update-eval: results=$results"

cleanup() {
  if [ "$eval_failed" -eq 0 ] && [ "$KEEP" -eq 0 ]; then
    rm -rf "$SCRATCH"
  else
    echo "update-eval: scratch retained at $SCRATCH"
  fi
}
trap cleanup EXIT

# ── Step 1: Prepare v-next plugin copy ───────────────────────────────────────
echo "update-eval: step 1 — prepare v-next plugin copy"

cp -R "$FOUNDRY_REPO/plugins/foundry" "$vnext"

# ── Bump install-hooks.sh template version ───────────────────────────────────
hooks_tpl="$vnext/templates/verbatim/scripts/install-hooks.sh"

tpl_hooks_ver="$(marker_version "$hooks_tpl")"
mf_hooks_ver="$(manifest_template_version "$manifest_path" "scripts/install-hooks.sh")"
next_hooks_ver="$(max_plus1 "$tpl_hooks_ver" "$mf_hooks_ver")"

echo "update-eval: install-hooks template_ver=$tpl_hooks_ver manifest_ver=$mf_hooks_ver -> v$next_hooks_ver"

python3 - "$hooks_tpl" "$next_hooks_ver" <<'PYBUMP'
import re, sys
path, new_ver = sys.argv[1], sys.argv[2]
text = open(path).read()
text = re.sub(r'(foundry-template: install-hooks) v\d+', rf'\1 v{new_ver}', text)
open(path, 'w').write(text)
PYBUMP

echo "# eval: bumped install-hooks to v$next_hooks_ver" >> "$hooks_tpl"
echo "update-eval: appended marker comment to install-hooks.sh"

# ── Bump glossary seed version ────────────────────────────────────────────────
glossary_seed="$vnext/templates/seeds/docs/glossary.md"

seed_glossary_ver="$(seed_version "$glossary_seed")"
# Glossary seed version comes from the seed file itself (seeds not in manifest)
# Compare against the repo file's seed marker
repo_glossary="$TREE/docs/glossary.md"
if [ -f "$repo_glossary" ]; then
  repo_seed_ver="$(seed_version "$repo_glossary" 2>/dev/null || echo 0)"
else
  repo_seed_ver=0
fi
next_seed_ver="$(max_plus1 "$seed_glossary_ver" "$repo_seed_ver")"

echo "update-eval: glossary seed_ver=$seed_glossary_ver repo_ver=$repo_seed_ver -> v$next_seed_ver"

python3 - "$glossary_seed" "$next_seed_ver" <<'PYBUMP'
import re, sys
path, new_ver = sys.argv[1], sys.argv[2]
text = open(path).read()
text = re.sub(r'(foundry-seed: glossary) v\d+', rf'\1 v{new_ver}', text)
open(path, 'w').write(text)
PYBUMP

echo "" >> "$glossary_seed"
echo "<!-- eval: bumped glossary seed to v$next_seed_ver -->" >> "$glossary_seed"
echo "update-eval: appended line to glossary seed"

# ── Bump plugin.json version ──────────────────────────────────────────────────
plugin_json="$vnext/.claude-plugin/plugin.json"

mf_plugin_ver="$(json_get "$manifest_path" "pluginVersion")"
bumped_plugin_ver="$(semver_patch_bump "$mf_plugin_ver")"

echo "update-eval: plugin manifest_ver=$mf_plugin_ver -> $bumped_plugin_ver"

python3 - "$plugin_json" "$bumped_plugin_ver" <<'PYJSON'
import json, sys
path, new_ver = sys.argv[1], sys.argv[2]
data = json.load(open(path))
data['version'] = new_ver
json.dump(data, open(path, 'w'), indent=2)
open(path, 'a').write('\n')
PYJSON

echo "update-eval: v-next plugin at $vnext (plugin version $bumped_plugin_ver)"

if [ "$PREPARE_ONLY" -eq 1 ]; then
  echo ""
  echo "update-eval: --prepare-only: verifying markers"
  echo "install-hooks.sh marker:"
  grep 'foundry-template:' "$hooks_tpl"
  echo "glossary seed marker:"
  grep 'foundry-seed:' "$glossary_seed"
  echo "plugin.json version:"
  python3 -c "import json; print(json.load(open('$plugin_json'))['version'])"
  echo ""
  echo "update-eval: --prepare-only done"
  exit 0
fi

# ── Step 2: Customize board.sh in the tree ────────────────────────────────────
echo "update-eval: step 2 — add customization to board.sh"
echo "# eval: local customization line $(date +%s)" >> "$TREE/scripts/board.sh"

# ── Step 3: Snapshot pre-state ────────────────────────────────────────────────
echo "update-eval: step 3 — snapshot pre-state"
snap_board="$(sha256_file "$TREE/scripts/board.sh")"
snap_hooks="$(sha256_file "$TREE/scripts/install-hooks.sh")"
snap_glossary="$(sha256_file "$TREE/docs/glossary.md")"

echo "update-eval: snap board=$snap_board"
echo "update-eval: snap install-hooks=$snap_hooks"
echo "update-eval: snap glossary=$snap_glossary"

# ── Step 4: Run update headless ───────────────────────────────────────────────
echo "update-eval: step 4 — running headless update (this takes minutes)"

prompt="Use the foundry update skill, follow it exactly. Canned go-ahead: yes, commit."

if (cd "$TREE" && claude -p "$prompt" \
    --plugin-dir "$vnext" \
    --dangerously-skip-permissions \
    --verbose --output-format stream-json) >"$log" 2>&1; then
  emit "update" "update:claude" "pass" "headless update completed"
else
  emit "update" "update:claude" "fail" "claude -p exited nonzero - see the log"
  eval_failed=1
fi

# ── Step 5: Grade ─────────────────────────────────────────────────────────────
echo "update-eval: step 5 — grading"

# ── 5a: install-hooks.sh refreshed ───────────────────────────────────────────
post_hooks="$(sha256_file "$TREE/scripts/install-hooks.sh")"
expected_hooks="$(sha256_file "$vnext/templates/verbatim/scripts/install-hooks.sh")"

if [ "$post_hooks" = "$expected_hooks" ]; then
  emit "update" "refresh:install-hooks:content" "pass" \
    "scripts/install-hooks.sh byte-identical to v-next template"
else
  emit "update" "refresh:install-hooks:content" "fail" \
    "scripts/install-hooks.sh sha256=$post_hooks expected=$expected_hooks"
  eval_failed=1
fi

post_hooks_mf_ver="$(manifest_template_version "$manifest_path" "scripts/install-hooks.sh")"
post_hooks_mf_sha="$(python3 -c "
import json; m=json.load(open('$manifest_path'))
print(m['files']['scripts/install-hooks.sh']['sha256'])
")"

if [ "$post_hooks_mf_ver" -eq "$next_hooks_ver" ]; then
  emit "update" "refresh:install-hooks:manifest-version" "pass" \
    "manifest install-hooks version=$post_hooks_mf_ver (expected $next_hooks_ver)"
else
  emit "update" "refresh:install-hooks:manifest-version" "fail" \
    "manifest install-hooks version=$post_hooks_mf_ver (expected $next_hooks_ver)"
  eval_failed=1
fi

if [ "$post_hooks_mf_sha" = "$post_hooks" ]; then
  emit "update" "refresh:install-hooks:manifest-hash" "pass" \
    "manifest install-hooks sha256 matches refreshed file"
else
  emit "update" "refresh:install-hooks:manifest-hash" "fail" \
    "manifest install-hooks sha256=$post_hooks_mf_sha file sha256=$post_hooks"
  eval_failed=1
fi

# ── 5b: board.sh protected (customization survived) ──────────────────────────
post_board="$(sha256_file "$TREE/scripts/board.sh")"

if [ "$post_board" = "$snap_board" ]; then
  emit "update" "protect:board.sh:content" "pass" \
    "scripts/board.sh sha256 unchanged from snapshot (customization survived)"
else
  emit "update" "protect:board.sh:content" "fail" \
    "scripts/board.sh sha256 changed: snapshot=$snap_board post=$post_board"
  eval_failed=1
fi

# board.sh manifest entry must NOT have been updated (hash should still differ)
post_board_mf_sha="$(python3 -c "
import json; m=json.load(open('$manifest_path'))
print(m['files']['scripts/board.sh']['sha256'])
" 2>/dev/null || echo "absent")"

if [ "$post_board_mf_sha" != "$post_board" ]; then
  emit "update" "protect:board.sh:manifest-not-updated" "pass" \
    "manifest board.sh sha256 not updated for customized file (sha256 still differs)"
else
  emit "update" "protect:board.sh:manifest-not-updated" "fail" \
    "manifest board.sh was updated despite customization — update overwrote a customized file"
  eval_failed=1
fi

# ── 5c: docs/glossary.md untouched ───────────────────────────────────────────
post_glossary="$(sha256_file "$TREE/docs/glossary.md")"

if [ "$post_glossary" = "$snap_glossary" ]; then
  emit "update" "seed-protect:glossary:content" "pass" \
    "docs/glossary.md sha256 unchanged from snapshot (seed never written)"
else
  emit "update" "seed-protect:glossary:content" "fail" \
    "docs/glossary.md sha256 changed: snapshot=$snap_glossary post=$post_glossary"
  eval_failed=1
fi

# ── 5d: manifest pluginVersion == bumped version ─────────────────────────────
post_plugin_ver="$(json_get "$manifest_path" "pluginVersion")"

if [ "$post_plugin_ver" = "$bumped_plugin_ver" ]; then
  emit "update" "manifest:pluginVersion" "pass" \
    "manifest pluginVersion=$post_plugin_ver (expected $bumped_plugin_ver)"
else
  emit "update" "manifest:pluginVersion" "fail" \
    "manifest pluginVersion=$post_plugin_ver (expected $bumped_plugin_ver)"
  eval_failed=1
fi

# ── 5e: gate green after refresh ─────────────────────────────────────────────
gate="scripts/check-fast.sh"
if (cd "$TREE" && bash "$gate") >>"$log" 2>&1; then
  emit "update" "gate:clean" "pass" "$gate exited 0 after update"
else
  emit "update" "gate:clean" "fail" "$gate exited nonzero after update - see the log"
  eval_failed=1
fi

# ── 5f: update committed; board.sh NOT in the commit ─────────────────────────
new_commit="$(git -C "$TREE" log --oneline -1 2>/dev/null || echo "")"
if echo "$new_commit" | grep -qi 'update\|refresh\|foundry'; then
  emit "update" "commit:present" "pass" \
    "update commit present: $new_commit"
else
  emit "update" "commit:present" "fail" \
    "no update-style commit found in git log; last commit: $new_commit"
  eval_failed=1
fi

if git -C "$TREE" diff HEAD~1 HEAD --name-only 2>/dev/null | grep -qx 'scripts/board.sh'; then
  emit "update" "commit:board-excluded" "fail" \
    "scripts/board.sh appears in the update commit — customized file must not be committed"
  eval_failed=1
else
  emit "update" "commit:board-excluded" "pass" \
    "scripts/board.sh absent from the update commit"
fi

# ── Summary ───────────────────────────────────────────────────────────────────
if [ "$eval_failed" -eq 0 ]; then
  echo "update-eval: PASS"
else
  echo "update-eval: FAIL"
  eval_failed=1  # ensure trap uses nonzero for cleanup decision
fi

exit "$eval_failed"
