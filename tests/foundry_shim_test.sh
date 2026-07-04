#!/usr/bin/env bash
# Tests for the .foundry/bin/foundry shim: self-host runs the local tree, a consumer
# resolves the pinned CLI from .foundry/config.toml, a missing pin fails loudly.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SHIM="$HERE/../src/foundry/templates/verbatim/.foundry/bin/foundry"
ROOT="$(mktemp -d)"
trap 'rm -rf "$ROOT"' EXIT

fail() { echo "FAIL: $1"; exit 1; }

# A stub bin dir where uv/uvx echo their argv instead of executing.
STUB="$ROOT/stub"; mkdir -p "$STUB"
printf '#!/usr/bin/env bash\necho "UV $*"\n' > "$STUB/uv";  chmod +x "$STUB/uv"
printf '#!/usr/bin/env bash\necho "UVX $*"\n' > "$STUB/uvx"; chmod +x "$STUB/uvx"

run_shim() { ( cd "$1" && PATH="$STUB:$PATH" bash "$SHIM" "${@:2}" ); }

mkrepo() { local d="$ROOT/$1"; mkdir -p "$d"; ( cd "$d" && git init -q ); echo "$d"; }

# --- consumer: resolves the pin from config, runs uvx ---
consumer="$(mkrepo consumer)"
mkdir -p "$consumer/.foundry"
cat > "$consumer/.foundry/config.toml" <<'EOF'
[foundry]
pin = "v9.9.9"
repo_url = "https://example.com/foundry"
EOF
out="$(run_shim "$consumer" gate)"
[[ "$out" == *'UVX --from git+https://example.com/foundry@v9.9.9 foundry gate'* ]] \
  || fail "consumer should run pinned uvx; got: $out"

# --- self-host: src/foundry/cli.py present -> local tree, never uvx ---
selfhost="$(mkrepo selfhost)"
mkdir -p "$selfhost/src/foundry"; : > "$selfhost/src/foundry/cli.py"
mkdir -p "$selfhost/.foundry"
cat > "$selfhost/.foundry/config.toml" <<'EOF'
[foundry]
pin = "v9.9.9"
repo_url = "https://example.com/foundry"
EOF
out="$(run_shim "$selfhost" gate)"
# (git resolves the toplevel through symlinks, so match on shape, not the exact path)
[[ "$out" == *"UV run --project "*" foundry gate"* ]] \
  || fail "self-host should run the local tree; got: $out"
[[ "$out" != *"UVX"* ]] || fail "self-host must never fetch a pinned tag; got: $out"

# --- consumer without a pin: fails, names the missing key ---
nopin="$(mkrepo nopin)"
mkdir -p "$nopin/.foundry"; printf '[foundry]\n' > "$nopin/.foundry/config.toml"
if run_shim "$nopin" gate >/dev/null 2>&1; then fail "missing pin should exit non-zero"; fi
err="$(run_shim "$nopin" gate 2>&1 || true)"
[[ "$err" == *"pin/repo_url missing"* ]] || fail "missing pin should name the key; got: $err"

# --- forwards arbitrary subcommands + args, not just gate ---
out="$(run_shim "$consumer" rubric spec)"
[[ "$out" == *'foundry rubric spec'* ]] || fail "shim should forward args verbatim; got: $out"

echo "foundry_shim_test: PASS"
