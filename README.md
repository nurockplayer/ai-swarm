# ai-swarm

ai-swarm 是一個完全獨立的 AI 開發基礎設施，與任何產品專案無關。任何 repo 都可以接上它：在 GitHub Issues 建任務、閒置的 Claude Code worker 自動領取執行、結果推回 GitHub 形成閉環。

## 這是什麼

- 在 GitHub Issues 建任務（打上指定 label）
- 閒置的 Claude Code worker 自動領取並執行
- 執行結果推回 GitHub（PR、review comment）
- 新 PR 自動觸發 review 任務，形成閉環

## 官方工作流程

本專案採用任務分層流程：

1. `Trivial`：Claude Code 可直接 patch
2. `Small / Medium`：Claude Code 寫 issue，Codex 實作開 PR，Claude Code review
3. `Test-Driven / Debug Loop`：優先交給 Codex 持續 debug / patch / 驗證
4. `Architecture / High Risk`：Claude Code 先做設計與拆解，再交給 Codex 實作

`/codex:rescue` 已廢棄，不再是官方流程。詳細規範見 [docs/codex-workflow.md](docs/codex-workflow.md)。

角色偏好：

- Claude Code：模糊度高、架構決策、需求拆解、final review
- Codex：確定性高、寫 code、debug、patch、測試循環

## 目前進度

| Task | 狀態 | 說明 |
|---|---|---|
| Task 1 — Repo scaffold | ✅ 完成 | 目錄結構、CI、GitHub repo 建立 |
| Task 2 — Task schema | ✅ 完成 | schema/task.schema.json + Python types |
| Task 3 — Cloudflare Worker bridge | ✅ 完成 | bridge/ TypeScript Worker 實作完成 |
| Task 4 — Worker daemon skeleton | ✅ 完成 | Python worker daemon with MQTT |
| Task 5 — Worker 任務執行 | ✅ 完成 | Claude Code CLI 呼叫、git worktree 隔離 |
| Task 6 — Label 路由邏輯 | ✅ 完成 | 依 label 決定 PR 推送策略 |
| Task 7 — E2E smoke test | ⏳ 待實作 | 一張 issue 走完整流程 |
| Task 8 — Deploy playbook | ⏳ 待實作 | HiveMQ / Tailscale / Cloudflare 設定文件 |

## 技術選擇

| 元件 | 技術 | 原因 |
|---|---|---|
| Worker daemon | Python (uv) | Anthropic SDK Python-first；paho-mqtt 成熟；迭代快 |
| Webhook bridge | Cloudflare Worker (TypeScript) | Serverless、免費、低維護 |
| MQTT broker | HiveMQ Cloud 免費方案 | 100 連線、10GB/月，MVP 夠用 |
| 網路 | Tailscale | Worker 在私網，不開 public port |
| Task 來源 | GitHub Issues + labels | 已在用，config-driven，可抽換 |
| Claude 呼叫方式 | claude --prompt-file CLI | MVP 最簡單，無額外 SDK 依賴 |
| MQTT 分派 | MQTT 5.0 Shared Subscriptions | Broker 自動負載平衡，worker 離線自動轉派 |

## Label 驅動的 PR 推送策略

| Label 組合 | Worker 完成後行為 |
|---|---|
| ai-task | 開 draft PR，等人工 review |
| ai-task + auto-merge | 開 PR 並打 auto-merge label，CI 綠燈即 merge |
| ai-task + human-review | 推 branch，通知人類，不自動開 PR |
| ai-review | PR review 任務（由 PR webhook 觸發） |

## MQTT Topic 設計

| Topic | 用途 |
|---|---|
| tasks/impl/{project} | 實作任務（$share/impl-workers/tasks/impl/+ shared） |
| tasks/review/{project} | 審查任務（$share/review-workers/tasks/review/+ shared） |
| workers/{worker_id}/heartbeat | Worker 心跳（每 30s） |
| workers/{worker_id}/status | 閒置/忙碌/離線 |
| tasks/{task_id}/progress | 任務進度回報 |
| tasks/{task_id}/result | 任務完成結果 |

## MVP 成功條件

在任意 repo 建一張 issue，打上 ai-task + auto-merge label，5 分鐘內：

1. Worker 自動領取
2. Claude Code 完成實作並 commit
3. PR 自動開啟並打上 auto-merge label
4. CI 綠燈後 auto-merge 生效

## 專案結構

```text
ai-swarm/
├── bridge/    # Cloudflare Worker webhook bridge (TypeScript)
├── worker/    # Worker daemon (Python, uv)
├── schema/    # Task JSON schema
├── docs/      # 架構、task format、execution plan
├── infra/     # 部署 playbook（HiveMQ / Cloudflare / Tailscale）
└── scripts/   # smoke test 等
```

## 文件索引

- [架構](docs/architecture.md)
- [Task 格式](docs/task-format.md)
- [執行計劃](docs/execution-plan.md)
- [部署 playbook](infra/)
