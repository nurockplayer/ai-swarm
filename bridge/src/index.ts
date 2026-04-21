import { connect, type IClientOptions, type MqttClient } from 'mqtt';
import type { BuiltTask, Env, Task, TaskType } from './types';

type JsonObject = Record<string, unknown>;

interface RepositoryPayload {
  name: string;
  full_name?: string;
  owner: {
    login: string;
  };
}

interface IssuePayload {
  number: number;
  title: string;
  body?: string | null;
}

interface PullRequestPayload {
  number: number;
  title: string;
  head?: {
    sha?: string | null;
  };
}

interface GitHubIssueLabeledPayload {
  action: string;
  label?: {
    name?: string;
  };
  repository: RepositoryPayload;
  issue: IssuePayload;
}

interface GitHubPullRequestPayload {
  action: string;
  repository: RepositoryPayload;
  pull_request: PullRequestPayload;
}

const SIGNATURE_PREFIX = 'sha256=';
const DEFAULT_TIMEOUT_SECONDS = 3600;

function isObject(value: unknown): value is JsonObject {
  return typeof value === 'object' && value !== null;
}

function hasRepository(value: JsonObject): value is JsonObject & { repository: RepositoryPayload } {
  const repository = value.repository;

  return (
    isObject(repository) &&
    typeof repository.name === 'string' &&
    isObject(repository.owner) &&
    typeof repository.owner.login === 'string'
  );
}

function isIssueLabeledPayload(value: unknown): value is GitHubIssueLabeledPayload {
  if (!isObject(value) || !hasRepository(value)) {
    return false;
  }

  const issue = value.issue;

  return (
    value.action === 'labeled' &&
    isObject(issue) &&
    typeof issue.number === 'number' &&
    typeof issue.title === 'string'
  );
}

function isPullRequestOpenedPayload(value: unknown): value is GitHubPullRequestPayload {
  if (!isObject(value) || !hasRepository(value)) {
    return false;
  }

  const pullRequest = value.pull_request;

  return (
    value.action === 'opened' &&
    isObject(pullRequest) &&
    typeof pullRequest.number === 'number' &&
    typeof pullRequest.title === 'string'
  );
}

function bytesToHex(bytes: ArrayBuffer): string {
  return [...new Uint8Array(bytes)]
    .map((byte) => byte.toString(16).padStart(2, '0'))
    .join('');
}

function constantTimeEquals(left: string, right: string): boolean {
  if (left.length !== right.length) {
    return false;
  }

  let difference = 0;
  for (let index = 0; index < left.length; index += 1) {
    difference |= left.charCodeAt(index) ^ right.charCodeAt(index);
  }

  return difference === 0;
}

function repositoryFullName(repository: RepositoryPayload): string {
  return repository.full_name ?? `${repository.owner.login}/${repository.name}`;
}

function createTaskId(
  owner: string,
  repo: string,
  kind: 'issue' | 'pr',
  number: number,
  taskType: 'impl' | 'review',
  timestamp: number,
): string {
  return `${owner}-${repo}-${kind}-${number}-${taskType}-${timestamp}`;
}

function baseTask(
  taskId: string,
  type: TaskType,
  repository: RepositoryPayload,
  prompt: string,
  createdAt: Date,
): Omit<Task, 'ref' | 'labels'> {
  return {
    task_id: taskId,
    type,
    source: 'github',
    repo: repositoryFullName(repository),
    prompt,
    priority: 'normal',
    created_at: createdAt.toISOString(),
    timeout_seconds: DEFAULT_TIMEOUT_SECONDS,
  };
}

export async function verifySignature(
  body: string,
  signature: string | null,
  secret: string,
): Promise<boolean> {
  if (!signature?.startsWith(SIGNATURE_PREFIX) || secret.length === 0) {
    return false;
  }

  const providedDigest = signature.slice(SIGNATURE_PREFIX.length).toLowerCase();
  if (!/^[0-9a-f]{64}$/.test(providedDigest)) {
    return false;
  }

  const encoder = new TextEncoder();
  const key = await crypto.subtle.importKey(
    'raw',
    encoder.encode(secret),
    { name: 'HMAC', hash: 'SHA-256' },
    false,
    ['sign'],
  );
  const digest = await crypto.subtle.sign('HMAC', key, encoder.encode(body));
  const expectedDigest = bytesToHex(digest);

  return constantTimeEquals(expectedDigest, providedDigest);
}

