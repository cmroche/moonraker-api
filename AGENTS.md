# Repository Guidelines

## Project Structure & Module Organization

This repository packages an async Python client for the Moonraker websocket API.
Core library code lives in `moonraker_api/`, with the public client in
`moonraker_api/moonrakerclient.py`, constants in `moonraker_api/const.py`, and
websocket internals in `moonraker_api/websockets/`. Tests live in `tests/`;
shared aiohttp service helpers are in `tests/common.py`, fixtures in
`tests/conftest.py`, and sample payloads in `tests/data.py`. Packaging metadata is
split between `setup.py`, `setup.cfg`, `requirements*.txt`, and release tooling in
`package.json` plus `.releaserc`.

## Build, Test, and Development Commands

Create a local environment before changing code:

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt
```

Run the test suite with the repository pytest defaults:

```bash
pytest
```

Match CI coverage output when needed:

```bash
pytest --cov-report=xml --cov=moonraker_api tests/
```

Run CI-style lint checks:

```bash
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
flake8 . --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics
```

Install Node dependencies only for release tooling: `npm ci` requires Node 24+.

## Coding Style & Naming Conventions

Use Python 3.10+ features only; CI tests 3.10 through 3.14. Follow existing
module style: four-space indentation, type hints on public async methods, and
descriptive exception classes such as `ClientNotConnectedError`. Keep websocket
state constants uppercase in `const.py`. Name tests `test_<behavior>` and keep
fixtures small and explicit.

## Testing Guidelines

Tests use `pytest`, `pytest-asyncio`, and `pytest-aiohttp`; `asyncio_mode = auto`
is configured in `setup.cfg`. Add or update async tests for websocket connection,
request, notification, and error-path changes. Prefer the existing aiohttp fake
Moonraker services in `tests/common.py` over live network calls.

## Commit & Pull Request Guidelines

This project uses semantic-release with the Angular conventional commit preset.
Use commit types such as `feat:`, `fix:`, `deps:`, and `chore:`; breaking changes
use `feat!:` or a `BREAKING CHANGE:` footer. Pull requests should describe the
behavioral change, include linked issues when available, and note test commands
run locally. For API changes, update `README.md` examples and add coverage.

## Security & Configuration Tips

Do not commit API keys, printer hostnames, or local virtual environments. Use
test fixtures and mocks for credentials. Keep generated files such as
`coverage.xml`, `.coverage`, and `__pycache__/` out of commits unless explicitly
required by a release process.
