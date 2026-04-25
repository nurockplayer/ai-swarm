# Worker Daemon Deployment

This guide installs and runs an AI Swarm worker that consumes MQTT tasks. Complete this file after [github-webhook-setup.md](./github-webhook-setup.md).

## Prerequisites

- Complete [hivemq-setup.md](./hivemq-setup.md), [cloudflare-deploy.md](./cloudflare-deploy.md), and [github-webhook-setup.md](./github-webhook-setup.md)
- Python 3.11+
- Git
- `uv`
- GitHub CLI (`gh`) authenticated for the same OS user that will run the worker
- Claude CLI installed for the same OS user that will run the worker
- The AI Swarm repository URL and a writable checkout directory
- The following values ready:
  - `mqtts://<YOUR_CLUSTER_ID>.hivemq.cloud:8883`
  - `<YOUR_MQTT_USERNAME>`
  - `<YOUR_MQTT_PASSWORD>`
  - `<YOUR_WORKER_ID>`

## Step-by-step

1. Install `uv` if it is not already available.

   Install guide: https://docs.astral.sh/uv/getting-started/installation/

   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. Verify the required CLIs for the worker user.

   ```bash
   python3 --version
   uv --version
   git --version
   gh auth status
   claude --version
   ```

3. Clone the repository into a stable path and install Python dependencies.

   ```bash
   git clone https://github.com/nurockplayer/ai-swarm.git ~/ai-swarm
   cd ~/ai-swarm/worker
   uv sync
   ```

4. Create a local environment file for the worker.

   ```bash
   mkdir -p ~/.ai-swarm
   cat > ~/.ai-swarm/.env <<'EOF'
   export AI_SWARM_MQTT_BROKER_URL='mqtts://<YOUR_CLUSTER_ID>.hivemq.cloud:8883'
   export AI_SWARM_MQTT_USERNAME='<YOUR_MQTT_USERNAME>'
   export AI_SWARM_MQTT_PASSWORD='<YOUR_MQTT_PASSWORD>'
   export AI_SWARM_WORKER_ID='<YOUR_WORKER_ID>'
   EOF
   ```

5. Load the worker environment into the current shell.

   ```bash
   set -a
   source ~/.ai-swarm/.env
   set +a
   ```

6. Start the worker in the foreground for the first boot.

   ```bash
   cd ~/ai-swarm/worker
   uv run worker start
   ```

7. In a second terminal, run the local pre-flight smoke test from the repo root.

   ```bash
   cd ~/ai-swarm
   set -a
   source ~/.ai-swarm/.env
   set +a
   ./scripts/smoke-test.sh
   ```

8. Optional: install the worker as a background service after the foreground test succeeds.

   macOS `launchd` example:

   ```xml
   <?xml version="1.0" encoding="UTF-8"?>
   <!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
     "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
   <plist version="1.0">
   <dict>
     <key>Label</key>
     <string>com.ai-swarm.worker</string>
     <key>ProgramArguments</key>
     <array>
       <string>/Users/<YOUR_MACOS_USER>/.local/bin/uv</string>
       <string>run</string>
       <string>worker</string>
       <string>start</string>
     </array>
     <key>WorkingDirectory</key>
     <string>/Users/<YOUR_MACOS_USER>/ai-swarm/worker</string>
     <key>EnvironmentVariables</key>
     <dict>
       <key>AI_SWARM_MQTT_BROKER_URL</key>
       <string>mqtts://<YOUR_CLUSTER_ID>.hivemq.cloud:8883</string>
       <key>AI_SWARM_MQTT_USERNAME</key>
       <string><YOUR_MQTT_USERNAME></string>
       <key>AI_SWARM_MQTT_PASSWORD</key>
       <string><YOUR_MQTT_PASSWORD></string>
       <key>AI_SWARM_WORKER_ID</key>
       <string><YOUR_WORKER_ID></string>
     </dict>
     <key>RunAtLoad</key>
     <true/>
     <key>KeepAlive</key>
     <true/>
     <key>StandardOutPath</key>
     <string>/tmp/ai-swarm-worker.log</string>
     <key>StandardErrorPath</key>
     <string>/tmp/ai-swarm-worker.err</string>
   </dict>
   </plist>
   ```

   Load it:

   ```bash
   launchctl unload ~/Library/LaunchAgents/com.ai-swarm.worker.plist 2>/dev/null || true
   launchctl load ~/Library/LaunchAgents/com.ai-swarm.worker.plist
   launchctl start com.ai-swarm.worker
   ```

   Linux `systemd` example:

   ```ini
   [Unit]
   Description=AI Swarm Worker
   After=network-online.target
   Wants=network-online.target

   [Service]
   Type=simple
   User=<YOUR_LINUX_USER>
   WorkingDirectory=/home/<YOUR_LINUX_USER>/ai-swarm/worker
   Environment=AI_SWARM_MQTT_BROKER_URL=mqtts://<YOUR_CLUSTER_ID>.hivemq.cloud:8883
   Environment=AI_SWARM_MQTT_USERNAME=<YOUR_MQTT_USERNAME>
   Environment=AI_SWARM_MQTT_PASSWORD=<YOUR_MQTT_PASSWORD>
   Environment=AI_SWARM_WORKER_ID=<YOUR_WORKER_ID>
   ExecStart=/home/<YOUR_LINUX_USER>/.local/bin/uv run worker start
   Restart=always
   RestartSec=5

   [Install]
   WantedBy=multi-user.target
   ```

   Enable it:

   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable ai-swarm-worker
   sudo systemctl start ai-swarm-worker
   ```

## Verification

1. The worker process starts without exiting immediately.

2. The worker log shows a successful broker connection, for example:

   ```json
   {"ts":"<YOUR_TIMESTAMP>","level":"INFO","msg":"connected to broker"}
   ```

3. `./scripts/smoke-test.sh` passes all local pre-flight checks.

4. After you label a GitHub issue with `ai-task`, the worker remains connected and is ready to consume the task.

## Troubleshooting

### MQTT Connection Failure

Cause: The worker cannot authenticate to HiveMQ or the broker URL is malformed.

Fix:

- Confirm `AI_SWARM_MQTT_BROKER_URL` is exactly `mqtts://<YOUR_CLUSTER_ID>.hivemq.cloud:8883`.
- Confirm `AI_SWARM_MQTT_USERNAME` and `AI_SWARM_MQTT_PASSWORD` match HiveMQ.
- Re-check HiveMQ ACLs for `tasks/#` and `workers/#`.

### `claude` or `gh` Not Found in Service Mode

Cause: The background service user does not inherit the same PATH as your interactive shell.

Fix:

- Run `gh auth status` and `claude --version` as the service user.
- Use absolute paths in `launchd` or `systemd`.
- Restart the service after updating the PATH or service file.

### Smoke Test Fails Before MQTT

Cause: The worker shell did not export environment variables, or dependencies were not installed.

Fix:

- Re-run `uv sync` inside `~/ai-swarm/worker`.
- Re-run `set -a; source ~/.ai-swarm/.env; set +a`.
- Re-run `./scripts/smoke-test.sh` from the repo root.
