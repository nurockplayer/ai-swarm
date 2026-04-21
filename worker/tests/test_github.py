from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

from ai_swarm_worker.executor import TaskResult
from ai_swarm_worker.github import push_and_route
from ai_swarm_worker.task import Task, TaskRef


def make_task(labels: list[str], pr_number: int | None = None) -> Task:
    return Task(
        task_id="task-123",
        type="implementation",
        source="github",
        repo="owner/repo",
        ref=TaskRef(issue_number=42, pr_number=pr_number, commit_sha="abc123"),
        labels=labels,
        prompt="Fix the task",
        priority="normal",
        created_at=datetime(2026, 4, 21, tzinfo=UTC),
        timeout_seconds=600,
    )


def make_result(
    status: str = "success",
    branch: str | None = "ai/task-123",
) -> TaskResult:
    return TaskResult(
        task_id="task-123",
        worker_id="worker-1",
        status=status,
        exit_code=0 if status == "success" else 1,
        branch=branch,
        elapsed_seconds=10.0,
    )


def make_subprocess_result(stdout: str = "") -> MagicMock:
    m = MagicMock()
    m.stdout = stdout
    m.returncode = 0
    return m


class TestPushAndRoute:
    def test_push_and_route_auto_merge(self) -> None:
        task = make_task(["ai-task", "auto-merge"])
        result = make_result()
        worktree = Path("/tmp/worktree")

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = make_subprocess_result("https://github.com/owner/repo/pull/1")
            push_and_route(task, result, worktree)

        calls = mock_run.call_args_list
        assert any("git" in str(c) and "push" in str(c) for c in calls)

        pr_create_calls = [
            c for c in calls if "gh" in str(c) and "pr" in str(c) and "create" in str(c)
        ]
        assert len(pr_create_calls) >= 1
        pr_create_args = pr_create_calls[0][0][0]
        assert "--draft" not in pr_create_args

        merge_calls = [c for c in calls if "gh" in str(c) and "merge" in str(c)]
        assert len(merge_calls) >= 1
        merge_args = merge_calls[0][0][0]
        assert "--auto" in merge_args
        assert "--squash" in merge_args

    def test_push_and_route_draft_pr(self) -> None:
        task = make_task(["ai-task"])
        result = make_result()
        worktree = Path("/tmp/worktree")

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = make_subprocess_result("https://github.com/owner/repo/pull/2")
            push_and_route(task, result, worktree)

        calls = mock_run.call_args_list
        pr_create_calls = [c for c in calls if "gh" in str(c) and "create" in str(c)]
        assert len(pr_create_calls) >= 1
        pr_create_args = pr_create_calls[0][0][0]
        assert "--draft" in pr_create_args

        merge_calls = [c for c in calls if "gh" in str(c) and "merge" in str(c)]
        assert len(merge_calls) == 0

    def test_push_and_route_human_review(self) -> None:
        task = make_task(["ai-task", "human-review"])
        result = make_result()
        worktree = Path("/tmp/worktree")

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = make_subprocess_result()
            push_and_route(task, result, worktree)

        calls = mock_run.call_args_list
        git_push_calls = [c for c in calls if "git" in str(c) and "push" in str(c)]
        assert len(git_push_calls) >= 1

        pr_create_calls = [c for c in calls if "gh" in str(c) and "create" in str(c)]
        assert len(pr_create_calls) == 0

    def test_push_and_route_ai_review_comments_without_push(self) -> None:
        task = make_task(["ai-review"], pr_number=7)
        result = make_result()
        worktree = Path("/tmp/worktree")

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = make_subprocess_result()
            push_and_route(task, result, worktree)

        calls = mock_run.call_args_list
        git_push_calls = [c for c in calls if "git" in str(c) and "push" in str(c)]
        assert len(git_push_calls) == 0

        review_calls = [c for c in calls if "gh" in str(c) and "review" in str(c)]
        assert len(review_calls) == 1
        review_args = review_calls[0][0][0]
        assert "--comment" in review_args
        assert "--body" in review_args

    def test_push_and_route_skips_on_failure(self) -> None:
        task = make_task(["ai-task"])
        result = make_result(status="failure")
        worktree = Path("/tmp/worktree")

        with patch("subprocess.run") as mock_run:
            push_and_route(task, result, worktree)

        calls = mock_run.call_args_list
        git_push_calls = [c for c in calls if "git" in str(c) and "push" in str(c)]
        assert len(git_push_calls) == 0

    def test_push_and_route_no_matching_label_only_logs(self) -> None:
        task = make_task(["bug"])
        result = make_result()
        worktree = Path("/tmp/worktree")

        with patch("subprocess.run") as mock_run:
            push_and_route(task, result, worktree)

        mock_run.assert_not_called()
