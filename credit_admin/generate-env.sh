#!/bin/bash

# Generate secure .env file for Credit Admin System

set -e  # Exit on any error

ENV_FILE=".env"
BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🔑 Generating secure environment configuration for Credit Admin..."

# Check if .env already exists
if [ -f "$ENV_FILE" ]; then
    echo "⚠️  .env file already exists. Backing up to .env.backup"
    cp "$ENV_FILE" "${ENV_FILE}.backup"
    rm "$ENV_FILE"
fi

# Generate secure keys
SECRET_KEY=$(openssl rand -hex 32)
CREDITS_API_KEY=$(openssl rand -hex 32)

# Default admin password - CHANGE THIS IN PRODUCTION!
ADMIN_PASSWORD="admin123"
ADMIN_USERNAME="admin"

# Other defaults
PORT=8000
ENABLE_SSL=false
OPENWEBUI_DATABASE_PATH="/root/.open-webui/webui.db"
ACCESS_TOKEN_EXPIRE_MINUTES=30
CREDITS_API_PROTOCOL="http"
CREDITS_API_HOST="localhost:8000"
CREDITS_API_SSL_VERIFY="false"

# Write to .env
cat > "$ENV_FILE" << EOF
# Credit Admin Environment Configuration
# Generated on $(date)
# ⚠️ CHANGE DEFAULT PASSWORD AND KEYS BEFORE PRODUCTION!

# Application
PORT=$PORT
ENABLE_SSL=$ENABLE_SSL

# Security
ADMIN_USERNAME=$ADMIN_USERNAME
ADMIN_PASSWORD=$ADMIN_PASSWORD
SECRET_KEY=$SECRET_KEY
CREDITS_API_KEY=$CREDITS_API_KEY
ACCESS_TOKEN_EXPIRE_MINUTES=$ACCESS_TOKEN_EXPIRE_MINUTES

# Database
OPENWEBUI_DATABASE_PATH=$OPENWEBUI_DATABASE_PATH

# Extensions (for OpenWebUI setup - copy these to your OpenWebUI .env)
# CREDITS_API_PROTOCOL=$CREDITS_API_PROTOCOL
# CREDITS_API_HOST=$CREDITS_API_HOST
# CREDITS_API_SSL_VERIFY=$CREDITS_API_SSL_VERIFY
# CREDITS_API_KEY=$CREDITS_API_KEY
EOF

chmod 600 "$ENV_FILE"

echo "✅ .env file generated successfully at $ENV_FILE with 600 permissions"
echo ""
echo "🔐 Generated Keys (masked for security):"
echo "   SECRET_KEY: ${SECRET_KEY:0:8}...${SECRET_KEY: -8}"
echo "   CREDITS_API_KEY: ${CREDITS_API_KEY:0:8}...${CREDITS_API_KEY: -8}"
echo ""
echo "👤 Admin Credentials:"
echo "   Username: $ADMIN_USERNAME"
echo "   Password: $ADMIN_PASSWORD"
echo ""
echo "📝 Next steps:"
echo "1. Review and edit $ENV_FILE if needed (e.g., change ADMIN_PASSWORD)"
echo "2. For OpenWebUI extensions, set these in Valves:"
echo "   CREDITS_API_PROTOCOL=$CREDITS_API_PROTOCOL"
echo "   CREDITS_API_HOST=$CREDITS_API_HOST"
echo "   CREDITS_API_SSL_VERIFY=$CREDITS_API_SSL_VERIFY"
echo "   CREDITS_API_KEY=$CREDITS_API_KEY"
echo "3. Run: chmod +x generate-env.sh (if needed)"
echo "4. To view full config: source .env && cat .env | grep -E '^(SECRET_KEY|CREDITS_API_KEY)'"
echo ""
echo "⚠️  Add .env to .gitignore to avoid committing secrets!"