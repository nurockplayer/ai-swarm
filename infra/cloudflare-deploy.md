# Cloudflare Worker Deployment

This guide deploys the AI Swarm bridge as a Cloudflare Worker. The bridge receives GitHub webhook events and publishes tasks to MQTT.

## Prerequisites

- Node.js 18+
- pnpm
- A Cloudflare account with Wrangler access
- A HiveMQ Cloud broker URL, username, and password
- A GitHub webhook secret

Install Wrangler globally:

```bash
pnpm add -g wrangler
```

Log in to Cloudflare:

```bash
wrangler login
```

## Configure Secrets

Generate a webhook secret:

```bash
openssl rand -hex 32
```

From the `bridge/` directory, add the required secrets:

```bash
cd bridge
wrangler secret put GITHUB_WEBHOOK_SECRET
wrangler secret put MQTT_BROKER_URL
wrangler secret put MQTT_USERNAME
wrangler secret put MQTT_PASSWORD
```

Use the same `GITHUB_WEBHOOK_SECRET` value later when configuring the GitHub webhook.

Use the MQTT broker URL format expected by the bridge, for example:

```text
mqtts://YOUR-CLUSTER.s1.YOUR-REGION.hivemq.cloud:8883
```

## Deploy

Deploy the Worker from the `bridge/` directory:

```bash
pnpm deploy
```

List deployments and copy the Worker URL:

```bash
wrangler deployments list
```

The deployed URL should look like:

```text
https://ai-swarm-bridge.YOUR-SUBDOMAIN.workers.dev
```

## GitHub Webhook Setup

In the target GitHub repository:

1. Open **Settings**.
2. Open **Webhooks**.
3. Select **Add webhook**.
4. Set **Payload URL** to the Cloudflare Worker URL.
5. Set **Content type** to `application/json`.
6. Set **Secret** to the same value stored in `GITHUB_WEBHOOK_SECRET`.
7. Under **Which events would you like to trigger this webhook?**, select **Let me select individual events**.
8. Enable **Issues** and **Pull requests**.
9. Keep **Active** checked.
10. Select **Add webhook**.

See [github-webhook-setup.md](github-webhook-setup.md) for detailed webhook testing and redelivery steps.

## Troubleshooting

### 401 Signature Mismatch

Cause: GitHub and Cloudflare Worker are using different webhook secret values.

Fix:

- Re-run `wrangler secret put GITHUB_WEBHOOK_SECRET` in `bridge/`.
- Paste the exact same secret into the GitHub webhook **Secret** field.
- Redeliver a recent GitHub webhook delivery.

### MQTT Publish Failure

Cause: Broker URL, credentials, or ACLs are incorrect.

Fix:

- Confirm `MQTT_BROKER_URL` uses `mqtts://` and port `8883`.
- Confirm the hostname matches the HiveMQ cluster URL.
- Confirm `MQTT_USERNAME` and `MQTT_PASSWORD` match HiveMQ Access Management credentials.
- Confirm HiveMQ ACLs allow publish access to `tasks/#` and `workers/#`.
