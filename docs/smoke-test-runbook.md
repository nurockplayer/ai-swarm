# E2E Smoke Test Runbook

這份 runbook 說明如何用 `scripts/smoke-test.sh --e2e <owner/repo>` 驗證 GitHub Issue 到 PR auto-merge 的完整閉環。

## 前置條件

- 已安裝 `bash`、`gh` CLI。
- `gh auth status` 可通過，且 token 對測試 repo 具備 issue、pull request、contents 與 auto-merge 所需權限。
- 測試 repo 已啟用 GitHub webhook，會把 `issues.labeled` 事件送到 Cloudflare Worker bridge。
- MQTT broker、Cloudflare Worker bridge、worker daemon 都已部署並啟動。
- worker daemon 已在可用狀態，例如另一個終端機正在跑 `worker start`。
- 測試 repo 已存在 `ai-task` 與 `auto-merge` labels。
- 測試 repo 的 branch protection、CI 與 auto-merge 設定允許符合條件的 PR 自動合併。
- 若要觀察 MQTT 層事件，可安裝 `mosquitto_sub` 並設定 MQTT 相關環境變數；沒有安裝時，腳本會改用 `gh pr list` 輪詢判斷 PR 是否出現。

## 執行指令

先跑本機 pre-flight：

```bash
./scripts/smoke-test.sh
```

執行完整 E2E：

```bash
./scripts/smoke-test.sh --e2e <owner/repo>
```

腳本不 hardcode repo 或 credentials；repo 必須由 `<owner/repo>` 參數傳入，GitHub 認證由 `gh` CLI 既有 auth 狀態提供。

## 檢查點與預期輸出

| 檢查點 | 說明 | 預期 |
|---|---|---|
| `start` | 記錄開始時間與 repo | 顯示 `repo=<owner/repo>` |
| `mqtt-observer` | 判斷是否有 `mosquitto_sub` | 有則提示可看 MQTT 層；無則提示使用 `gh pr list` fallback |
| `preflight` | 確認 `gh auth status` 可用 | 顯示 `gh auth ok` |
| `issue-created` | 建立測試 issue | 顯示 issue number 與 URL |
| `waiting-for-pr` | 等待 worker 開 PR | 最多 300 秒；輪詢間隔預設 10 秒 |
| `pr-created` | 找到與 issue 關聯的 PR | 顯示 PR number 與 URL |
| `waiting-for-merge` | 等待 PR merge | 最多再 300 秒 |
| `pr-merged` | PR 已 merge | 顯示 `merged_at` |
| `E2E smoke test summary` | 最終摘要 | `result=PASS` 且 `elapsed_seconds` 小於 300 |

成功時摘要範例：

```text
=== E2E smoke test summary ===
repo=owner/repo
issue_number=123
pr_number=456
pr_url=https://github.com/owner/repo/pull/456
elapsed_seconds=240
success_target_seconds=300
result=PASS
```

## 常見失敗排查

| 現象 | 可能原因 | 排查方式 |
|---|---|---|
| `gh auth status` 失敗 | 未登入或 token 權限不足 | 執行 `gh auth status`、重新登入或換成有 repo 權限的 token |
| issue 建立失敗 | repo 名稱錯、label 不存在、token 無 issue 權限 | 確認 `<owner/repo>`、labels 與 GitHub token scopes |
| 5 分鐘內沒有 PR | webhook 未觸發、Cloudflare Worker 未部署、MQTT 設定錯、worker daemon 未啟動 | 查 GitHub webhook delivery、Cloudflare logs、MQTT dashboard、worker log |
| PR 出現但沒有 merge | CI 失敗、branch protection 卡住、auto-merge 沒啟用、worker 沒成功執行 `gh pr merge --auto --squash` | 查 PR checks、PR timeline、worker log |
| 找不到 PR 但 GitHub UI 有 PR | PR body 沒有 `Closes #<issue>`，或 worker PR 格式被改 | 確認 worker 的 PR body 仍包含 issue reference |
| `mosquitto_sub` 不存在 | 本機未安裝 MQTT CLI | 可忽略；腳本會使用 `gh pr list` fallback |

## 成功標準

- 腳本建立一張帶有 `ai-task`、`auto-merge` label 的 issue。
- worker 在 5 分鐘內開出關聯 PR。
- PR 在同一次 E2E 流程內完成 merge。
- `E2E smoke test summary` 顯示 `result=PASS`。
- `elapsed_seconds < 300`。
