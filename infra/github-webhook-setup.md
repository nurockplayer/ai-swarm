# GitHub Webhook Setup

This guide connects a target GitHub repository to the deployed Cloudflare Worker bridge. Complete this file after [cloudflare-deploy.md](./cloudflare-deploy.md), then continue with [worker-deployment.md](./worker-deployment.md).

## Prerequisites

- Complete [cloudflare-deploy.md](./cloudflare-deploy.md)
- Admin access to the target GitHub repository
- GitHub webhook docs:
  - Create a webhook: https://docs.github.com/en/webhooks/creating-webhooks
  - View deliveries: https://docs.github.com/webhooks/testing-and-troubleshooting-webhooks/viewing-webhook-deliveries
  - Redeliver deliveries: https://docs.github.com/enterprise-cloud@latest/webhooks/testing-and-troubleshooting-webhooks/redelivering-webhooks
- The following values ready:
  - `https://<YOUR_WORKER_SUBDOMAIN>.workers.dev`
  - `<YOUR_GITHUB_WEBHOOK_SECRET>`

## Step-by-step

1. Open the target repository on GitHub.

2. Go to `Settings` -> `Webhooks` -> `Add webhook`.

3. Fill `Payload URL` with the deployed Cloudflare Worker URL.

   ```text
   https://<YOUR_WORKER_SUBDOMAIN>.workers.dev
   ```

4. Set `Content type` to:

   ```text
   application/json
   ```

5. Paste the same webhook secret used in Cloudflare.

   ```text
   <YOUR_GITHUB_WEBHOOK_SECRET>
   ```

6. Under `Which events would you like to trigger this webhook?`, choose `Let me select individual events`.

7. Enable these events only:

   - `Issues`
   - `Pull requests`

8. Keep `Active` checked, then select `Add webhook`.

9. After the webhook is created, open it and inspect `Recent Deliveries`.

10. Confirm the initial `ping` delivery exists and returned a `2xx` response.

11. Trigger a real delivery by adding the `ai-task` label to a test issue in the same repository.

12. If the first delivery fails, use `Recent Deliveries` -> `Redeliver` after fixing the bridge secret or MQTT settings.

## Verification

1. The webhook entry is visible under `Settings` -> `Webhooks`.

2. `Recent Deliveries` contains a `ping` event with a `2xx` response.

3. A labeled issue generates an `issues` webhook delivery with a `2xx` response.

4. Continue to [worker-deployment.md](./worker-deployment.md) so a worker is available to consume the published MQTT tasks.

## Troubleshooting

### 401 Signature Mismatch

Cause: GitHub and Cloudflare are not using the same `GITHUB_WEBHOOK_SECRET` value.

Fix:

- Re-run `pnpm exec wrangler secret put GITHUB_WEBHOOK_SECRET` in `bridge/`.
- Update the GitHub webhook secret to the exact same value.
- Use `Redeliver` on the failed delivery.

### No Recent Deliveries

Cause: The webhook is inactive, the repository event did not match, or the webhook was added at the wrong scope.

Fix:

- Confirm `Active` is enabled.
- Confirm the webhook was created on the repository that receives the issue or PR activity.
- Confirm `Issues` and `Pull requests` are both selected.

### Delivery Is 2xx but No Task Reaches MQTT

Cause: The Worker accepted the webhook but could not publish to HiveMQ.

Fix:

- Re-check `MQTT_BROKER_URL`, `MQTT_USERNAME`, and `MQTT_PASSWORD` in Cloudflare.
- Re-check the HiveMQ ACLs for `tasks/#` and `workers/#`.
- Re-deploy the Worker, then redeliver the same webhook.
