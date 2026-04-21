from __future__ import annotations

import logging
import subprocess
from pathlib import Path

from ai_swarm_worker.executor import TaskResult
from ai_swarm_worker.task import Task

logger = logging.getLogger(__name__)


def run_gh(*args: str, cwd: Path) -> str:
    """Run gh CLI command and return stdout."""
    result = subprocess.run(
        ["gh", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def run_git(*args: str, cwd: Path) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def build_pr_body(task: Task, result: TaskResult) -> str:
    issue_ref = f"#{task.ref.issue_number}" if task.ref.issue_number else "n/a"
    closes = f"\n\nCloses #{task.ref.issue_number}" if task.ref.issue_number else ""
    return (
        "## AI Task Result\n\n"
        f"- **Task ID:** {task.task_id}\n"
        f"- **Source:** {task.repo} issue {issue_ref}\n"
        f"- **Elapsed:** {result.elapsed_seconds:.0f}s\n"
        f"- **Status:** {result.status}"
        f"{closes}"
    )


def push_and_route(task: Task, result: TaskResult, worktree_path: Path) -> None:
    """Push branch and open PR based on task labels. No-op if result.branch is None."""
    if result.branch is None:
        logger.info("No branch to push", extra={"task_id": task.task_id})
        return

    if result.status != "success":
        logger.info(
            "Skipping push for non-success result",
            extra={"task_id": task.task_id, "status": result.status},
        )
        return

    labels = set(task.labels)

    try:
        if "ai-review" in labels:
            _handle_review_task(task, worktree_path)
        elif "ai-task" in labels and "auto-merge" in labels:
            run_git("push", "origin", result.branch, cwd=worktree_path)
            logger.info("Branch pushed", extra={"branch": result.branch})
            _open_pr(task, result, worktree_path, auto_merge=True)
        elif "ai-task" in labels and "human-review" in labels:
            run_git("push", "origin", result.branch, cwd=worktree_path)
            logger.info("Branch pushed", extra={"branch": result.branch})
            logger.info(
                "human-review: branch pushed, no PR created",
                extra={"branch": result.branch},
            )
        elif "ai-task" in labels:
            run_git("push", "origin", result.branch, cwd=worktree_path)
            logger.info("Branch pushed", extra={"branch": result.branch})
            _open_pr(task, result, worktree_path, auto_merge=False)
        else:
            logger.info(
                "No matching label routing rule",
                extra={"labels": list(labels)},
            )

    except subprocess.CalledProcessError as exc:
        logger.error(
            "GitHub operation failed",
            extra={"task_id": task.task_id, "stderr": exc.stderr},
        )


def _open_pr(task: Task, result: TaskResult, cwd: Path, *, auto_merge: bool) -> None:
    title = f"ai: {task.task_id}"
    body = build_pr_body(task, result)

    args = ["pr", "create", "--title", title, "--body", body]
    if not auto_merge:
        args.append("--draft")

    pr_url = run_gh(*args, cwd=cwd)
    logger.info("PR created", extra={"url": pr_url, "auto_merge": auto_merge})

    if auto_merge:
        run_gh("pr", "merge", "--auto", "--squash", cwd=cwd)
        logger.info("Auto-merge enabled", extra={"url": pr_url})


def _handle_review_task(task: Task, cwd: Path) -> None:
    if task.ref.pr_number is None:
        logger.warning(
            "ai-review task has no pr_number",
            extra={"task_id": task.task_id},
        )
        return

    body = f"AI review for task `{task.task_id}`"
    run_gh(
        "pr",
        "review",
        str(task.ref.pr_number),
        "--comment",
        "--body",
        body,
        cwd=cwd,
    )
    logger.info("Review comment posted", extra={"pr_number": task.ref.pr_number})
