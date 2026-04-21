# Tailscale Setup

Tailscale is optional for the MVP. HiveMQ Cloud does not require it because workers connect outbound to the managed MQTT broker over TLS.

Use Tailscale only if you want private machine-to-machine access now, or if you later self-host the MQTT broker.

## Install Tailscale

Install Tailscale on each worker machine:

```bash
curl -fsSL https://tailscale.com/install.sh | sh
```

On macOS, install from https://tailscale.com/download/mac or use Homebrew:

```bash
brew install --cask tailscale
```

## Create a Tailnet

1. Sign in at https://login.tailscale.com/.
2. Create a new tailnet or use an existing organization tailnet.
3. Confirm the admin console is accessible.

## Invite Worker Machines

On each worker machine, authenticate with the tailnet:

```bash
sudo tailscale up
```

For unattended servers, use an auth key from the Tailscale admin console:

```bash
sudo tailscale up --auth-key tskey-auth-REPLACE_ME
```

Confirm each worker appears in the Tailscale admin console.

## ACL Tag

Use the tag `tag:ai-worker` for worker machines.

In the Tailscale admin console:

1. Open **Access controls**.
2. Add `tag:ai-worker` to `tagOwners`.
3. Apply the tag to worker machines.

Example ACL fragment:

```json
{
  "tagOwners": {
    "tag:ai-worker": ["autogroup:admin"]
  },
  "acls": [
    {
      "action": "accept",
      "src": ["tag:ai-worker"],
      "dst": ["*:*"]
    }
  ]
}
```

Restrict `dst` further when you know the exact private services the workers need.

## Future Self-hosted MQTT

If AI Swarm later moves from HiveMQ Cloud to a self-hosted MQTT broker, place the broker inside the tailnet.

Recommended shape:

- Broker runs on a tailnet machine named `broker-machine`.
- Workers connect outbound through Tailscale.
- Broker URL becomes:

```text
mqtts://broker-machine:8883
```

Keep TLS enabled even inside the tailnet so credentials and messages are encrypted end to end.
