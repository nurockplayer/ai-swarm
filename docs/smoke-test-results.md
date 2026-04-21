# E2E Smoke Test Results

## Environment

| Item | Value |
|---|---|
| Date | YYYY-MM-DD |
| Worker version | 0.1.0 |
| Worker machine | (hostname) |
| HiveMQ broker | (URL) |
| Test repo | (owner/repo) |

## Pre-flight

Run `./scripts/smoke-test.sh` and paste results here.

## Test Issue

- URL: https://github.com/{owner}/{repo}/issues/{number}
- Title: `[test] ai-task smoke test: add hello world function`
- Labels: `ai-task`, `auto-merge`
- Created at: HH:MM:SS

## Verification Checklist

| Step | Expected | Actual | Time |
|---|---|---|---|
| GitHub webhook triggered | CF Worker receives POST | | |
| MQTT published | HiveMQ dashboard shows message | | |
| Worker picks up task | Worker log shows task_id | | |
| Claude CLI executes | Worker log shows claude output | | |
| PR opened | GitHub PR created | | |
| CI passes → auto-merge | PR merged | | |
| Total elapsed | < 5 minutes | | |

## Fault Tolerance Test

| Test | Expected | Result |
|---|---|---|
| Kill worker mid-execution | Message returns to queue | |
| Second worker picks up | Task completes on worker B | |

## Notes

<!-- Any deviations, errors, or observations -->

## Conclusion

[ ] PASS — All checks passed, MVP success criteria met
[ ] PARTIAL — Some checks passed with workarounds
[ ] FAIL — Critical issues found (describe below)
