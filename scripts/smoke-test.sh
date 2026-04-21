#!/usr/bin/env bash
set -euo pipefail

echo "=== AI Swarm E2E Smoke Test Pre-flight ==="

PASS=0
FAIL=0

check() {
  local name="$1"
  local cmd="$2"
  if eval "$cmd" &>/dev/null; then
    echo "  ✓ $name"
    PASS=$((PASS + 1))
  else
    echo "  ✗ $name"
    FAIL=$((FAIL + 1))
  fi
}

echo ""
echo "--- Required tools ---"
check "python3 >= 3.11"  "python3 -c 'import sys; assert sys.version_info >= (3,11)'"
check "uv"               "uv --version"
check "git"              "git --version"
check "gh CLI"           "gh --version"
check "claude CLI"       "claude --version"

echo ""
echo "--- Environment variables ---"
check "AI_SWARM_MQTT_BROKER_URL"  "test -n \"${AI_SWARM_MQTT_BROKER_URL:-}\""
check "AI_SWARM_MQTT_USERNAME"    "test -n \"${AI_SWARM_MQTT_USERNAME:-}\""
check "AI_SWARM_MQTT_PASSWORD"    "test -n \"${AI_SWARM_MQTT_PASSWORD:-}\""
check "GITHUB_TOKEN (gh auth)"    "gh auth status"

echo ""
echo "--- Worker setup ---"
check "worker installed (uv sync)"  "test -f worker/pyproject.toml"
check "pydantic-settings available" "uv --project worker run python -c 'import pydantic_settings'"

echo ""
echo "--- Results ---"
echo "  Passed: $PASS"
echo "  Failed: $FAIL"

if [ "$FAIL" -gt 0 ]; then
  echo ""
  echo "Fix the above failures before running the E2E test."
  exit 1
fi

echo ""
echo "Pre-flight passed. Run 'worker start' and create a test issue to begin."
