#!/bin/bash

export PYTHONPATH="/root/sources/openwebui-credit-system/credit_admin:$PYTHONPATH"

credit_admin/venv/bin/python3 credit_admin/app/main.py
