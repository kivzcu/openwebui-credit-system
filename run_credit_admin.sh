#!/bin/bash
#
# Credit Admin Startup Script
#
# RECOMMENDED: Run behind nginx for TLS termination (more secure, easier to manage)
#   - Nginx handles HTTPS on port 443
#   - Credit Admin runs on port 8081 (plain HTTP)
#   - Nginx proxies https://chat-dev.kiv.zcu.cz/credits/* to http://127.0.0.1:8081/*
#
# Nginx is configured at: /etc/nginx/sites-enabled/chat-dev.kiv.zcu.cz.conf
#
# If you need the app to handle TLS directly (not recommended):
#   - Set APP_ENABLE_SSL=true before running this script
#   - Ensure SSL certs are accessible
#
cd credit_admin

export PYTHONPATH="/root/sources/openwebui-credit-system/credit_admin:$PYTHONPATH"

# export $(grep -v '^#' .env | xargs -d '\n')

# Prefer live Let's Encrypt certs if available, otherwise fall back to credit_admin/ssl
SSL_CERT=""
SSL_KEY=""

# If user specified a domain, use it
if [ -n "$LETSENCRYPT_DOMAIN" ]; then
	LIVE_DIR="/etc/letsencrypt/live/$LETSENCRYPT_DOMAIN"
	if [ -d "$LIVE_DIR" ]; then
		CAND_CERT="$LIVE_DIR/fullchain.pem"
		CAND_KEY="$LIVE_DIR/privkey.pem"
		if [ -f "$CAND_CERT" ] && [ -f "$CAND_KEY" ]; then
			SSL_CERT="$CAND_CERT"
			SSL_KEY="$CAND_KEY"
		fi
	fi
fi

# If no domain provided, auto-detect a single live cert dir if present
if [ -z "$SSL_CERT" ]; then
	if [ -d "/etc/letsencrypt/live" ]; then
		# count directories (excluding '.' and '..')
		dirs=(/etc/letsencrypt/live/*)
		if [ ${#dirs[@]} -eq 1 ] && [ -d "${dirs[0]}" ]; then
			AUTO_DOMAIN=$(basename "${dirs[0]}")
			CAND_CERT="/etc/letsencrypt/live/$AUTO_DOMAIN/fullchain.pem"
			CAND_KEY="/etc/letsencrypt/live/$AUTO_DOMAIN/privkey.pem"
			if [ -f "$CAND_CERT" ] && [ -f "$CAND_KEY" ]; then
				SSL_CERT="$CAND_CERT"
				SSL_KEY="$CAND_KEY"
			fi
		fi
	fi
fi

# Fallback to repo-local copy
if [ -z "$SSL_CERT" ] || [ -z "$SSL_KEY" ]; then
	LOCAL_CERT="$(pwd)/credit_admin/ssl/cert.pem"
	LOCAL_KEY="$(pwd)/credit_admin/ssl/key.pem"
	if [ -f "$LOCAL_CERT" ] && [ -f "$LOCAL_KEY" ]; then
		SSL_CERT="$LOCAL_CERT"
		SSL_KEY="$LOCAL_KEY"
	fi
fi

if [ -f "$SSL_CERT" ] && [ -f "$SSL_KEY" ]; then
	echo "Found SSL cert: $SSL_CERT"
	echo "Note: For production, run behind nginx for TLS termination (recommended)."
	if [ "${APP_ENABLE_SSL,,}" = "true" ] || [ "${APP_ENABLE_SSL}" = "1" ]; then
		echo "Enabling SSL for the app process (APP_ENABLE_SSL=true)"
		export ENABLE_SSL=true
		export SSL_CERT_PATH="$SSL_CERT"
		export SSL_KEY_PATH="$SSL_KEY"
	else
		echo "Starting Credit Admin without SSL; nginx will handle TLS (recommended)."
	fi
else
	echo "No SSL certs found - starting without HTTPS"
fi

# Run using uvx (resolve deps from `credit_admin/pyproject.toml`)
uv run --env-file .env python app/main.py
