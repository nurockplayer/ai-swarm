# GitHub Webhook Setup

This guide connects a GitHub repository to the AI Swarm Cloudflare Worker bridge.

The Payload URL comes from the deployed Cloudflare Worker. See [cloudflare-deploy.md](cloudflare-deploy.md) for deployment and URL discovery.

## Required Events

Select these webhook events:

- **Issues**
- **Pull requests**

Issues create implementation tasks. Pull request events create review or follow-up tasks when the routing labels match the AI Swarm configuration.

## Add the Webhook

1. Open the target GitHub repository.
2. Go to **Settings → Webhooks**.
3. Select **Add webhook**.
4. Fill in the fields below.
5. Select **Add webhook**.

## Field Reference

### Payload URL

Set this to the Cloudflare Worker URL, for example:

```text
https://ai-swarm-bridge.YOUR-SUBDOMAIN.workers.dev
```

Get this URL with:

```bash
cd bridge
wrangler deployments list
```

### Content Type

Select:

```text
application/json
```

The bridge expects JSON webhook payloads.

### Secret

Use the same value stored in the Cloudflare Worker secret:

```bash
cd bridge
wrangler secret put GITHUB_WEBHOOK_SECRET
```

Generate a strong secret with:

```bash
openssl rand -hex 32
```

GitHub signs webhook requests with this secret. The bridge rejects requests when the signature does not match.

### Events

Choose **Let me select individual events** and enable:

- **Issues**
- **Pull requests**

### Active

Keep **Active** checked. Inactive webhooks are saved but do not send deliveries.

## Test the Webhook

After creating the webhook:

1. Open **Settings → Webhooks**.
2. Select the AI Swarm webhook.
3. Open **Recent Deliveries**.
4. Confirm GitHub sent a `ping` delivery.
5. Select the delivery and inspect the response status.

Expected result:

- HTTP status is `2xx`.
- Response does not show a signature error.
- Cloudflare Worker logs show the request was received.

Create or update a test issue with the `ai-task` label to trigger an issue delivery.

## Redeliver for Testing

To retry a webhook delivery:

1. Open **Settings → Webhooks**.
2. Select the AI Swarm webhook.
3. Open **Recent Deliveries**.
4. Select a delivery.
5. Select **Redeliver**.

Use redelivery after changing Cloudflare secrets, MQTT credentials, or bridge code. It lets you test the same payload without creating another GitHub issue.

## Troubleshooting

### 401 Response

Cause: The GitHub webhook secret does not match `GITHUB_WEBHOOK_SECRET` in Cloudflare.

Fix: Update one side so both values are identical, then redeliver the failed delivery.

### No Deliveries

Cause: The webhook is inactive or the selected event type does not match the GitHub action.

Fix: Confirm **Active** is checked and **Issues** plus **Pull requests** are selected.

### MQTT Task Not Published

Cause: The webhook reached Cloudflare, but bridge MQTT configuration failed.

Fix: Check Cloudflare Worker logs and verify `MQTT_BROKER_URL`, `MQTT_USERNAME`, `MQTT_PASSWORD`, and HiveMQ ACLs.
