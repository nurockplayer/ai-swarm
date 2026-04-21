export interface Env {
  GITHUB_WEBHOOK_SECRET: string;
  MQTT_BROKER_URL: string;
  MQTT_USERNAME: string;
  MQTT_PASSWORD: string;
  LOG_LEVEL: string;
}

export type TaskType = 'implementation' | 'review';
export type TaskPriority = 'low' | 'normal' | 'high';

export interface TaskRef {
  issue_number?: number | null;
  pr_number?: number | null;
  commit_sha?: string | null;
}

export interface Task {
  task_id: string;
  type: TaskType;
  source: 'github';
  repo: string;
  ref?: TaskRef;
  labels: string[];
  prompt: string;
  priority: TaskPriority;
  created_at: string;
  timeout_seconds: number;
}

export interface BuiltTask {
  task: Task;
  topic: string;
}
