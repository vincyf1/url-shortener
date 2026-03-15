# Contributing

Thanks for your interest in contributing to URL Shortener.

## Development setup

```bash
uv sync --dev
uv run python run.py
```

## Run tests

```bash
uv run python -m pytest -q
```

## Coding guidelines

- Keep changes focused and small.
- Add or update tests for behaviour changes.
- Prefer clear names and simple control flow.
- Avoid introducing new dependencies unless justified.

## Pull requests

Please include:

- What changed
- Why it changed
- How it was tested
- Any screenshots/GIFs for TUI changes

Before opening a PR, ensure:

- [ ] Tests pass locally
- [ ] Docs updated (if applicable)
- [ ] No secrets or local machine paths in commits
