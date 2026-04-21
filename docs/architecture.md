# Architecture

## 系統元件總覽

```
┌─────────────────────┐
│   GitHub Issues     │  (source of truth)
│   + Labels          │
└──────────┬──────────┘
           │ webhook (issues.labeled / pull_request)
           v
┌──────────────────────┐       ┌────────────────────┐
│  Cloudflare Worker   │──────>│  MQTT Broker       │
│  (webhook bridge)    │       │  HiveMQ Cloud      │
│  GitHub → MQTT       │       │  (免費方案)        │
└──────────────────────┘       └─────────┬──────────┘
                                         │ MQTT 5.0
                              Tailscale Private Network
                                         │
          ┌──────────────────┬───────────┼──────────────┐
          v                  v           v              v
    ┌──────────┐       ┌──────────┐ ┌──────────┐ ┌──────────┐
    │ Worker A │       │ Worker B │ │ Worker C │ │ Worker D │
    │ laptop 1 │       │ laptop 2 │ │  laptop  │ │   VPS    │
    └──────────┘       └──────────┘ └──────────┘ └──────────┘
```

## 元件說明

### Webhook Bridge（`bridge/`）

- Cloudflare Worker（TypeScript）
- 接收 GitHub webhook：`issues.labeled`、`pull_request.opened`
- 驗證 webhook signature（`x-hub-signature-256`）
- 把 GitHub event 轉換成標準 Task format（見 task-format.md）
- Publish 到 HiveMQ Cloud MQTT broker
- 完全 config-driven（no hardcoded repo names）

### MQTT Broker

- HiveMQ Cloud 免費方案（MVP）
- 支援 MQTT 5.0（Shared Subscriptions 是關鍵特性）
- Worker 透過 TLS 連線；Tailscale 用於 worker 之間協調

### Worker Daemon（`worker/`）

- Python daemon（uv 管理，`worker start` CLI）
- 訂閱 `$share/impl-workers/tasks/impl/+`（Shared Subscription）
- Broker 自動負載平衡，只有一個 worker 收到每則訊息
- Worker 離線時訊息自動轉給下一個可用的 worker

**執行流程：**

```
1. 收到 MQTT 任務訊息
2. 驗證 task format
3. git clone / pull repo（git worktree 隔離）
4. checkout 新 feature branch
5. 呼叫 claude --prompt-file <task-prompt>
6. Claude Code 依指示呼叫 codex-plugin-cc 交給 Codex 實作
7. 完成後跑本地驗證
8. 依 label 決定推送策略（見 CLAUDE.md）
9. 發布結果到 MQTT tasks/{task_id}/result
```

**Idle 模式（config-driven）：**

| 模式 | 說明 |
|---|---|
| `manual`（MVP 預設）| `worker start` / `worker stop` CLI |
| `auto`（Phase 1）| 背景偵測 Claude Code process + IDE 活動 |
| `schedule`（Phase 1）| crontab 設定夜間自動加入 pool |

## Data Flow

### Implementation Task

```
GitHub Issue 打上 ai-task label
  → GitHub webhook → Cloudflare Worker
  → 轉換成 Task JSON → Publish 到 tasks/impl/{project}
  → Worker 收到（Shared Subscription 保證只有一個 worker）
  → Worker 執行（Claude Code + Codex）
  → 完成後推 branch / 開 PR
```

### Review Task

```
PR 開啟
  → GitHub webhook → Cloudflare Worker
  → Publish 到 tasks/review/{project}
  → Reviewer worker 收到
  → Gemini 初審 → Claude 驗證 → Codex 主審
  → gh pr review --request-changes / approve
```

## 安全考量

| 風險 | 緩解 |
|---|---|
| Prompt injection via issue body | MVP：只有 maintainer 能打 `ai-task` label |
| GitHub Token 外洩 | fine-grained PAT，限定 repo 範圍 |
| MQTT 未授權存取 | HiveMQ Cloud ACL + TLS；每個 worker 有獨立 credentials |
| Worker crash 中途 | MQTT QoS 1 + timeout；失敗後訊息回 queue |

## 未來規劃

| Phase | 內容 |
|---|---|
| Phase 1 | Auto-detect idle 模式、Schedule 模式、多專案支援 |
| Phase 2 | Review 任務 pipeline（Gemini + Codex 全流程） |
| Phase 3 | Observer UI、metrics、retry policy、DLQ |
| Phase 4 | 自架 Mosquitto broker、fine-grained ACL |
