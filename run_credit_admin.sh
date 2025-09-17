#!/bin/bash

export PYTHONPATH="/root/sources/openwebui-credit-system/credit_admin:$PYTHONPATH"

export $(grep -v '^#' .env | xargs -d '\n')

cd credit_admin

# Run using uvx (resolve deps from `credit_admin/pyproject.toml`)
uv run python app/main.py
