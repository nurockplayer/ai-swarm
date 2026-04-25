# Codex 工作流程

本文件定義本專案目前的官方工作流程、任務分層規則、與 Claude / Codex 的角色偏好。

## 核心原則

比固定角色更重要的原則：

- 規格清晰、驗證明確、可機械執行 -> Codex
- 模糊度高、需要判斷、需要架構決策 -> Claude Code

一句話版本：

```text
Codex 適合確定性高的任務，Claude Code 適合模糊性高的任務。
```

## 角色偏好

### Claude Code

預設負責：

- 規劃架構
- 拆解需求與定義 scope
- 撰寫或整理 GitHub issue
- 在 PR 最後做 review 與驗收

可以直接動手的例外：

- trivial patch
- typo / 文案修正
- 單點 config 調整
- 幾乎不需要測試循環的機械式修改

### Codex

預設負責：

- 寫 code
- debug
- patch
- commit / push / 開 PR
- 根據 review feedback 修正

特別適合：

- 規格清楚的功能開發
- 需要反覆跑測試直到通過的任務
- bugfix / patch / debug loop

## 任務分層

### 1. Trivial

定義：

- 小於約 10 行的改動
- typo、文案、單點 config
- 明確、機械式、幾乎不需要來回驗證

流程：

```text
Claude Code 直接 patch
    ↓
必要時自行驗證
    ↓
直接提交或收斂結果
```

這類任務不強制走 issue -> Codex -> review 三段式。

### 2. Small / Medium

定義：

- 一般功能、API、元件、文件補完、普通 bugfix
- scope 清楚，但仍值得保留 GitHub artifact

流程：

```text
Claude Code 寫 issue
    ↓
Codex 實作、commit、push、開 PR
    ↓
Claude Code review
    ↓
Codex 修正
```

這是本專案的預設主流程。

### 3. Test-Driven / Debug Loop

定義：

- 需要反覆跑測試直到過
- 修 failing test / failing CI
- 追 bug、修 patch、驗證回歸

流程：

```text
Claude Code 提供 issue 或明確任務定義
    ↓
Codex 持續 debug / patch / rerun
    ↓
Codex 開 PR
    ↓
Claude Code final review
```

原則：這類任務一定優先交給 Codex，不要讓 Claude Code 進 implementation loop。

### 4. Architecture / High Risk

定義：

- 架構重構
- 跨模組高風險改動
- schema、infra、workflow、系統邊界調整
- scope 尚未清楚，需要先做設計

流程：

```text
Claude Code 先做設計與拆解
    ↓
拆成一個或多個 issue
    ↓
Codex 逐個實作
    ↓
Claude Code final review
```

原則：先讓 Claude Code 處理模糊度，再讓 Codex 處理確定性執行。

## 現行官方主流程

對大多數 `Small / Medium` 任務，唯一推薦主流程是：

```text
Claude Code 規劃並寫完整 GitHub issue
    ↓
Codex 依 issue 內容寫 code / debug / patch
    ↓
Codex commit / push / 開 PR
    ↓
Claude Code 在 GitHub PR 上做最終 review
    ↓
Codex 依 review feedback 修正
```

這條流程的目標是把需求、實作、審查都放回 GitHub artifact：

- issue 是單一需求來源
- PR 是單一實作交付物
- review comment 是單一審查紀錄

## `/codex:rescue` 狀態

`/codex:rescue` 已廢棄，不再是本專案允許的日常流程。

原因：

- Claude Code 內直接 dispatch 給 Codex 的可追蹤性不足
- prompt、acceptance criteria、review 脈絡不集中在 GitHub
- 後續交接、稽核、回溯不如 issue / PR workflow 清楚

如果需要 Codex 執行工作，請改成：

1. 由 Claude Code 建立或整理 GitHub issue
2. 在 issue 內放完整 prompt 與 acceptance criteria
3. 讓 Codex 依 issue 開 branch、實作、push、開 PR

## Issue 撰寫規則

當任務屬於 `Small / Medium`、`Test-Driven / Debug Loop`、或 `Architecture / High Risk` 時，Claude Code 建 issue 至少要包含：

- `Task Level`
- `背景`
- `目標`
- `範圍`
- `Acceptance Criteria`
- `限制`
- `交付物`
- branch 命名要求

建議額外包含：

- 非目標
- 參考文件 / URL
- 驗證方式

## Codex 實作規則

Codex 接手 issue 後，應遵守：

- 以 issue 為唯一需求來源，不自行擴 scope
- branch 名稱依 issue 指示建立
- commit message 與 PR title 依 issue 指示
- PR body 要回報修改摘要與 AC 完成情況
- 若 issue 不完整，先補齊假設或回報缺口，不硬做
- 實作、debug、patch 由 Codex 負責

## Claude Code Review 規則

Claude Code review 只在 GitHub PR 上進行，不再以 Claude Code session 內的 `/codex:review` 或 `/codex:rescue` 流程為主。

review 重點：

- 是否符合 issue scope
- 是否逐條滿足 acceptance criteria
- 是否有不必要擴張
- 是否缺測試、缺文件、或引入風險

## 不再推薦的流程

以下流程都不再推薦：

### 1. Claude Code 內直接用 `/codex:rescue`

```text
Claude Code 寫 sub-spec
    ↓
/codex:rescue "<prompt>"
    ↓
Claude Code 在 session 內追結果
```

狀態：廢棄。

### 2. 把 sub-spec 貼成 issue comment，等待黑箱非同步領取

```text
sub-spec comment 到 issue
    ↓
等待背景 worker 非同步領取
```

狀態：不推薦。需求與執行上下文過度分散。

## 模板

請優先使用：

- [GitHub issue template](../.github/ISSUE_TEMPLATE/codex-task.yml)
- [PR template](../.github/pull_request_template.md)

這兩份模板就是本流程的標準輸入與標準輸出格式。
