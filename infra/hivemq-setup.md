# HiveMQ Cloud Setup

This guide creates a HiveMQ Cloud MQTT broker for AI Swarm. The MVP uses HiveMQ Cloud directly, so worker machines do not need public inbound networking.

## Create an Account

1. Open https://www.hivemq.com/mqtt-cloud/.
2. Create or sign in to a HiveMQ Cloud account.
3. Select the **Serverless** free plan.

## Create a Cluster

1. In HiveMQ Cloud, create a new Serverless cluster.
2. Select the preferred cloud region.
3. Wait for the cluster status to become ready.
4. Copy the cluster URL.

The URL format is:

```text
{cluster-id}.s1.{region}.hivemq.cloud
```

Use port `8883` with TLS for MQTT clients.

## Create Credentials

1. Open the cluster.
2. Go to **Access Management**.
3. Open **Credentials**.
4. Create a new username and password for AI Swarm.
5. Store the password securely. It will be used by both the Cloudflare bridge and worker daemon.

## Configure ACLs

In **Access Management**, configure ACL permissions for the AI Swarm credential.

Allow subscribe and publish access to:

```text
tasks/#
workers/#
```

Required permissions:

| Topic filter | Subscribe | Publish |
|---|---:|---:|
| `tasks/#` | Yes | Yes |
| `workers/#` | Yes | Yes |

## Test with mosquitto

Replace `YOUR-CLUSTER`, `YOUR-USERNAME`, and `YOUR-PASSWORD` with the HiveMQ values.

Subscribe in one terminal:

```bash
mosquitto_sub \
  -h YOUR-CLUSTER.s1.YOUR-REGION.hivemq.cloud \
  -p 8883 \
  -u YOUR-USERNAME \
  -P YOUR-PASSWORD \
  --cafile /etc/ssl/cert.pem \
  -t 'tasks/#'
```

Publish in another terminal:

```bash
mosquitto_pub \
  -h YOUR-CLUSTER.s1.YOUR-REGION.hivemq.cloud \
  -p 8883 \
  -u YOUR-USERNAME \
  -P YOUR-PASSWORD \
  --cafile /etc/ssl/cert.pem \
  -t 'tasks/impl/test-repo' \
  -m '{"task_id":"smoke-test","kind":"impl"}'
```

The subscriber should receive the JSON message.

## Environment Variables

Export these variables before running the worker:

```bash
export AI_SWARM_MQTT_BROKER_URL='mqtts://YOUR-CLUSTER.s1.YOUR-REGION.hivemq.cloud:8883'
export AI_SWARM_MQTT_USERNAME='YOUR-USERNAME'
export AI_SWARM_MQTT_PASSWORD='YOUR-PASSWORD'
```

Use equivalent Cloudflare Worker secrets for the bridge:

- `MQTT_BROKER_URL`
- `MQTT_USERNAME`
- `MQTT_PASSWORD`

## Troubleshooting

### Connection Refused

Cause: Username or password is incorrect, disabled, or not assigned to the cluster.

Fix:

- Recreate the credential in **Access Management → Credentials**.
- Confirm the exact username and password are used by the worker and bridge.
- Confirm the broker hostname and port are correct.

### TLS Errors

Cause: The client cannot find a CA certificate bundle or is connecting without TLS.

Fix:

- Use port `8883`.
- Use `mqtts://` in application configuration.
- For `mosquitto_sub` and `mosquitto_pub`, pass `--cafile /etc/ssl/cert.pem`.
- On systems without `/etc/ssl/cert.pem`, use the platform CA bundle path.

### ACL Denied

Cause: The credential does not have topic permissions for the requested publish or subscribe.

Fix:

- Confirm ACLs include `tasks/#` with subscribe and publish.
- Confirm ACLs include `workers/#` with subscribe and publish.
- Retry the `mosquitto_sub` and `mosquitto_pub` test commands.
