# Contributing

Thank you for improving Polysocial. Please open an issue before a large change so API, migration, and interface decisions can be discussed first.

## Development

1. Create a Python 3.11+ virtual environment.
2. Install `requirements.txt`.
3. Run `python server.py` and open `http://127.0.0.1:5500`.
4. Use test social accounts. Never commit tokens, databases, `install.env`, or runtime data.

Before opening a pull request, run:

```bash
python -m unittest discover -s tests -v
node --check app.js
node --check overrides.js
bash -n deploy/*.sh run-cloudflared.sh
```

Pull requests that change stored data must include a backward-compatible migration and recovery test. Publishing changes must account for ambiguous network failures and avoid automatic duplicate posts.

By contributing, you agree that your contribution is licensed under the MIT License.
