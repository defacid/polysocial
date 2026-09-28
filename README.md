# Polysocial

Polysocial is a responsive, accessible, local-first social publishing console.
Compose once, publish immediately or schedule locally, and track independent
delivery receipts for Facebook Pages, Instagram Professional accounts,
Threads, and Bluesky.

There are no Polysocial user accounts and no hosted Polysocial database. Posts,
media, schedules, tokens, and receipts stay on the computer running the app.

> **Project status:** early alpha. Use test accounts and review queued content.
> Social APIs and their approval requirements change frequently.

## Features

- Facebook Page text and multi-image posts
- Instagram image and carousel posts
- Threads text, image, carousel, and automatic long-text reply chains
- Bluesky images and automatic 300-character reply chains
- Multiple attachments with previews, removal, and drag-to-reorder
- Scheduled queue, calendars, delivery history, and per-platform receipts
- Encrypted local credential vault
- Responsive keyboard-accessible interface
- Locally vendored Font Awesome icons

## Requirements

- Python 3.11 or newer
- `pip`
- A browser with JavaScript enabled
- API applications/credentials for the services you connect
- Optional: systemd, curl, Cloudflare Tunnel, and Cloudflare Access for a
  persistent HTTPS installation

## Quick start

```bash
git clone https://github.com/YOUR-ACCOUNT/polysocial.git
cd polysocial
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -r requirements.txt
python3 server.py --port 5500
```

Open `http://127.0.0.1:5500`. Use **Settings** to connect accounts. Runtime
state is created under `~/.local/share/polysocial/`, outside the checkout.

Scheduling is local: the Python service must remain running when a post becomes
due. Closing the browser does not stop an installed service.

## Platform setup

### Bluesky

Create an app password in Bluesky settings, then enter the handle and app
password in Polysocial. If Bluesky emails a sign-in code, enter it when prompted.

### Facebook and Instagram

Create your own Meta developer app and configure Facebook Login for Business.
The configuration needs Page discovery/read/publishing permissions and Instagram
content publishing permissions. Add this exact callback URL in Meta, replacing
the hostname with your own public origin:

```text
https://social.example.com/api/oauth/meta/callback
```

Facebook publishing targets Pages, not normal personal timelines. Instagram
must be a Professional account linked to the selected Facebook Page. The UI
asks for your App ID, Login for Business Configuration ID, and App Secret; the
secret is encrypted locally.

### Threads

Enable the Threads API use case in your Meta app and add:

```text
https://social.example.com/api/oauth/threads/callback
```

The Threads account must be an app tester while the app remains in development,
unless Meta has approved the necessary production access.

## Persistent local service

Copy and edit the installation example:

```bash
cp install.env.example install.env
```

Then install the systemd service:

```bash
sudo ./deploy/install-services.sh
```

The installer discovers the checkout path and current user; it does not assume
a particular home directory. It also locks down local data permissions.

## Optional Cloudflare Tunnel

Download `cloudflared` to `.local-tools/cloudflared`, make it executable, and
create `~/.local/share/polysocial/cloudflared/tunnel.env` containing only:

```text
CLOUDFLARE_TUNNEL_TOKEN=replace-with-your-token
```

Set the file to mode `600`, then rerun the installer. Configure the tunnel's
public hostname to forward to `http://127.0.0.1:5500`.

Protect the main hostname with Cloudflare Access. Meta must fetch attached
media from the internet, so create a second, more-specific Access application:

- Application path: `social.example.com/api/media/*`
- Policy action: **Bypass**
- Include: **Everyone**

Only that path is public, and the origin accepts requests only when they contain
a short-lived cryptographic signature. Never bypass Access for the whole app.

## Local storage and privacy

- Posts and delivery state: `~/.local/share/polysocial/posts.sqlite3`
- Encrypted credentials: `~/.local/share/polysocial/credentials/`
- Optional tunnel token: `~/.local/share/polysocial/cloudflared/tunnel.env`

The credential encryption key is intentionally local so scheduled publishing
can continue unattended. Encryption does not make these files safe to publish.
Keep the entire data directory private and backed up only to a secure
location.

## Testing

```bash
python3 -m unittest discover -s tests -v
node --check app.js
node --check overrides.js
```

## Limitations

- Only image attachments are fully implemented across every platform.
- Meta requires publicly fetchable, HTTPS media URLs for Instagram and Threads.
- A local power/network outage can delay scheduled posts.
- Platform limits, app-review rules, and available permissions can change.
- Delivery is at-least-once during ambiguous network failures; always inspect
  history before manually retrying a post.

## License

Polysocial source code is released under the [MIT License](LICENSE). Third-party
components are documented in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
The DEFACID name and logo identify the original project and are not an
endorsement of modified distributions.

## Security

Read [SECURITY.md](SECURITY.md) before exposing Polysocial beyond localhost or
making a fork public.
