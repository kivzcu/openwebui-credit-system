#!/bin/bash

export PYTHONPATH="/root/sources/openwebui-credit-system/credit_admin:$PYTHONPATH"


CREDIT_DATABASE_URL=postgresql://openwebui_user:rMKJQrxIZQC3uofJbM5Q@localhost:5432/credit_system_db credit_admin/venv/bin/python3 credit_admin/app/main.py
