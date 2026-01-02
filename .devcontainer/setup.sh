#!/bin/bash
set -e

echo "==> Installing Python dependencies..."
uv sync --all-extras

echo "==> Installing pre-commit hooks..."
uv run pre-commit install || true

echo "==> Installing frontend dependencies..."
cd /workspace/frontend && npm install

echo "==> Setup complete!"
