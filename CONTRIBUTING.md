# Contributing

## Before you start

- Check existing issues. Your problem might already be tracked.
- Small, focused PRs. One fix per PR. Don't refactor the world.
- If it's a big change, open an issue first to discuss.

## Setup

```bash
sudo pacman -S gtk4 gtk4-layer-shell gobject-introspection cairo portaudio wtype wl-clipboard

python -m venv .venv && source .venv/bin/activate
pip install -e .
pip install ruff
```

## Code style

Ruff handles it. CI will reject anything that doesn't pass:

```bash
ruff check .
ruff format --check .
```

Run `ruff format .` before committing and save yourself the round trip.

## Submitting a PR

1. Fork and branch from `main`
2. Make your changes
3. Run the linter
4. Open a PR with a clear description of what and why
5. Wait — this is a one-person project, patience appreciated

## Bugs

File an issue. Include:
- What you did
- What happened
- What you expected
- Distro, compositor, Python version

## Feature requests

Open an issue. Keep it concrete. "It would be nice if..." is fine, but don't expect everything to land. This tool is intentionally minimal.
