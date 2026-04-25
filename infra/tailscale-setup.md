# Tailscale Setup

Tailscale is optional for the current MVP because workers connect outbound to HiveMQ Cloud over TLS. Use this guide if you want private operator access to worker machines now, or if you plan to move MQTT to a self-hosted broker later.

## Prerequisites

- A Tailscale account: https://login.tailscale.com/
- Tailscale install docs:
  - Linux: https://tailscale.com/docs/install/linux
  - macOS: https://tailscale.com/download/mac
- Auth key docs: https://tailscale.com/docs/features/access-control/auth-keys
- A machine that will run the AI Swarm worker
- Optional placeholder if you use unattended setup:
  - `<YOUR_TAILSCALE_AUTH_KEY>`

## Step-by-step

1. Create or sign in to a tailnet.

   Admin console:

   ```text
   https://login.tailscale.com/admin
   ```

2. Install Tailscale on the worker machine.

   Ubuntu or Debian:

   ```bash
   curl -fsSL https://tailscale.com/install.sh | sh
   ```

   macOS with Homebrew:

   ```bash
   brew install --cask tailscale
   ```

3. Start the Tailscale client on the worker machine.

   Linux:

   ```bash
   sudo tailscale up
   ```

   For unattended servers, use an auth key instead:

   ```bash
   sudo tailscale up --auth-key='<YOUR_TAILSCALE_AUTH_KEY>'
   ```

4. In the Tailscale admin console, confirm the worker machine appears in the machine list.

5. Create a worker tag policy if you want to separate AI Swarm nodes from personal devices.

   Open `Access controls`, then add a policy fragment like this:

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

6. Apply the `tag:ai-worker` tag to AI Swarm worker machines if your tailnet policy requires it.

7. If you later self-host MQTT inside Tailscale, update the broker value used by AI Swarm to the internal hostname instead of HiveMQ Cloud.

   Example future format:

   ```text
   mqtts://<YOUR_TAILNET_BROKER_HOST>:8883
   ```

## Verification

1. The worker machine shows as connected in the Tailscale admin console.

2. `tailscale status` lists the machine and shows an assigned tailnet IP.

   ```bash
   tailscale status
   ```

3. If you use tagging, the machine shows the `tag:ai-worker` tag in the admin console.

4. If you do not need private operator access, you can skip this file and continue with [worker-deployment.md](./worker-deployment.md).

## Troubleshooting

### `tailscale up` Requires Browser Login on a Headless Server

Cause: Interactive login was used on a machine without a browser session.

Fix:

- Generate an auth key in the Tailscale admin console.
- Re-run `sudo tailscale up --auth-key='<YOUR_TAILSCALE_AUTH_KEY>'`.
- Revoke the key after provisioning if it is one-off.

### Machine Appears but Cannot Reach Other Tailnet Nodes

Cause: ACLs or tag policies block traffic.

Fix:

- Review the policy in `Access controls`.
- Confirm the node has the expected tag, such as `tag:ai-worker`.
- Temporarily broaden the ACL rule to verify policy is the blocker, then tighten it again.

### Auth Key Rejected

Cause: The auth key expired, was revoked, or was pasted incorrectly.

Fix:

- Generate a new auth key.
- Copy it again as `<YOUR_TAILSCALE_AUTH_KEY>`.
- Re-run `sudo tailscale up --auth-key='<YOUR_TAILSCALE_AUTH_KEY>'`.
