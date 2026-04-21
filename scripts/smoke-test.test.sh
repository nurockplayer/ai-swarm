#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

mkdir -p "$TMP_DIR/bin"

cat >"$TMP_DIR/bin/gh" <<'GH'
#!/usr/bin/env bash
set -euo pipefail

printf '%s\n' "$*" >>"$GH_CALLS"

case "$1 $2" in
  "auth status")
    exit 0
    ;;
  "issue create")
    printf 'https://github.com/example/repo/issues/123\n'
    ;;
  "pr list")
    if [[ "$*" == *".[0].number"* ]]; then
      printf '42\n'
    else
      printf 'https://github.com/example/repo/pull/42\n'
    fi
    ;;
  "pr view")
    case "$*" in
      *".state"*) printf 'MERGED\n' ;;
      *".mergedAt"*) printf '2026-04-22T00:01:00Z\n' ;;
      *) printf 'https://github.com/example/repo/pull/42\n' ;;
    esac
    ;;
  *)
    exit 1
    ;;
esac
GH
chmod +x "$TMP_DIR/bin/gh"

export PATH="$TMP_DIR/bin:$PATH"
export GH_CALLS="$TMP_DIR/gh-calls.log"
export SMOKE_TEST_PR_TIMEOUT_SECONDS=3
export SMOKE_TEST_MERGE_TIMEOUT_SECONDS=3
export SMOKE_TEST_POLL_INTERVAL_SECONDS=1

output="$("$ROOT_DIR/scripts/smoke-test.sh" --e2e example/repo)"

grep -q "E2E smoke test summary" <<<"$output"
grep -q "issue_number=123" <<<"$output"
grep -q "pr_number=42" <<<"$output"
grep -q "result=PASS" <<<"$output"
grep -q "issue create --repo example/repo" "$GH_CALLS"
grep -q "pr list --repo example/repo" "$GH_CALLS"
grep -q "pr view 42 --repo example/repo" "$GH_CALLS"

echo "smoke-test e2e harness passed"
