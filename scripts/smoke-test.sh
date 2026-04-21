#!/usr/bin/env bash
set -euo pipefail

readonly PR_TIMEOUT_SECONDS="${SMOKE_TEST_PR_TIMEOUT_SECONDS:-300}"
readonly MERGE_TIMEOUT_SECONDS="${SMOKE_TEST_MERGE_TIMEOUT_SECONDS:-300}"
readonly POLL_INTERVAL_SECONDS="${SMOKE_TEST_POLL_INTERVAL_SECONDS:-10}"

PASS=0
FAIL=0

usage() {
  cat <<'USAGE'
Usage:
  scripts/smoke-test.sh
  scripts/smoke-test.sh --e2e <owner/repo>

Without flags, runs the local pre-flight checks.
With --e2e, creates an ai-task issue, waits for a PR, then waits for merge.
USAGE
}

timestamp() {
  date -u +"%Y-%m-%dT%H:%M:%SZ"
}

elapsed_seconds() {
  local start="$1"
  echo "$((SECONDS - start))"
}

checkpoint() {
  local name="$1"
  local detail="${2:-}"

  if [[ -n "$detail" ]]; then
    printf '[%s] %s: %s\n' "$(timestamp)" "$name" "$detail"
  else
    printf '[%s] %s\n' "$(timestamp)" "$name"
  fi
}

check() {
  local name="$1"
  shift

  if "$@" &>/dev/null; then
    echo "  PASS $name"
    PASS=$((PASS + 1))
  else
    echo "  FAIL $name"
    FAIL=$((FAIL + 1))
  fi
}

check_env() {
  local name="$1"
  local value="${!name:-}"

  if [[ -n "$value" ]]; then
    echo "  PASS $name"
    PASS=$((PASS + 1))
  else
    echo "  FAIL $name"
    FAIL=$((FAIL + 1))
  fi
}

run_preflight() {
  echo "=== AI Swarm E2E Smoke Test Pre-flight ==="

  echo ""
  echo "--- Required tools ---"
  check "python3 >= 3.11" python3 -c 'import sys; assert sys.version_info >= (3,11)'
  check "uv" uv --version
  check "git" git --version
  check "gh CLI" gh --version
  check "claude CLI" claude --version

  echo ""
  echo "--- Environment variables ---"
  check_env "AI_SWARM_MQTT_BROKER_URL"
  check_env "AI_SWARM_MQTT_USERNAME"
  check_env "AI_SWARM_MQTT_PASSWORD"
  check "GITHUB_TOKEN (gh auth)" gh auth status

  echo ""
  echo "--- Worker setup ---"
  check "worker installed (uv sync)" test -f worker/pyproject.toml
  check "pydantic-settings available" uv --project worker run python -c 'import pydantic_settings'

  echo ""
  echo "--- Results ---"
  echo "  Passed: $PASS"
  echo "  Failed: $FAIL"

  if [[ "$FAIL" -gt 0 ]]; then
    echo ""
    echo "Fix the above failures before running the E2E test."
    exit 1
  fi

  echo ""
  echo "Pre-flight passed. Run 'worker start' and create a test issue to begin."
}

require_e2e_tools() {
  command -v gh >/dev/null
  gh auth status >/dev/null
}

create_e2e_issue() {
  local repo="$1"
  local title="[test] ai-task smoke test: add hello world function"
  local body

  body=$(cat <<'BODY'
Add a Python function hello_world() that returns "Hello, World!". Add a test for it.

This issue was created by scripts/smoke-test.sh --e2e.
BODY
)

  gh issue create \
    --repo "$repo" \
    --title "$title" \
    --body "$body" \
    --label ai-task \
    --label auto-merge
}

issue_number_from_url() {
  local issue_url="$1"
  local number="${issue_url##*/}"

  if [[ "$number" =~ ^[0-9]+$ ]]; then
    echo "$number"
  else
    return 1
  fi
}

pr_search_query() {
  local issue_number="$1"
  printf '"Closes #%s" in:body' "$issue_number"
}

find_pr_number_for_issue() {
  local repo="$1"
  local issue_number="$2"
  local query

  query="$(pr_search_query "$issue_number")"
  gh pr list \
    --repo "$repo" \
    --state all \
    --search "$query" \
    --json number \
    --jq '.[0].number // empty'
}

pr_url() {
  local repo="$1"
  local pr_number="$2"

  gh pr view "$pr_number" \
    --repo "$repo" \
    --json url \
    --jq '.url'
}

