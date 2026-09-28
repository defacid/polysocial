# Changelog

All notable changes are documented here. Polysocial follows Semantic Versioning.

## 0.1.0 — 2026-09-28

- Publish to Facebook Pages, Instagram, Threads, and Bluesky.
- Schedule posts locally with independent delivery receipts and retries.
- Encrypt connected-account credentials at rest.
- Validate image attachments and support per-image alt text.
- Recover interrupted deliveries without automatically creating duplicates.
- Add per-connection health checks and Threads token refresh.
- Move attached images out of SQLite into private per-post files, with automatic migration.
- Add verified backups, restore tooling, daily backup timers, and database checks.
- Bind to localhost by default, add optional HTTP authentication, and harden HTTP and systemd security.
- Add Docker Compose, service upgrade/uninstall documentation, CI, and contributor templates.
