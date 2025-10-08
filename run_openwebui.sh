#!/bin/bash
#
# OpenWebUI Startup Script
#
# This script reads PostgreSQL configuration from credit_admin/.env
# and constructs the DATABASE_URL for OpenWebUI.
#
# For HTTPS access, use nginx as a reverse proxy (recommended setup):
#   - Nginx listens on ports 80/443 and handles TLS
#   - OpenWebUI runs on port 8080 (plain HTTP, default)
#   - Nginx proxies HTTPS requests to http://127.0.0.1:8080
#

ENV_FILE="credit_admin/.env"

if [ ! -f "$ENV_FILE" ]; then
	echo "Error: $ENV_FILE not found"
	exit 1
fi

# Read PostgreSQL configuration from .env
echo "Reading database configuration from $ENV_FILE..."

# Source the .env file to get the variables
set -a
source "$ENV_FILE"
set +a

# Construct DATABASE_URL for OpenWebUI
# Format: postgresql://user:password@host:port/database
if [ -n "$DB_USER" ] && [ -n "$DB_PASSWORD" ] && [ -n "$DB_HOST" ] && [ -n "$DB_PORT" ] && [ -n "$DB_NAME" ]; then
	export DATABASE_URL="postgresql://${DB_USER}:${DB_PASSWORD}@${DB_HOST}:${DB_PORT}/${DB_NAME}"
	echo "Database URL configured: postgresql://${DB_USER}:***@${DB_HOST}:${DB_PORT}/${DB_NAME}"
else
	echo "Warning: PostgreSQL configuration incomplete in $ENV_FILE"
	echo "OpenWebUI will use default SQLite database"
fi

# Start OpenWebUI
echo "Starting OpenWebUI..."
DATA_DIR=~/.open-webui uvx --python 3.11 --with itsdangerous 'open-webui[postgres]@latest' serve
