# Contributing to CorvusTunnel

Thanks for your interest in CorvusTunnel. It is a free, open-source, non-profit
project, and contributions of every kind are welcome: bug fixes, features,
documentation, tests, and ideas. This guide covers how to get set up and what we
expect from a change.

## Before you begin

### Contributor License Agreement

By opening a pull request you agree to the
[Contributor License Agreement](https://corvustunnel.com/landing/cla.html). In short:

- You keep ownership of your contributions.
- You grant KALAI a license to use your code under the MIT License.
- You confirm the work is your own, or that you have permission to submit it.

Your first pull request counts as acceptance of the CLA.

### Requirements

- Python 3.10 or newer
- Git
- Node.js (only if you are working on the web UI in `frontend/`)

## Getting set up

```bash
git clone https://github.com/maliozturk/CorvusTunnel.git
cd CorvusTunnel

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -e ".[dev]"
```

Run it locally:

```bash
AGENT_TOKEN=dev-token corvustunnel start --verbose
```

## Making a change

1. Branch from `master` with a descriptive name, for example
   `fix/websocket-reconnect` or `feature/custom-relay-url`.
2. Make your change, with tests where it makes sense.
3. Run the tests and the linter (see below). Both must be clean.
4. Commit and open a pull request against `maliozturk/CorvusTunnel` with a clear
   description of what changed and why.

We use [Conventional Commits](https://www.conventionalcommits.org/) for commit
messages: `feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`.

## Tests and linting

```bash
python -m pytest                 # run the suite
python -m pytest --cov=corvustunnel

ruff check .                     # lint
ruff check . --fix               # auto-fix what it can
ruff format .                    # format
```

All tests must pass and `ruff check .` must report no problems before a change is
merged.

## Code style

Configuration lives in [`pyproject.toml`](pyproject.toml). The essentials:

- Lines are at most 100 characters.
- Double quotes.
- Type hints everywhere; we target Python 3.10+.
- Imports are sorted by ruff.

CorvusTunnel keeps source files free of inline comments and docstrings. Instead,
every file starts with a single header banner that names the file and describes
its purpose in a line or two, and the code below is written to be readable on its
own through clear names and small functions. When you add a file, copy the banner
from a neighboring file and write a short, honest `Description`:

```python
# /*--------------------------------*- py -*-----------------------------*\
# |     __                                                               |
# |   <(o )___    CorvusTunnel                                           |
# |    ( ._> /    control AI agents from any device                      |
# |     `---'     self-hosted · E2E encrypted · MIT                      |
# *----------------------------------------------------------------------*/
# File:        corvustunnel/example.py
# Description: One or two lines on what this module is for.
# \*---------------------------------------------------------------------*/

from __future__ import annotations
```

If a piece of logic feels like it needs an explanatory comment, prefer a clearer
name or a small helper function instead.

## Project layout

```
corvustunnel/
├── cli.py            command-line entry point: servers, relay, the QR code
├── boot.py           renders the QR code in the terminal
├── version.py        single source of the version string
├── apps/             FastAPI apps: public (8000) and internal (8001)
├── auth/             boot/session tokens, IP binding, WebSocket tickets
├── crypto/           end-to-end encryption (X25519 + NaCl Box)
├── executor/         the PTY session that runs the agent
├── routers/          HTTP and WebSocket route handlers
├── middleware/       client-IP trust, IP bans, rate limits, security headers
├── audit/            audit and forensic logging
├── config/           settings loaded from the environment
├── history/          reads past Claude / Codex / Antigravity sessions
└── static/           the built web UI
frontend/             web UI source (Svelte + Vite)
tests/                test suite
```

The web UI is built with `npm install && npm run build` inside `frontend/`, which
writes the bundle into `corvustunnel/static/`.

## Reporting bugs

Open an issue at
[github.com/maliozturk/CorvusTunnel/issues](https://github.com/maliozturk/CorvusTunnel/issues).
Please include your Python version, operating system, the CorvusTunnel version,
and clear steps to reproduce.

## Security issues

Do not open public issues for security vulnerabilities. Email
admin@kalai-tech.com privately instead.

## Links

- Website: [corvustunnel.com](https://corvustunnel.com)
- Maintained by: [kalai-tech.com](https://kalai-tech.com)
- Contact: admin@kalai-tech.com
