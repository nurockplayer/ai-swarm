from __future__ import annotations

import json
import logging
import shutil
import subprocess
import threading
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from pydantic import ValidationError

from ai_swarm_worker.config import WorkerConfig
from ai_swarm_worker.mqtt import MQTTClient
from ai_swarm_worker.task import Task

logger = logging.getLogger(__name__)

REPOS_CACHE = Path.home() / ".ai-swarm" / "repos"
WORKTREES_DIR = Path("/tmp/ai-swarm")
VERSION = "0.1.0"


@dataclass
class TaskResult:
    task_id: str
    worker_id: str
    status: str  # "success" | "failure" | "timeout"
    exit_code: int | None
    branch: str | None
    elapsed_seconds: float
    error: str | None = None


class TaskExecutor:
    def __init__(self, mqtt_client: MQTTClient, config: WorkerConfig) -> None:
        self.mqtt_client = mqtt_client
        self.config = config
        self._lock = threading.Lock()
        self._busy = False

    @property
    def is_busy(self) -> bool:
        return self._busy

    def handle_message(self, payload: str) -> None:
        """Called by MQTT on_message — runs in MQTT network thread."""
        try:
            task = Task.model_validate_json(payload)
        except ValidationError:
            logger.error(
                "Invalid task payload",
                extra={"payload_preview": payload[:200]},
            )
            return

        with self._lock:
            if self._busy:
                logger.warning(
                    "Worker busy, dropping task",
                    extra={"task_id": task.task_id},
                )
                return
            self._busy = True

        thread = threading.Thread(target=self._execute, args=(task,), daemon=True)
        thread.start()

    def _execute(self, task: Task) -> None:
        start = datetime.now(UTC)
        branch = f"ai/{task.task_id}"
        worktree_path = WORKTREES_DIR / task.task_id

        try:
            logger.info(
                "Task started",
                extra={"task_id": task.task_id, "repo": task.repo},
            )
            self._publish_progress(task, "running", 0, "starting")

            repo_path = self._ensure_repo(task.repo)
            self._create_worktree(repo_path, worktree_path, branch)

            prompt_file = worktree_path / "task-prompt.md"
            prompt_file.write_text(task.prompt, encoding="utf-8")

            exit_code = self._run_claude(task, worktree_path, start)

            elapsed = (datetime.now(UTC) - start).total_seconds()
            status = "success" if exit_code == 0 else "failure"

            result = TaskResult(
                task_id=task.task_id,
                worker_id=self.config.worker_id,
                status=status,
                exit_code=exit_code,
                branch=branch,
                elapsed_seconds=elapsed,
            )
            logger.info(
                "Task finished",
                extra={"task_id": task.task_id, "status": status},
            )

        except TimeoutError:
            elapsed = (datetime.now(UTC) - start).total_seconds()
            result = TaskResult(
                task_id=task.task_id,
                worker_id=self.config.worker_id,
                status="timeout",
                exit_code=None,
                branch=branch,
                elapsed_seconds=elapsed,
                error=f"Exceeded {task.timeout_seconds}s timeout",
            )
            logger.warning("Task timed out", extra={"task_id": task.task_id})

        except Exception as exc:  # noqa: BLE001
            elapsed = (datetime.now(UTC) - start).total_seconds()
            result = TaskResult(
                task_id=task.task_id,
                worker_id=self.config.worker_id,
                status="failure",
                exit_code=None,
                branch=None,
                elapsed_seconds=elapsed,
                error=str(exc),
            )
            logger.exception("Task failed", extra={"task_id": task.task_id})

        finally:
            self._cleanup_worktree(worktree_path)
            self._busy = False

        self._publish_result(task, result)

    def _ensure_repo(self, repo: str) -> Path:
        repo_dir_name = repo.replace("/", "-")
        repo_path = REPOS_CACHE / repo_dir_name
        REPOS_CACHE.mkdir(parents=True, exist_ok=True)

        if not repo_path.exists():
            logger.info("Cloning repo", extra={"repo": repo})
            subprocess.run(
                [
                    "git",
                    "clone",
                    "--depth",
                    "1",
                    f"https://github.com/{repo}.git",
                    str(repo_path),
                ],
                check=True,
                capture_output=True,
            )
        else:
            subprocess.run(
                ["git", "-C", str(repo_path), "pull", "--ff-only"],
                check=False,
                capture_output=True,
            )
        return repo_path

    def _create_worktree(
        self,
        repo_path: Path,
        worktree_path: Path,
        branch: str,
    ) -> None:
        WORKTREES_DIR.mkdir(parents=True, exist_ok=True)
        if worktree_path.exists():
            shutil.rmtree(worktree_path)

        subprocess.run(
            [
                "git",
                "-C",
                str(repo_path),
                "worktree",
                "add",
                str(worktree_path),
                "-b",
                branch,
            ],
            check=True,
            capture_output=True,
        )
        logger.info(
            "Worktree created",
            extra={"path": str(worktree_path), "branch": branch},
        )

    def _run_claude(self, task: Task, cwd: Path, start: datetime) -> int:
        cmd = [
            "claude",
            "--print",
            "--prompt-file",
            "task-prompt.md",
            "--dangerously-skip-permissions",
        ]

        proc = subprocess.Popen(
            cmd,
            cwd=str(cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

        last_line = ""
        last_progress_at = 0.0

        try:
            assert proc.stdout is not None
            for line in proc.stdout:
                line = line.rstrip()
                if line:
                    last_line = line
                    logger.debug("claude: %s", line)

                elapsed = (datetime.now(UTC) - start).total_seconds()
                if elapsed - last_progress_at >= 10:
                    self._publish_progress(task, "running", elapsed, last_line)
                    last_progress_at = elapsed

                if elapsed > task.timeout_seconds:
                    proc.kill()
                    raise TimeoutError

            proc.wait(timeout=5)
            return proc.returncode if proc.returncode is not None else 1

        except TimeoutError:
            proc.kill()
            raise

    def _cleanup_worktree(self, worktree_path: Path) -> None:
        if worktree_path.exists():
            try:
                result = subprocess.run(
                    ["git", "-C", str(worktree_path), "rev-parse", "--git-common-dir"],
                    capture_output=True,
                    text=True,
                )
                if result.returncode == 0:
                    common_dir = result.stdout.strip()
                    repo_root = Path(common_dir).parent
                    subprocess.run(
                        [
                            "git",
                            "-C",
                            str(repo_root),
                            "worktree",
                            "remove",
                            "--force",
                            str(worktree_path),
                        ],
                        capture_output=True,
                    )
                else:
                    shutil.rmtree(worktree_path)
            except Exception:  # noqa: BLE001
                shutil.rmtree(worktree_path, ignore_errors=True)

    def _publish_progress(
        self,
        task: Task,
        status: str,
        elapsed: float,
        last_line: str,
    ) -> None:
        topic = f"tasks/{task.task_id}/progress"
        payload = json.dumps({
            "task_id": task.task_id,
            "worker_id": self.config.worker_id,
            "status": status,
            "elapsed_seconds": round(elapsed, 1),
            "last_output_line": last_line[:500],
            "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        })
        self.mqtt_client.publish(topic, payload)

    def _publish_result(self, task: Task, result: TaskResult) -> None:
        topic = f"tasks/{task.task_id}/result"
        payload = json.dumps({
            "task_id": result.task_id,
            "worker_id": result.worker_id,
            "status": result.status,
            "exit_code": result.exit_code,
            "branch": result.branch,
            "elapsed_seconds": round(result.elapsed_seconds, 1),
            "error": result.error,
            "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        })
        self.mqtt_client.publish(topic, payload)
