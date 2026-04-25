# HiveMQ Cloud Setup

This guide creates the managed MQTT broker used by AI Swarm. Complete this file first, then continue with [cloudflare-deploy.md](./cloudflare-deploy.md).

## Prerequisites

- A HiveMQ Cloud account: https://console.hivemq.cloud/
- A local shell with `openssl`
- Optional MQTT CLI tools for verification:
  - mosquitto clients install guide: https://mosquitto.org/download/
  - Homebrew example: `brew install mosquitto`
  - Ubuntu example: `sudo apt-get update && sudo apt-get install -y mosquitto-clients`
- A secure place to store these placeholders after you create them:
  - `mqtts://<YOUR_CLUSTER_ID>.hivemq.cloud:8883`
  - `<YOUR_MQTT_USERNAME>`
  - `<YOUR_MQTT_PASSWORD>`

## Step-by-step

1. Open the HiveMQ Cloud console.

   URL: https://console.hivemq.cloud/

2. Sign in, then create a Serverless cluster.

   Product guide: https://docs.hivemq.com/hivemq-cloud/quick-start-guide.html

3. In the cluster creation flow, choose a region and wait until the cluster status is ready.

4. Open the new cluster and copy the broker hostname.

   Save it in this format:

   ```text
   mqtts://<YOUR_CLUSTER_ID>.hivemq.cloud:8883
   ```

5. Create a dedicated username and password for AI Swarm.

   In the HiveMQ console, open `Manage Cluster` -> `Access Management` -> `Credentials`, then create:

   ```text
   Username: <YOUR_MQTT_USERNAME>
   Password: <YOUR_MQTT_PASSWORD>
   ```

6. Configure ACLs for that credential.

   In `Access Management`, allow both publish and subscribe on:

   ```text
   tasks/#
   workers/#
   ```

   Minimum ACL table:

   | Topic filter | Subscribe | Publish |
   |---|---:|---:|
   | `tasks/#` | Yes | Yes |
   | `workers/#` | Yes | Yes |

7. Export the values locally so you can reuse them in the next guides.

   ```bash
   export AI_SWARM_MQTT_BROKER_URL='mqtts://<YOUR_CLUSTER_ID>.hivemq.cloud:8883'
   export AI_SWARM_MQTT_USERNAME='<YOUR_MQTT_USERNAME>'
   export AI_SWARM_MQTT_PASSWORD='<YOUR_MQTT_PASSWORD>'
   ```

8. If `mosquitto_sub` and `mosquitto_pub` are installed, run a broker smoke test.

   Terminal A:

   ```bash
   mosquitto_sub \
     -h <YOUR_CLUSTER_ID>.hivemq.cloud \
     -p 8883 \
     -u '<YOUR_MQTT_USERNAME>' \
     -P '<YOUR_MQTT_PASSWORD>' \
     --cafile /etc/ssl/cert.pem \
     -t 'tasks/#'
   ```

   Terminal B:

   ```bash
   mosquitto_pub \
     -h <YOUR_CLUSTER_ID>.hivemq.cloud \
     -p 8883 \
     -u '<YOUR_MQTT_USERNAME>' \
     -P '<YOUR_MQTT_PASSWORD>' \
     --cafile /etc/ssl/cert.pem \
     -t 'tasks/impl/smoke-test' \
     -m '{"task_id":"smoke-test","type":"implementation"}'
   ```

## Verification

1. Confirm the HiveMQ dashboard shows the cluster status as ready.

2. Confirm the broker, username, and password are recorded only as placeholders in docs or shell history:

   ```text
   mqtts://<YOUR_CLUSTER_ID>.hivemq.cloud:8883
   <YOUR_MQTT_USERNAME>
   <YOUR_MQTT_PASSWORD>
   ```

3. If you ran the `mosquitto` smoke test, Terminal A should receive the JSON payload published from Terminal B.

4. Continue to [cloudflare-deploy.md](./cloudflare-deploy.md) with the same three values.

## Troubleshooting

### Connection Refused

Cause: The username or password is wrong, disabled, or attached to a different cluster.

Fix:

- Recreate the credential in `Access Management` -> `Credentials`.
- Re-export `AI_SWARM_MQTT_USERNAME` and `AI_SWARM_MQTT_PASSWORD`.
- Re-run the `mosquitto_sub` and `mosquitto_pub` commands.

### TLS or Certificate Error

Cause: The client is not using TLS, is using the wrong port, or cannot find a CA bundle.

Fix:

- Use port `8883` only.
- Use `mqtts://<YOUR_CLUSTER_ID>.hivemq.cloud:8883` in application config.
- Pass `--cafile /etc/ssl/cert.pem` to `mosquitto_*`.
- If `/etc/ssl/cert.pem` does not exist on your OS, use the platform CA bundle path instead.

### ACL Denied

Cause: The credential can connect but does not have topic permissions.

Fix:

- Confirm both publish and subscribe are enabled for `tasks/#`.
- Confirm both publish and subscribe are enabled for `workers/#`.
- Save ACL changes, then repeat the smoke test.
