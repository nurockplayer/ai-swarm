# Cloudflare Worker Deployment

This guide deploys the `bridge/` service to Cloudflare Workers. It consumes GitHub webhooks and publishes tasks to HiveMQ. Complete this file after [hivemq-setup.md](./hivemq-setup.md), then continue with [github-webhook-setup.md](./github-webhook-setup.md).

## Prerequisites

- Complete [hivemq-setup.md](./hivemq-setup.md)
- A Cloudflare account: https://dash.cloudflare.com/
- Node.js and pnpm installed
- Wrangler install/update guide: https://developers.cloudflare.com/workers/wrangler/install-and-update/
- Cloudflare Workers CLI docs: https://developers.cloudflare.com/workers/wrangler/
- The following values ready:
  - `mqtts://<YOUR_CLUSTER_ID>.hivemq.cloud:8883`
  - `<YOUR_MQTT_USERNAME>`
  - `<YOUR_MQTT_PASSWORD>`
  - `<YOUR_GITHUB_WEBHOOK_SECRET>`

## Step-by-step

1. Open the repo root and install the bridge dependencies.

   ```bash
   cd bridge
   pnpm install
   ```

2. Authenticate Wrangler with Cloudflare.

   Login docs: https://developers.cloudflare.com/workers/wrangler/commands/#login

   ```bash
   pnpm exec wrangler login
   ```

3. Generate a webhook secret that will also be used in GitHub.

   ```bash
   openssl rand -hex 32
   ```

   Save the output as:

   ```text
   <YOUR_GITHUB_WEBHOOK_SECRET>
   ```

4. Set the Worker secret for the GitHub webhook signature.

   Secret docs: https://developers.cloudflare.com/workers/configuration/secrets/

   ```bash
   cd bridge
   pnpm exec wrangler secret put GITHUB_WEBHOOK_SECRET
   ```

   When prompted, paste:

   ```text
   <YOUR_GITHUB_WEBHOOK_SECRET>
   ```

5. Set the MQTT broker URL secret.

   ```bash
   cd bridge
   pnpm exec wrangler secret put MQTT_BROKER_URL
   ```

   When prompted, paste:

   ```text
   mqtts://<YOUR_CLUSTER_ID>.hivemq.cloud:8883
   ```

6. Set the MQTT username secret.

   ```bash
   cd bridge
   pnpm exec wrangler secret put MQTT_USERNAME
   ```

   When prompted, paste:

   ```text
   <YOUR_MQTT_USERNAME>
   ```

7. Set the MQTT password secret.

   ```bash
   cd bridge
   pnpm exec wrangler secret put MQTT_PASSWORD
   ```

   When prompted, paste:

   ```text
   <YOUR_MQTT_PASSWORD>
   ```

8. Deploy the Worker.

   ```bash
   cd bridge
   pnpm deploy
   ```

9. List deployments and copy the generated Worker URL.

   ```bash
   cd bridge
   pnpm exec wrangler deployments list
   ```

   Record it as:

   ```text
   https://<YOUR_WORKER_SUBDOMAIN>.workers.dev
   ```

## Verification

1. Confirm `pnpm deploy` finishes successfully and prints a deployed Worker name.

2. Confirm `pnpm exec wrangler deployments list` shows the latest deployment.

3. Save the Worker URL as:

   ```text
   https://<YOUR_WORKER_SUBDOMAIN>.workers.dev
   ```

4. Continue to [github-webhook-setup.md](./github-webhook-setup.md) with:

   - `https://<YOUR_WORKER_SUBDOMAIN>.workers.dev`
   - `<YOUR_GITHUB_WEBHOOK_SECRET>`

## Troubleshooting

### `wrangler login` Fails

Cause: The browser login flow did not complete or the wrong Cloudflare account was selected.

Fix:

- Re-run `pnpm exec wrangler login`.
- Confirm the browser session lands in the target Cloudflare account.
- Retry `pnpm exec wrangler deployments list` before deploying again.

### Secret Missing at Deploy Time

Cause: One or more required secrets were never created or were created in a different account.

Fix:

- Re-run `pnpm exec wrangler secret put GITHUB_WEBHOOK_SECRET`.
- Re-run `pnpm exec wrangler secret put MQTT_BROKER_URL`.
- Re-run `pnpm exec wrangler secret put MQTT_USERNAME`.
- Re-run `pnpm exec wrangler secret put MQTT_PASSWORD`.

### MQTT Publish Failure After Deploy

Cause: Cloudflare received the webhook, but the Worker cannot authenticate to HiveMQ.

Fix:

- Confirm `MQTT_BROKER_URL` is exactly `mqtts://<YOUR_CLUSTER_ID>.hivemq.cloud:8883`.
- Confirm `MQTT_USERNAME` and `MQTT_PASSWORD` match the HiveMQ credential.
- Re-check the ACLs from [hivemq-setup.md](./hivemq-setup.md).
