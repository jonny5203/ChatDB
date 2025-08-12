# CRUSH.md

Project: Flask app with pytest. Uses Pipenv (Python 3.11).

Build/run
- pipenv install --dev
- pipenv run python main.py
- pipenv run gunicorn -w 2 -b 0.0.0.0:8080 main:app

Test
- pipenv run pytest -q
- Single test file: pipenv run pytest -q tests/test_main.py
- Single test node: pipenv run pytest -q tests/test_main.py::test_health
- Verbose + last-failed: pipenv run pytest -q -k "health" --lf -vv

Lint/format (recommended)
- pipenv run python -m pip install ruff==0.5.7 black==24.8.0
- Lint: pipenv run ruff check .
- Fix: pipenv run ruff check . --fix
- Format: pipenv run black .

Code style
- Imports: stdlib, third-party, local; no wildcard imports; explicit from ... import. Keep unused imports out (ruff F401).
- Formatting: Black defaults; 88 cols; trailing commas where Black applies.
- Types: prefer type hints on public functions; from __future__ import annotations if needed; mypy optional.
- Naming: snake_case for functions/vars, PascalCase for classes, UPPER_CASE for constants; test names describe behavior.
- Errors: raise HTTP errors via Flask idioms; avoid bare except; log or return JSON where applicable.
- Tests: pytest fixtures in conftest.py when shared; use client for Flask endpoints; keep assertions precise.

K8s/Docker
- Docker builds from Dockerfile; k8s manifests in k8s/ directory.

Notes
- No Cursor/Copilot rules present.
