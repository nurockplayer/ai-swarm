from __future__ import annotations

from datetime import datetime
from typing import Literal, Self

from pydantic import BaseModel, field_validator, model_validator

TaskType = Literal["implementation", "review"]
Priority = Literal["low", "normal", "high"]


class TaskRef(BaseModel):
    issue_number: int | None
    pr_number: int | None
    commit_sha: str | None


class Task(BaseModel):
    task_id: str
    type: TaskType
    source: str
    repo: str
    ref: TaskRef
    labels: list[str]
    prompt: str
    priority: Priority
    created_at: datetime
    timeout_seconds: int

    @field_validator("task_id")
    @classmethod
    def validate_task_id(cls, value: str) -> str:
        if value == "":
            raise ValueError("task_id is required")
        return value

    @field_validator("source")
    @classmethod
    def validate_source(cls, value: str) -> str:
        if value != "github":
            raise ValueError("source must be github")
        return value

    @field_validator("repo")
    @classmethod
    def validate_repo(cls, value: str) -> str:
        parts = value.split("/")
        if len(parts) != 2 or parts[0] == "" or parts[1] == "":
            raise ValueError("repo must be in owner/repo form")
        return value

    @field_validator("labels")
    @classmethod
    def validate_labels(cls, value: list[str]) -> list[str]:
        for index, label in enumerate(value):
            if label == "":
                raise ValueError(f"labels[{index}] must not be empty")
        return value

    @field_validator("prompt")
    @classmethod
    def validate_prompt(cls, value: str) -> str:
        if value == "":
            raise ValueError("prompt is required")
        return value

    @model_validator(mode="after")
    def validate_timeout_seconds(self) -> Self:
        if self.timeout_seconds < 60:
            raise ValueError("timeout_seconds must be at least 60")
        return self

    def has_label(self, label: str) -> bool:
        return label in self.labels
