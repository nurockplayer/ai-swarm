# Worker Daemon Deployment

This guide installs and runs an AI Swarm worker daemon on a developer machine or server.

## Prerequisites

- Python 3.11+
- uv
- GitHub CLI (`gh`) logged in
- Claude CLI logged in
- Git

Install uv:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Verify GitHub authentication:

```bash
gh auth status
```

Verify Claude CLI authentication:

```bash
claude --version
```

## Installation

```bash
git clone https://github.com/nurockplayer/ai-swarm.git
cd ai-swarm/worker
uv sync
```

## Config Setup

```bash
mkdir -p ~/.ai-swarm
cat > ~/.ai-swarm/.env << 'EOF'
AI_SWARM_MQTT_BROKER_URL=mqtts://YOUR-CLUSTER.hivemq.cloud:8883
AI_SWARM_MQTT_USERNAME=your-username
AI_SWARM_MQTT_PASSWORD=your-password
AI_SWARM_WORKER_ID=my-laptop-worker
EOF
source ~/.ai-swarm/.env
```

## Start

```bash
cd ai-swarm/worker
uv run worker start
```

## macOS launchd

Create `~/Library/LaunchAgents/com.ai-swarm.worker.plist`:

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
    <string>/Users/YOUR-USER/.local/bin/uv</string>
    <string>run</string>
    <string>worker</string>
    <string>start</string>
  </array>
  <key>WorkingDirectory</key>
  <string>/Users/YOUR-USER/ai-swarm/worker</string>
  <key>EnvironmentVariables</key>
  <dict>
    <key>AI_SWARM_MQTT_BROKER_URL</key>
    <string>mqtts://YOUR-CLUSTER.hivemq.cloud:8883</string>
    <key>AI_SWARM_MQTT_USERNAME</key>
    <string>your-username</string>
    <key>AI_SWARM_MQTT_PASSWORD</key>
    <string>your-password</string>
    <key>AI_SWARM_WORKER_ID</key>
    <string>my-laptop-worker</string>
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

Load and start it:

```bash
launchctl load ~/Library/LaunchAgents/com.ai-swarm.worker.plist
launchctl start com.ai-swarm.worker
```

## Linux systemd

Create `/etc/systemd/system/ai-swarm-worker.service`:

```ini
[Unit]
Description=AI Swarm Worker
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=ai-swarm
WorkingDirectory=/home/ai-swarm/ai-swarm/worker
Environment=AI_SWARM_MQTT_BROKER_URL=mqtts://YOUR-CLUSTER.hivemq.cloud:8883
Environment=AI_SWARM_MQTT_USERNAME=your-username
Environment=AI_SWARM_MQTT_PASSWORD=your-password
Environment=AI_SWARM_WORKER_ID=linux-worker-1
ExecStart=/home/ai-swarm/.local/bin/uv run worker start
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable and start it:

```bash
sudo systemctl daemon-reload
sudo systemctl enable ai-swarm-worker
sudo systemctl start ai-swarm-worker
```

## Verification

Expected worker log line:

```json
{"ts":"...","level":"INFO","msg":"connected to broker"}
```

Confirm:

- HiveMQ dashboard shows the worker client online.
- `gh auth status` succeeds for the worker user.
- `claude --version` works for the worker user.
- From the repo root, `./scripts/smoke-test.sh` passes.

## Troubleshooting

### MQTT Connection Failure

Check that `AI_SWARM_MQTT_BROKER_URL` uses `mqtts://` and port `8883`, and that username and password match HiveMQ credentials.

If HiveMQ rejects the connection, confirm the credential is enabled and ACLs allow `tasks/#` and `workers/#`.

### claude CLI Not Found

Check the service user PATH:

```bash
which claude
claude --version
```

For launchd or systemd, use absolute paths or add the CLI install directory to the service environment.

### Git Worktree Failure

Confirm the worker has:

- Write access to its checkout and temporary workspace directory.
- Git installed and available in PATH.
- A clean clone with access to the target GitHub repository.
- `gh auth status` passing for the same OS user that runs the worker.
