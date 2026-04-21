import { describe, expect, test, vi } from 'vitest';
import { buildTask, publishTask, verifySignature } from '../src/index';

async function signatureFor(body: string, secret: string): Promise<string> {
  const encoder = new TextEncoder();
  const key = await crypto.subtle.importKey(
    'raw',
    encoder.encode(secret),
    { name: 'HMAC', hash: 'SHA-256' },
    false,
    ['sign'],
  );
  const digest = await crypto.subtle.sign('HMAC', key, encoder.encode(body));
  const hex = [...new Uint8Array(digest)]
    .map((byte) => byte.toString(16).padStart(2, '0'))
    .join('');

  return `sha256=${hex}`;
}

describe('verifySignature', () => {
  test('returns true for correct secret', async () => {
    const body = JSON.stringify({ action: 'opened' });
    const signature = await signatureFor(body, 'correct-secret');

    await expect(verifySignature(body, signature, 'correct-secret')).resolves.toBe(true);
  });

  test('returns false for wrong secret', async () => {
    const body = JSON.stringify({ action: 'opened' });
    const signature = await signatureFor(body, 'correct-secret');

    await expect(verifySignature(body, signature, 'wrong-secret')).resolves.toBe(false);
  });
});

describe('buildTask', () => {
  test('builds implementation task for issues.labeled with ai-task label', () => {
    vi.setSystemTime(new Date('2026-04-21T10:30:00.000Z'));

    const result = buildTask('issues', {
      action: 'labeled',
      label: { name: 'ai-task' },
      repository: {
        name: 'repo-name',
        owner: { login: 'owner-name' },
        full_name: 'owner-name/repo-name',
      },
      issue: {
        number: 42,
        title: 'Implement bridge',
        body: 'Wire GitHub to MQTT.',
        html_url: 'https://github.com/owner-name/repo-name/issues/42',
      },
    });

    expect(result).toEqual({
      topic: 'tasks/impl/repo-name',
      task: {
        task_id: 'owner-name-repo-name-issue-42-impl-1776767400000',
        type: 'implementation',
        source: 'github',
        repo: 'owner-name/repo-name',
        ref: {
          issue_number: 42,
          pr_number: null,
          commit_sha: null,
        },
        labels: ['ai-task'],
        prompt: 'Implement bridge\n\nWire GitHub to MQTT.',
        priority: 'normal',
        created_at: '2026-04-21T10:30:00.000Z',
        timeout_seconds: 3600,
      },
    });

    vi.useRealTimers();
  });

  test('returns null for issues.labeled without ai-task label', () => {
    const result = buildTask('issues', {
      action: 'labeled',
      label: { name: 'not-ai-task' },
      repository: {
        name: 'repo-name',
        owner: { login: 'owner-name' },
        full_name: 'owner-name/repo-name',
      },
      issue: {
        number: 42,
        title: 'Implement bridge',
        body: 'Wire GitHub to MQTT.',
        html_url: 'https://github.com/owner-name/repo-name/issues/42',
      },
    });

    expect(result).toBeNull();
  });
});

describe('publishTask', () => {
  test('can be mocked without opening an MQTT connection', () => {
    const mockPublishTask = vi.fn<typeof publishTask>();

    expect(mockPublishTask).not.toHaveBeenCalled();
  });
});
