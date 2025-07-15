#!/bin/bash

export PYTHONPATH="$(pwd)/credit_admin/"
export ENABLE_SSL="true"
export CREDITS_API_KEY="vY97Yvh6qKywm8xE-ErTGfUofV0t1BiZ36wR3lLNHIY"
export ADMIN_PASSWORD="cunicredit"

credit_admin/venv/bin/python3 credit_admin/app/main.py
