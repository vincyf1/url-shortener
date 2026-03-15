# Release Checklist

## Pre-release

- [ ] `uv sync --dev`
- [ ] `uv run python -m pytest -q`
- [ ] Review open issues/PRs for blockers
- [ ] Confirm README and docs reflect current behaviour
- [ ] Confirm LICENSE and .github files are present

## Security and hygiene

- [ ] No secrets committed
- [ ] No local absolute paths in docs/config
- [ ] `.env` and local DB files are ignored

## Tag and publish

- [ ] Create release notes (highlights + breaking changes)
- [ ] Tag version
- [ ] Publish GitHub release
