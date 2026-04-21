from __future__ import annotations

import pytest
from pydantic import ValidationError

from ai_swarm_worker.task import Task


def test_valid_task_deserializes_correctly() -> None:
    task = Task.model_validate(
        {
            "task_id": "task-123",
            "type": "implementation",
            "source": "github",
            "repo": "owner/repo",
            "ref": {
                "issue_number": 42,
                "pr_number": None,
                "commit_sha": "abc123",
            },
            "labels": ["bug", "urgent"],
            "prompt": "Fix the failing test",
            "priority": "high",
            "created_at": "2026-04-20T12:00:00Z",
            "timeout_seconds": 600,
        }
    )

    assert task.task_id == "task-123"
    assert task.type == "implementation"
    assert task.ref.issue_number == 42
    assert task.ref.pr_number is None
    assert task.has_label("urgent") is True


def test_missing_prompt_fails_validation() -> None:
    with pytest.raises(ValidationError):
        Task.model_validate(
            {
                "task_id": "task-123",
                "type": "implementation",
                "source": "github",
                "repo": "owner/repo",
                "ref": {
                    "issue_number": None,
                    "pr_number": None,
                    "commit_sha": None,
                },
                "labels": [],
                "priority": "normal",
                "created_at": "2026-04-20T12:00:00Z",
                "timeout_seconds": 600,
            }
        )


def test_unknown_type_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Task.model_validate(
            {
                "task_id": "task-123",
                "type": "deployment",
                "source": "github",
                "repo": "owner/repo",
                "ref": {
                    "issue_number": None,
                    "pr_number": 7,
                    "commit_sha": None,
                },
                "labels": ["review"],
                "prompt": "Review this pull request",
                "priority": "normal",
                "created_at": "2026-04-20T12:00:00Z",
                "timeout_seconds": 600,
            }
        )
