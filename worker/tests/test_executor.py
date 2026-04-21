from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import ai_swarm_worker.executor as executor_module
from ai_swarm_worker.executor import TaskExecutor, TaskResult
from ai_swarm_worker.task import Task


def make_task() -> Task:
    return Task.model_validate(
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
            "labels": ["bug"],
            "prompt": "Fix the failing test",
            "priority": "normal",
            "created_at": "2026-04-20T12:00:00Z",
            "timeout_seconds": 600,
        }
    )


def make_executor() -> TaskExecutor:
    mqtt_client = Mock()
    config = Mock(worker_id="worker-1")
    return TaskExecutor(mqtt_client, config)


def test_handle_message_invalid_json(monkeypatch) -> None:
    executor = make_executor()
    run = Mock()
    monkeypatch.setattr(executor_module.subprocess, "run", run)

    executor.handle_message("{invalid json")

    run.assert_not_called()


def test_handle_message_drops_when_busy(monkeypatch) -> None:
    executor = make_executor()
    executor._busy = True
    thread = Mock()
    monkeypatch.setattr(executor_module.threading, "Thread", Mock(return_value=thread))

    executor.handle_message(make_task().model_dump_json())

    thread.start.assert_not_called()


def test_publish_progress() -> None:
    executor = make_executor()
    task = make_task()

    executor._publish_progress(task, "running", 45.0, "Running tests")

    topic, payload = executor.mqtt_client.publish.call_args.args
    data = json.loads(payload)
    assert topic == f"tasks/{task.task_id}/progress"
    assert data["task_id"] == task.task_id
    assert data["worker_id"] == "worker-1"
    assert data["status"] == "running"
    assert data["elapsed_seconds"] == 45.0
    assert data["last_output_line"] == "Running tests"
    assert data["timestamp"].endswith("Z")


def test_publish_result() -> None:
    executor = make_executor()
    task = make_task()
    result = TaskResult(
        task_id=task.task_id,
        worker_id="worker-1",
        status="success",
        exit_code=0,
        branch="ai/task-123",
        elapsed_seconds=12.34,
    )

    executor._publish_result(task, result)

    topic, payload = executor.mqtt_client.publish.call_args.args
    data = json.loads(payload)
    assert topic == f"tasks/{task.task_id}/result"
    assert data["task_id"] == task.task_id
    assert data["worker_id"] == "worker-1"
    assert data["status"] == "success"
    assert data["exit_code"] == 0
    assert data["branch"] == "ai/task-123"
    assert data["elapsed_seconds"] == 12.3
    assert data["error"] is None
    assert data["timestamp"].endswith("Z")


def test_cleanup_worktree_removes_on_failure(monkeypatch, tmp_path: Path) -> None:
    executor = make_executor()
    worktree_path = tmp_path / "worktree"
    worktree_path.mkdir()

    monkeypatch.setattr(
        executor_module.subprocess,
        "run",
        Mock(return_value=SimpleNamespace(returncode=1, stdout="")),
    )

    executor._cleanup_worktree(worktree_path)

    assert not worktree_path.exists()