export function buildTask(event: string, payload: unknown): BuiltTask | null {
  const createdAt = new Date();
  const timestamp = createdAt.getTime();

  if (event === 'issues' && isIssueLabeledPayload(payload)) {
    if (payload.label?.name !== 'ai-task') {
      return null;
    }

    const owner = payload.repository.owner.login;
    const repo = payload.repository.name;
    const taskId = createTaskId(owner, repo, 'issue', payload.issue.number, 'impl', timestamp);
    const body = payload.issue.body ?? '';
    const task: Task = {
      ...baseTask(taskId, 'implementation', payload.repository, `${payload.issue.title}\n\n${body}`, createdAt),
      ref: {
        issue_number: payload.issue.number,
        pr_number: null,
        commit_sha: null,
      },
      labels: ['ai-task'],
    };

    return {
      task,
      topic: `tasks/impl/${repo}`,
    };
  }

  if (event === 'pull_request' && isPullRequestOpenedPayload(payload)) {
    const owner = payload.repository.owner.login;
    const repo = payload.repository.name;
    const pr = payload.pull_request;
    const taskId = createTaskId(owner, repo, 'pr', pr.number, 'review', timestamp);
    const task: Task = {
      ...baseTask(taskId, 'review', payload.repository, `Review PR #${pr.number}: ${pr.title}`, createdAt),
      ref: {
        issue_number: null,
        pr_number: pr.number,
        commit_sha: pr.head?.sha ?? null,
      },
      labels: [],
    };

    return {
      task,
      topic: `tasks/review/${repo}`,
    };
  }

  return null;
}

export async function publishTask(task: Task, topic: string, env: Env): Promise<void> {
  const options: IClientOptions = {
    username: env.MQTT_USERNAME,
    password: env.MQTT_PASSWORD,
    protocol: 'wss',
    reconnectPeriod: 0,
    connectTimeout: 10_000,
    clean: true,
  };
  const client = connect(env.MQTT_BROKER_URL, options);

  await new Promise<void>((resolve, reject) => {
    const cleanup = (): void => {
      client.removeListener('connect', onConnect);
      client.removeListener('error', onError);
    };
    const onError = (error: Error): void => {
      cleanup();
      reject(error);
    };
    const onConnect = (): void => {
      cleanup();
      resolve();
    };

    client.once('connect', onConnect);
    client.once('error', onError);
  });

  try {
    await publishWithQoS(client, topic, JSON.stringify(task));
  } finally {
    await endClient(client);
  }
}

function publishWithQoS(client: MqttClient, topic: string, message: string): Promise<void> {
  return new Promise((resolve, reject) => {
    client.publish(topic, message, { qos: 1 }, (error?: Error) => {
      if (error) {
        reject(error);
        return;
      }

      resolve();
    });
  });
}

function endClient(client: MqttClient): Promise<void> {
  return new Promise((resolve) => {
    client.end(false, {}, () => {
      resolve();
    });
  });
}

function jsonResponse(body: JsonObject, status: number): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      'content-type': 'application/json',
    },
  });
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    if (request.method !== 'POST') {
      return jsonResponse({ error: 'method_not_allowed' }, 405);
    }

    const body = await request.text();
    const signature = request.headers.get('x-hub-signature-256');
    const isValid = await verifySignature(body, signature, env.GITHUB_WEBHOOK_SECRET);
    if (!isValid) {
      return jsonResponse({ error: 'invalid_signature' }, 401);
    }

    let payload: unknown;
    try {
      payload = JSON.parse(body);
    } catch {
      return jsonResponse({ error: 'invalid_json' }, 400);
    }

    const event = request.headers.get('x-github-event') ?? '';
    const builtTask = buildTask(event, payload);
    if (builtTask === null) {
      return jsonResponse({ status: 'ignored' }, 202);
    }

    await publishTask(builtTask.task, builtTask.topic, env);

    return jsonResponse(
      {
        status: 'published',
        topic: builtTask.topic,
        task_id: builtTask.task.task_id,
      },
      202,
    );
  },
};
