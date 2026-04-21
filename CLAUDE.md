# ai-swarm — Claude Code Guidelines

## 專案說明

`ai-swarm` 是一個**完全獨立的 AI 開發基礎設施**，與任何產品專案（tachigo、tachiya 等）無關。

任何專案都可以接上它：

- 在 GitHub Issues 建任務（打上指定 label）
- 閒置的 Claude Code worker 自動領取並執行
- 執行結果推回 GitHub（PR、review comment）
- 新 PR 自動觸發 review 任務，形成閉環

## 語言設定

永遠使用台灣正體中文回覆。

## 實作分工

**執行模式**：Codex 主力實作，Claude Code 擔任規劃與監工。

| 角色 | 職責 |
|---|---|
| **Claude Code** | 拆任務、寫 sub-spec、審查 Codex 產出、整合決策 |
| **Codex** | 具體實作（寫程式、跑測試、commit、push） |

Claude Code 不直接寫程式碼，除非 Codex 明確無法處理。

## 目前進度

| Task | 狀態 | 說明 |
|---|---|---|
| Task 1 — Repo scaffold | ✅ 完成 | 目錄結構、CI、GitHub repo 建立 |
| Task 2 — Task schema | ✅ 完成 | `schema/task.schema.json` + Go types `worker/task.go` |
| Task 3 — Cloudflare Worker bridge | ⏳ 待實作 | GitHub webhook → MQTT publish |
| Task 4 — Worker daemon skeleton | ⏳ 待實作 | MQTT 連線、shared subscription、heartbeat |
| Task 5 — Worker 任務執行 | ⏳ 待實作 | Claude Code CLI 呼叫、git worktree 隔離 |
| Task 6 — Label 路由邏輯 | ⏳ 待實作 | 依 label 決定 PR 推送策略 |
| Task 7 — E2E smoke test | ⏳ 待實作 | 一張 issue 走完整流程 |
| Task 8 — Deploy playbook | ⏳ 待實作 | HiveMQ / Tailscale / Cloudflare 設定文件 |

## 技術選擇

| 元件 | 技術 | 原因 |
|---|---|---|
| Worker daemon | Go | 單 binary、paho.mqtt.golang 成熟 |
| Webhook bridge | Cloudflare Worker (TypeScript) | Serverless、免費、低維護 |
| MQTT broker | HiveMQ Cloud 免費方案 | 100 連線、10GB/月，MVP 夠用 |
| 網路 | Tailscale | Worker 在私網，不開 public port |
| Task 來源 | GitHub Issues + labels | 已在用，config-driven，可抽換 |
| Claude 呼叫方式 | `claude --prompt-file` CLI | MVP 最簡單，無額外 SDK 依賴 |
| MQTT 分派 | MQTT 5.0 Shared Subscriptions | Broker 自動負載平衡，worker 離線自動轉派 |

## Label 驅動的 PR 推送策略

| Label 組合 | Worker 完成後行為 |
|---|---|
| `ai-task` | 開 draft PR，等人工 review |
| `ai-task` + `auto-merge` | 開 PR 並打 auto-merge label，CI 綠燈即 merge |
| `ai-task` + `human-review` | 推 branch，通知人類，不自動開 PR |
| `ai-review` | PR review 任務（由 PR webhook 觸發） |

## MQTT Topic 設計

| Topic | 用途 |
|---|---|
| `tasks/impl/{project}` | 實作任務（`$share/impl-workers/tasks/impl/+` shared） |
| `tasks/review/{project}` | 審查任務（`$share/review-workers/tasks/review/+` shared） |
| `workers/{worker_id}/heartbeat` | Worker 心跳（每 30s） |
| `workers/{worker_id}/status` | 閒置/忙碌/離線 |
| `tasks/{task_id}/progress` | 任務進度回報 |
| `tasks/{task_id}/result` | 任務完成結果 |

## MVP 成功條件

在任意 repo 建一張 issue，打上 `ai-task` + `auto-merge` label，5 分鐘內：

1. Worker 自動領取
2. Codex 完成實作並 commit
3. PR 自動開啟並打上 `auto-merge` label
4. CI 綠燈後 auto-merge 生效

## 重要限制

- **完全 project-agnostic**：repo、project、label 全部從 config 讀取，不 hardcode
- **MVP 只做 manual toggle idle 模式**（`worker start` / `worker stop`）
- **MVP 單 worker 單任務**（git worktree 隔離）
- **No real credentials**：secret 用環境變數，不進 repo

## 架構圖

見 [docs/architecture.md](docs/architecture.md)

## Task 格式

見 [docs/task-format.md](docs/task-format.md)，schema 定義在 [schema/task.schema.json](schema/task.schema.json)
