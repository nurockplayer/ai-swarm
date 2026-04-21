# AI Swarm — MVP 執行計畫

## 現況（2026-04-21）

| Task | 狀態 | PR / Branch |
|---|---|---|
| Task 1 — Repo scaffold | ✅ merged (main) | — |
| Task 2 — Task schema (Python) | 🔁 review | PR #2 `refactor/task-2-python-migration` |
| Task 3 — Cloudflare Worker bridge | 🔁 review | PR #3 `feat/task-3-bridge` |
| Task 4 — Worker daemon skeleton | ⏳ 待實作 | — |
| Task 5 — Worker 任務執行 | ⏳ 待實作 | — |
| Task 6 — Label 路由邏輯 | ⏳ 待實作 | — |
| Task 7 — E2E smoke test | ⏳ 待實作 | — |
| Task 8 — Deploy playbook | ⏳ 待實作 | — |

PR #2、#3 merge 後，Task 4 才能開始（依賴 Python stack 確定）。

---

## Task 4 — Worker Daemon Skeleton

**Branch:** `feat/task-4-worker-daemon`
**依賴:** PR #2 merged（Python stack）

### 目標

建立可運作的 Python worker daemon，能連上 HiveMQ Cloud、訂閱 MQTT shared topic、發送 heartbeat，並支援 `worker start` / `worker stop` CLI。

### 技術規格

#### Config（`worker/src/ai_swarm_worker/config.py`）

用 pydantic-settings 從環境變數讀取：

```python
class WorkerConfig(BaseSettings):
    worker_id: str              # 唯一 ID，預設 "{hostname}-{pid}"
    mqtt_broker_url: str        # e.g. "mqtts://abc123.hivemq.cloud:8883"
    mqtt_username: str
    mqtt_password: str
    mqtt_keepalive: int = 60
    heartbeat_interval: int = 30   # seconds
    log_level: str = "INFO"
```

config file 路徑（可選）：`~/.ai-swarm/config.toml`，環境變數優先。

#### MQTT Client（`worker/src/ai_swarm_worker/mqtt.py`）

- 使用 `paho-mqtt` v2（callback API v2）
- TLS：`ssl.PROTOCOL_TLS_CLIENT`，verify HiveMQ 憑證
- MQTT 5.0：`MQTTv5`
- Shared subscription：`$share/impl-workers/tasks/impl/+`
- QoS 1 for task messages、heartbeat

```
連線流程：
1. client.connect_async(host, port, keepalive)
2. on_connect callback → subscribe shared topic
3. 開始 client.loop_start()（背景執行緒）
```

#### Heartbeat（`worker/src/ai_swarm_worker/heartbeat.py`）

每 30s publish 一次到 `workers/{worker_id}/heartbeat`：

```json
{
  "worker_id": "laptop-a-12345",
  "status": "idle",
  "timestamp": "2026-04-21T10:00:00Z",
  "version": "0.1.0"
}
```

同時 publish 到 `workers/{worker_id}/status`（retained message）：`"idle"` / `"busy"` / `"offline"`。

LWT（Last Will and Testament）設為 `workers/{worker_id}/status` = `"offline"`，這樣 worker 斷線時 broker 自動廣播。

#### CLI（`worker/src/ai_swarm_worker/main.py`）

```
worker start [--config PATH]   # 啟動 daemon，前景執行，Ctrl-C 優雅關閉
worker stop                    # 送 SIGTERM 給背景 daemon（若以背景模式啟動）
worker status                  # 顯示目前連線狀態
```

MVP 只需要 `worker start` 前景模式（Ctrl-C 關閉）。`stop` 可以是 stub。

#### Graceful Shutdown

捕捉 `SIGTERM` 和 `SIGINT`：
1. publish `workers/{worker_id}/status` = `"offline"`
2. client.disconnect()
3. 等 loop_stop()
4. exit(0)

#### Logging

用 Python stdlib `logging`，JSON 格式輸出到 stdout：

```json
{"ts": "2026-04-21T10:00:00Z", "level": "INFO", "msg": "connected to broker", "broker": "abc123.hivemq.cloud"}
```

### 驗收標準

- [ ] `worker start` 成功連上 HiveMQ Cloud（需真實 credentials 在環境變數）
- [ ] HiveMQ dashboard 可看到 client 上線
- [ ] 每 30s 出現 heartbeat（dashboard 可驗證）
- [ ] LWT 設定正確：kill process 後 30-60s 內 `workers/{worker_id}/status` 變成 `"offline"`
- [ ] `pyright` + `ruff` + `pytest` 全過（包含 mock MQTT 的單元測試）
- [ ] 收到 MQTT 任務訊息時 log 出來（尚不執行）

### 新增依賴

```toml
dependencies = [
    "pydantic>=2.10",
    "pydantic-settings>=2.7",
    "paho-mqtt>=2.1",
    "click>=8.1",
]
```

---

## Task 5 — Worker 任務執行

**Branch:** `feat/task-5-task-execution`
**依賴:** Task 4 merged

### 目標

