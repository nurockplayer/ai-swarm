# Infra Deploy Playbook

This directory contains the deployment runbooks for bringing up AI Swarm in a fresh environment. Follow the files in this order for the main path:

1. [hivemq-setup.md](./hivemq-setup.md) - Create the MQTT broker, credentials, and ACLs.
2. [cloudflare-deploy.md](./cloudflare-deploy.md) - Deploy the `bridge/` Worker and store the HiveMQ credentials as Cloudflare secrets.
3. [github-webhook-setup.md](./github-webhook-setup.md) - Point a GitHub repository webhook at the deployed Worker.
4. [worker-deployment.md](./worker-deployment.md) - Install and start a worker that consumes MQTT tasks.

Optional:

- [tailscale-setup.md](./tailscale-setup.md) - Add private machine access or prepare for a future self-hosted MQTT broker.

## What each file covers

- `hivemq-setup.md`: broker provisioning, credentials, ACLs, and a broker smoke test
- `cloudflare-deploy.md`: Wrangler login, Worker secrets, deploy, and Worker URL capture
- `github-webhook-setup.md`: repository webhook creation, delivery checks, and redelivery
- `worker-deployment.md`: worker install, environment setup, foreground start, and local smoke test
- `tailscale-setup.md`: optional private networking for operators or future infrastructure changes

## Placeholder policy

All sample values in this directory must stay as placeholders. Use forms like:

- `<YOUR_CLUSTER_ID>`
- `<YOUR_MQTT_USERNAME>`
- `<YOUR_MQTT_PASSWORD>`
- `<YOUR_GITHUB_WEBHOOK_SECRET>`
- `https://<YOUR_WORKER_SUBDOMAIN>.workers.dev`

Broker URLs should always use this format:

```text
mqtts://<YOUR_CLUSTER_ID>.hivemq.cloud:8883
```
