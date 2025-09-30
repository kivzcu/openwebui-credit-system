#!/bin/bash
cd credit_admin

export PYTHONPATH="/root/sources/openwebui-credit-system/credit_admin:$PYTHONPATH"

# export $(grep -v '^#' .env | xargs -d '\n')

# Run using uvx (resolve deps from `credit_admin/pyproject.toml`)
uv run --env-file .env python app/main.py
