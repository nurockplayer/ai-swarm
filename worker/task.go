package main

import (
	"errors"
	"fmt"
	"strings"
	"time"
)

// TaskType identifies the kind of work the worker should perform.
type TaskType string

const (
	// TaskTypeImplementation requests implementation work.
	TaskTypeImplementation TaskType = "implementation"

	// TaskTypeReview requests review work.
	TaskTypeReview TaskType = "review"
)

// Priority identifies the scheduling priority for a task.
type Priority string

const (
	// PriorityLow marks a task as lower priority than normal work.
	PriorityLow Priority = "low"

	// PriorityNormal marks a task as standard priority.
	PriorityNormal Priority = "normal"

	// PriorityHigh marks a task as higher priority than normal work.
	PriorityHigh Priority = "high"
)

// TaskRef points to the GitHub object or commit that produced the task.
type TaskRef struct {
	// IssueNumber is the GitHub issue number associated with the task, when any.
	IssueNumber *int `json:"issue_number"`

	// PRNumber is the GitHub pull request number associated with the task, when any.
	PRNumber *int `json:"pr_number"`

	// CommitSHA is the Git commit SHA associated with the task, when any.
	CommitSHA *string `json:"commit_sha"`
}

// Task is the canonical bridge-to-worker task contract.
type Task struct {
	// TaskID is the stable unique identifier for the task.
	TaskID string `json:"task_id"`

	// Type identifies whether the task is implementation or review work.
	Type TaskType `json:"type"`

	// Source identifies the external system that published the task.
	Source string `json:"source"`

	// Repo is the GitHub repository in owner/repo form.
	Repo string `json:"repo"`

	// Ref identifies the issue, pull request, or commit associated with the task.
	Ref TaskRef `json:"ref"`

	// Labels contains the labels attached to the task.
	Labels []string `json:"labels"`

	// Prompt contains the worker instructions for the task.
	Prompt string `json:"prompt"`

	// Priority identifies the task scheduling priority.
	Priority Priority `json:"priority"`

	// CreatedAt is the RFC3339 timestamp for when the task was created.
	CreatedAt string `json:"created_at"`

	// TimeoutSeconds is the maximum task runtime in seconds.
	TimeoutSeconds int `json:"timeout_seconds"`
}

// HasLabel reports whether the task has the given label.
func (t Task) HasLabel(label string) bool {
	for _, taskLabel := range t.Labels {
		if taskLabel == label {
			return true
		}
	}
	return false
}

// Validate checks the task fields that JSON decoding cannot enforce.
func (t Task) Validate() error {
	if t.TaskID == "" {
		return errors.New("task_id is required")
	}
	if t.Type != TaskTypeImplementation && t.Type != TaskTypeReview {
		return fmt.Errorf("type must be one of %q or %q", TaskTypeImplementation, TaskTypeReview)
	}
	if t.Source != "github" {
		return errors.New("source must be github")
	}
	if !validRepo(t.Repo) {
		return errors.New("repo must be in owner/repo form")
	}
	if t.Labels == nil {
		return errors.New("labels is required")
	}
	for i, label := range t.Labels {
		if label == "" {
			return fmt.Errorf("labels[%d] must not be empty", i)
		}
	}
	if t.Prompt == "" {
		return errors.New("prompt is required")
	}
	if t.Priority != PriorityLow && t.Priority != PriorityNormal && t.Priority != PriorityHigh {
		return fmt.Errorf("priority must be one of %q, %q, or %q", PriorityLow, PriorityNormal, PriorityHigh)
	}
	if _, err := time.Parse(time.RFC3339, t.CreatedAt); err != nil {
		return fmt.Errorf("created_at must be RFC3339 date-time: %w", err)
	}
	if t.TimeoutSeconds < 60 {
		return errors.New("timeout_seconds must be at least 60")
	}
	return nil
}

func validRepo(repo string) bool {
	owner, name, ok := strings.Cut(repo, "/")
	return ok && owner != "" && name != "" && !strings.Contains(name, "/")
}
