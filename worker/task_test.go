package main

import (
	"encoding/json"
	"testing"
)

func TestValidTaskDeserializesCorrectly(t *testing.T) {
	data := []byte(`{
		"task_id": "task-123",
		"type": "implementation",
		"source": "github",
		"repo": "owner/repo",
		"ref": {
			"issue_number": 42,
			"pr_number": null,
			"commit_sha": "abc123"
		},
		"labels": ["bug", "urgent"],
		"prompt": "Fix the failing test",
		"priority": "high",
		"created_at": "2026-04-20T12:00:00Z",
		"timeout_seconds": 600
	}`)

	var task Task
	if err := json.Unmarshal(data, &task); err != nil {
		t.Fatalf("unmarshal task: %v", err)
	}
	if err := task.Validate(); err != nil {
		t.Fatalf("validate task: %v", err)
	}

	if task.TaskID != "task-123" {
		t.Fatalf("TaskID = %q, want task-123", task.TaskID)
	}
	if task.Type != TaskTypeImplementation {
		t.Fatalf("Type = %q, want %q", task.Type, TaskTypeImplementation)
	}
	if task.Ref.IssueNumber == nil || *task.Ref.IssueNumber != 42 {
		t.Fatalf("IssueNumber = %v, want 42", task.Ref.IssueNumber)
	}
	if task.Ref.PRNumber != nil {
		t.Fatalf("PRNumber = %v, want nil", task.Ref.PRNumber)
	}
	if !task.HasLabel("urgent") {
		t.Fatalf("HasLabel(%q) = false, want true", "urgent")
	}
}

func TestMissingRequiredFieldFailsValidation(t *testing.T) {
	data := []byte(`{
		"task_id": "task-123",
		"type": "implementation",
		"source": "github",
		"repo": "owner/repo",
		"ref": {
			"issue_number": null,
			"pr_number": null,
			"commit_sha": null
		},
		"labels": [],
		"priority": "normal",
		"created_at": "2026-04-20T12:00:00Z",
		"timeout_seconds": 600
	}`)

	var task Task
	if err := json.Unmarshal(data, &task); err != nil {
		t.Fatalf("unmarshal task: %v", err)
	}
	if err := task.Validate(); err == nil {
		t.Fatal("Validate() succeeded, want missing prompt failure")
	}
}

func TestUnknownTypeIsRejected(t *testing.T) {
	data := []byte(`{
		"task_id": "task-123",
		"type": "deployment",
		"source": "github",
		"repo": "owner/repo",
		"ref": {
			"issue_number": null,
			"pr_number": 7,
			"commit_sha": null
		},
		"labels": ["review"],
		"prompt": "Review this pull request",
		"priority": "normal",
		"created_at": "2026-04-20T12:00:00Z",
		"timeout_seconds": 600
	}`)

	var task Task
	if err := json.Unmarshal(data, &task); err != nil {
		t.Fatalf("unmarshal task: %v", err)
	}
	if err := task.Validate(); err == nil {
		t.Fatal("Validate() succeeded, want unknown type failure")
	}
}
