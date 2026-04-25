# ai-swarm — Claude Code Guidelines

## 語言設定

永遠使用台灣正體中文回覆，不得使用日文、韓文或簡體中文。

## AI 分工

本專案採分層協作模式，依任務規模決定誰動手：

| 任務等級 | Claude Code | Codex |
|---|---|---|
| Trivial（< 10 行、機械式） | 直接 patch | — |
| Small / Medium | 寫 issue | 實作 + PR |
| Test-Driven / Debug Loop | 定義任務 | debug / patch / rerun |
| Architecture / High Risk | 設計拆解 | 逐 issue 實作 |

詳見 `docs/codex-workflow.md`。

關鍵規則：

- Trivial 以外，Claude Code 不直接寫程式碼
- Codex 額度緊張時 Claude Code 應等待，不自己代打（除非使用者明確同意）
- 重複性掃描、大量檔案摘要 → 優先交給 Codex/Gemini，節省 Claude token

## 操作權限邊界

- Read-only 可直接執行：gh 查詢、git 讀取、檔案 Read/Grep/Glob
- 變動操作必須事先詢問：Edit/Write、commit、push、branch 操作、gh pr create/merge/review、issue 建立編輯

## Scope 邊界

- PR 只包含 issue 明確列出的任務；不順手重構、不擴張到其他 label/repo
- 實作途中發現額外想做的事 → 另開 issue，不混進現 PR
- docs / research draft 不自動視為 implementation source of truth

## AI 協作守則

- 不得未經驗證就宣稱「已完成」；必須回報實際跑過的測試、未驗證部分、已知風險
- Agent 提出的額外功能、future work、重構建議 → 拆成獨立 issue/PR

## 專案硬限制

- 完全 project-agnostic：repo、project、label 從 config 讀取，嚴禁 hardcode
- No real credentials in repo：secret 只透過環境變數，不 commit
- MVP 單 worker 單任務（git worktree 隔離）
- MVP 只做 manual toggle idle 模式（worker start / worker stop）

## Branch 命名

<type>/<short-description>，例：feat/mqtt-client、fix/mqtt-reconnect、docs/readme-split

## Commit 訊息格式

```text
<type>: <short description>

refs #<issue>

Co-Authored-By: Claude Sonnet 4.6 <claude[bot]@anthropic.com>
```

Type：feat / fix / docs / chore / refactor / test

- 實作過程中的 commit 用 refs #號碼
- PR 最後一個 commit 或 PR 描述用 closes #號碼

## 套件管理與工具

- Python：一律 uv（不用 pip/poetry）
- Node：一律 pnpm（不用 npm/yarn）
- Type check：Python 用 basedpyright（不用 mypy 或 pyright）；TypeScript 用 tsc
- Lint/Format：Python 用 ruff；TypeScript 用 bridge/ 既有設定

## 專案結構

見 README.md#專案結構。

## 架構

見 docs/architecture.md、docs/task-format.md。
