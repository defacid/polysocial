# Security

## Reporting a vulnerability

Please report security issues privately to the repository owner rather than
opening a public issue. Include reproduction steps and the affected version.

## Local data

Polysocial stores posts, attached media, OAuth tokens, app credentials, and
delivery receipts under `~/.local/share/polysocial/`. That directory must never be uploaded,
committed, backed up to a public location, or served as static content.

Credentials are encrypted at rest, but the encryption key is stored locally
so the unattended scheduler can publish after a restart. Filesystem permissions
and host security remain essential. The installer restricts `.local-data/` to
the service user.

The optional `/api/media/*` Cloudflare Access bypass is safe only because every
request requires a short-lived HMAC signature. Do not create broader public
bypass rules for the application.

Before making a repository public, run:

```bash
git status --ignored
git ls-files | grep -Ei '(\.env|\.vault|\.dpapi|sqlite|token|secret|\.pem|\.key)'
```

The second command should return no credential or runtime files. Source files
that merely contain variable names such as `access_token` are expected.
