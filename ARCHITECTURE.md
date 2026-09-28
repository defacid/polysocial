# Architecture

Polysocial is a local-first Python service with a dependency-free browser interface.

- `server.py` serves the allowlisted UI and JSON API.
- `polysocial/storage.py` owns SQLite posts, connection display state, and delivery receipts.
- `polysocial/vault.py` encrypts API credentials using a machine-local Fernet key.
- `polysocial/worker.py` finds due deliveries and publishes them independently.
- Platform modules contain OAuth and publishing clients.
- `polysocial/backup.py` creates consistent SQLite snapshots and verifies or restores archives.

## Delivery state

`queued → publishing → delivered` is the successful path. Transient failures move to `retry` with bounded exponential backoff. After five attempts a delivery becomes `failed`. A process interrupted while `publishing` is conservatively changed to `failed`; Polysocial cannot know whether the remote platform accepted the request, so only the operator can retry it.

Posts are JSON payloads keyed by a stable local ID. Media is stored as private
per-post files and hydrated only at the API boundary; legacy inline media is
migrated automatically. Each selected platform has its own delivery row and
remote receipt. Editing a post never changes an already delivered row.

## Trust boundaries

The main interface is intended for localhost or an authenticated reverse proxy. Signed `/api/media/*` URLs are the only intentionally public resources and expire quickly. Credentials and databases live outside the checkout under the configured data directory.