Worker 收到 MQTT 任務後，完整執行：clone repo → checkout branch → 呼叫 Claude Code CLI → 等待完成 → timeout 處理 → publish 結果。

### 技術規格

#### 任務執行流程（`worker/src/ai_swarm_worker/executor.py`）

```
1. 解析 Task JSON（pydantic Task model）
2. 設 worker status → "busy"
3. git clone {repo} 到 /tmp/ai-swarm/{task_id}/ 或用 git worktree
4. git checkout -b ai/{task_id}
5. 把 task.prompt 寫入 /tmp/ai-swarm/{task_id}/task-prompt.md
6. 呼叫 claude CLI：
   claude --print --prompt-file task-prompt.md --dangerously-skip-permissions
7. 串流 stdout/stderr，每 10s publish 進度到 tasks/{task_id}/progress
8. 等待完成（timeout = task.timeout_seconds）
9. 完成後：publish tasks/{task_id}/result
10. 設 worker status → "idle"
```

#### Git 隔離

用 git worktree 優先於 clone（速度快、共享 git history）：

```bash
# 主目錄 cache：~/.ai-swarm/repos/{owner}-{repo}/
git worktree add /tmp/ai-swarm/{task_id} -b ai/{task_id}
# 完成後清理
git worktree remove /tmp/ai-swarm/{task_id}
```

若 repo 尚未 clone，先 `git clone --depth 1`。

#### Claude Code CLI 呼叫

```python
import subprocess

proc = subprocess.Popen(
    ["claude", "--print", "--prompt-file", str(prompt_path), "--dangerously-skip-permissions"],
    cwd=str(worktree_path),
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
)
```

**重要限制：**
- `--dangerously-skip-permissions` 只在非互動模式下使用，是 headless 執行必要旗標
- timeout 用 `asyncio.wait_for` 或 `proc.wait(timeout=...)`
- 超時時 `proc.kill()`，publish failure result

#### 任務進度（Progress Payload）

```json
{
  "task_id": "...",
  "worker_id": "...",
  "status": "running",
  "elapsed_seconds": 45,
  "last_output_line": "Running tests...",
  "timestamp": "..."
}
```

#### 任務結果（Result Payload）

```json
{
  "task_id": "...",
  "worker_id": "...",
  "status": "success" | "failure" | "timeout",
  "exit_code": 0,
  "branch": "ai/task-id-here",
  "elapsed_seconds": 120,
  "timestamp": "..."
}
```

#### 錯誤處理

| 情況 | 行為 |
|---|---|
| claude CLI 不存在 | publish failure，log error，status → idle |
| git clone 失敗 | publish failure，清理 worktree，status → idle |
| 超時 | kill process，publish timeout result |
| 執行中 worker crash | MQTT QoS 1 保證訊息保留，下一個 worker 重新領取 |

### 驗收標準

- [ ] 收到合法 Task JSON → 開始執行 → 能在 HiveMQ dashboard 看到 progress
- [ ] claude CLI 不存在時優雅失敗（不 crash daemon）
- [ ] timeout 正確觸發（測試用 60s task + 10s timeout）
- [ ] worktree 在成功/失敗後都被清理
- [ ] 單元測試：mock subprocess + mock MQTT

---

## Task 6 — Label 路由邏輯

**Branch:** `feat/task-6-label-routing`
**依賴:** Task 5 merged

### 目標

依據 task.labels 決定執行完成後的 PR 推送策略。

### 路由規則（`worker/src/ai_swarm_worker/github.py`）

```python
def route_pr(task: Task, branch: str, result: TaskResult) -> None:
```

| 條件 | 行為 |
|---|---|
| `ai-task` 在 labels | `gh pr create --draft --title "ai: {task_id}" --body "..."` |
| `ai-task` + `auto-merge` | PR + `gh pr merge --auto --squash` |
| `ai-task` + `human-review` | `git push origin {branch}`，不開 PR，只 log |
| `ai-review` | `gh pr review {pr_number} --comment --body "..."` |

#### PR Body 格式

```markdown
## AI Task Result

- **Task ID:** {task_id}
- **Source:** {repo}#{issue_number}
- **Elapsed:** {elapsed}s

Closes #{issue_number}
```

#### GitHub CLI 封裝

用 `subprocess` 呼叫 `gh` CLI（比 PyGithub 輕量，不需額外 token 管理）：

```python
def run_gh(*args: str, cwd: Path) -> str:
    result = subprocess.run(
        ["gh", *args],
        cwd=cwd, capture_output=True, text=True, check=True,
    )
    return result.stdout.strip()
```

### 驗收標準

- [ ] `auto-merge` label → PR 開啟後自動觸發 auto-merge
- [ ] `human-review` label → 只推 branch，沒有 PR
- [ ] 單元測試：mock `gh` CLI，驗證呼叫參數

---

## Task 7 — E2E Smoke Test

**Branch:** `feat/task-7-e2e-smoke`
**依賴:** Tasks 4-6 merged，HiveMQ + Cloudflare 設定完成

### 目標