pr_state() {
  local repo="$1"
  local pr_number="$2"

  gh pr view "$pr_number" \
    --repo "$repo" \
    --json state \
    --jq '.state'
}

pr_merged_at() {
  local repo="$1"
  local pr_number="$2"

  gh pr view "$pr_number" \
    --repo "$repo" \
    --json mergedAt \
    --jq '.mergedAt // empty'
}

wait_for_pr() {
  local repo="$1"
  local issue_number="$2"
  local deadline=$((SECONDS + PR_TIMEOUT_SECONDS))
  local pr_number=""

  while [[ "$SECONDS" -le "$deadline" ]]; do
    pr_number="$(find_pr_number_for_issue "$repo" "$issue_number")"
    if [[ -n "$pr_number" ]]; then
      echo "$pr_number"
      return 0
    fi
    sleep "$POLL_INTERVAL_SECONDS"
  done

  return 1
}

wait_for_merge() {
  local repo="$1"
  local pr_number="$2"
  local deadline=$((SECONDS + MERGE_TIMEOUT_SECONDS))
  local state=""

  while [[ "$SECONDS" -le "$deadline" ]]; do
    state="$(pr_state "$repo" "$pr_number")"
    if [[ "$state" == "MERGED" ]]; then
      return 0
    fi
    sleep "$POLL_INTERVAL_SECONDS"
  done

  return 1
}

validate_repo_arg() {
  local repo="$1"

  if [[ ! "$repo" =~ ^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$ ]]; then
    echo "Invalid repo '$repo'. Expected owner/repo." >&2
    exit 2
  fi
}

run_e2e() {
  local repo="$1"
  local start="$SECONDS"
  local issue_url
  local issue_number
  local pr_number
  local url
  local merged_at

  validate_repo_arg "$repo"

  echo "=== AI Swarm E2E Smoke Test ==="
  checkpoint "start" "repo=$repo"

  if command -v mosquitto_sub >/dev/null; then
    checkpoint "mqtt-observer" "mosquitto_sub available; use broker logs for MQTT-level confirmation"
  else
    checkpoint "mqtt-observer" "mosquitto_sub not found; using gh pr list polling fallback"
  fi

  require_e2e_tools
  checkpoint "preflight" "gh auth ok"

  issue_url="$(create_e2e_issue "$repo")"
  issue_number="$(issue_number_from_url "$issue_url")"
  checkpoint "issue-created" "issue_number=$issue_number url=$issue_url"

  checkpoint "waiting-for-pr" "timeout=${PR_TIMEOUT_SECONDS}s poll=${POLL_INTERVAL_SECONDS}s"
  if ! pr_number="$(wait_for_pr "$repo" "$issue_number")"; then
    checkpoint "waiting-for-pr" "timeout"
    print_summary "$repo" "$issue_number" "" "" "FAIL" "$(elapsed_seconds "$start")"
    exit 1
  fi

  url="$(pr_url "$repo" "$pr_number")"
  checkpoint "pr-created" "pr_number=$pr_number url=$url"

  checkpoint "waiting-for-merge" "timeout=${MERGE_TIMEOUT_SECONDS}s poll=${POLL_INTERVAL_SECONDS}s"
  if ! wait_for_merge "$repo" "$pr_number"; then
    checkpoint "waiting-for-merge" "timeout"
    print_summary "$repo" "$issue_number" "$pr_number" "$url" "FAIL" "$(elapsed_seconds "$start")"
    exit 1
  fi

  merged_at="$(pr_merged_at "$repo" "$pr_number")"
  checkpoint "pr-merged" "pr_number=$pr_number merged_at=$merged_at"
  print_summary "$repo" "$issue_number" "$pr_number" "$url" "PASS" "$(elapsed_seconds "$start")"
}

print_summary() {
  local repo="$1"
  local issue_number="$2"
  local pr_number="$3"
  local pr_url_value="$4"
  local result="$5"
  local elapsed="$6"

  echo ""
  echo "=== E2E smoke test summary ==="
  echo "repo=$repo"
  echo "issue_number=$issue_number"
  echo "pr_number=${pr_number:-n/a}"
  echo "pr_url=${pr_url_value:-n/a}"
  echo "elapsed_seconds=$elapsed"
  echo "success_target_seconds=300"
  echo "result=$result"
}

main() {
  case "${1:-}" in
    "")
      run_preflight
      ;;
    --e2e)
      if [[ $# -ne 2 ]]; then
        usage >&2
        exit 2
      fi
      run_e2e "$2"
      ;;
    -h|--help)
      usage
      ;;
    *)
      usage >&2
      exit 2
      ;;
  esac
}

main "$@"