在真實環境走完一個完整循環，並記錄驗證結果。

### 測試流程

1. **準備環境**
   - HiveMQ Cloud 帳號建立（見 infra/hivemq-setup.md）
   - Cloudflare Worker deployed（見 infra/cloudflare-deploy.md）
   - GitHub webhook 設定 → Cloudflare Worker URL
   - Worker daemon 在本機啟動：`worker start`

2. **觸發測試**
   - 在任意 repo 建一張 issue：
     - Title: `[test] ai-task smoke test: add hello world function`
     - Body: `Add a Python function hello_world() that returns "Hello, World!". Add a test for it.`
     - Labels: `ai-task`, `auto-merge`

3. **驗證檢查點**

   | 步驟 | 預期 | 怎麼驗證 |
   |---|---|---|
   | GitHub webhook 觸發 | Cloudflare Worker 收到 | CF Worker log |
   | MQTT publish | HiveMQ dashboard 有訊息 | broker dashboard |
   | Worker 領取任務 | worker log 出現 task_id | stdout |
   | claude CLI 執行 | 看到 Claude Code 輸出 | worker log |
   | PR 開啟 | GitHub 上有新 PR | `gh pr list` |
   | CI 通過 → auto-merge | PR merged | GitHub UI |
   | 全程 < 5 分鐘 | 計時 | 人工計時 |

4. **結果記錄**
   - 把驗證結果寫入 `docs/smoke-test-results.md`
   - 記錄實際耗時、任何異常、版本資訊

### 驗收標準

- [ ] 上述所有檢查點全部通過
- [ ] `docs/smoke-test-results.md` 記錄測試結果
- [ ] 失敗路徑測試：kill worker 中途 → 訊息回到 queue（用第二個 worker 驗證）

---

## Task 8 — Deploy Playbook

**Branch:** `feat/task-8-deploy-playbook`
**依賴:** Task 7 passed（MVP 驗證後才補完整文件）

### 目標

讓任何人能在 30 分鐘內把整套基礎設施跑起來。

### 文件清單

#### `infra/hivemq-setup.md`

- 建立 HiveMQ Cloud 免費帳號步驟
- 建立 cluster、取得 broker URL
- 建立 credentials（username/password）
- ACL 設定：限制 worker 只能存取 `tasks/#` 和 `workers/#`
- 測試連線：`mosquitto_pub -h ... -u ... -P ... -t test -m hello`

#### `infra/cloudflare-deploy.md`

- 安裝 wrangler CLI
- `wrangler login`
- 設定 secrets：
  ```bash
  wrangler secret put GITHUB_WEBHOOK_SECRET
  wrangler secret put MQTT_BROKER_URL
  wrangler secret put MQTT_USERNAME
  wrangler secret put MQTT_PASSWORD
  ```
- `pnpm deploy`
- GitHub webhook 設定步驟（URL、secret、events: Issues, Pull requests）

#### `infra/tailscale-setup.md`（選配）

- 建立 tailnet
- 邀請 worker machines
- ACL tag 設定：`tag:ai-worker`
- 若 broker 在私網的設定方式（MVP 用 HiveMQ Cloud 可略過）

#### `infra/worker-deployment.md`

- 前置條件：Python 3.11+、uv、gh CLI、claude CLI
- 安裝：`uv tool install ai-swarm-worker`
- 設定環境變數（或 `~/.ai-swarm/config.toml`）
- 啟動：`worker start`
- 設成 launchd / systemd 背景服務（附範例 plist / service 檔）
- 升級：`uv tool upgrade ai-swarm-worker`

### 驗收標準

- [ ] 按照文件操作，一個全新環境能在 30 分鐘內跑起來
- [ ] 每份文件都有 troubleshooting section
- [ ] `infra/` 裡沒有真實 credentials（所有範例用 placeholder）

---

## 依賴關係圖

```
Task 1 (scaffold) ──┐
                    ├─► Task 2 (schema) ──► Task 4 (daemon) ──► Task 5 (execute) ──► Task 6 (routing)
Task 3 (bridge) ────┘                                                                      │
                                                                                           ▼
                                                                                     Task 7 (e2e)
                                                                                           │
                                                                                           ▼
                                                                                     Task 8 (deploy)
```

## 技術決策記錄

| 決策 | 選擇 | 時間 | 原因 |
|---|---|---|---|
| Worker daemon 語言 | Go → Python | 2026-04-21 | Anthropic SDK Python-first；使用者偏好；迭代速度 |
| 套件管理（Node） | npm → pnpm | 2026-04-21 | 使用者所有專案已遷移到 pnpm |
| 型別檢查（Python） | mypy → pyright | 2026-04-21 | 使用者使用 Pylance（同一引擎），IDE/CI 一致 |
| Claude 呼叫方式 | CLI `--prompt-file` | 2026-04-20 | MVP 最簡單，無額外 SDK 依賴 |
| MQTT broker | HiveMQ Cloud 免費方案 | 2026-04-20 | 100 連線，10GB/月，MVP 夠用 |
