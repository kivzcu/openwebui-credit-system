#!/bin/bash

# Load .env if it exists
if [ -f ".env" ]; then
    source .env
    echo "✅ Loaded configuration from .env"
else
    echo "⚠️  .env file not found. Please run ./generate-env.sh first."
    exit 1
fi

echo "🔐 Security Configuration Summary"
echo "================================="
echo ""
echo "Admin Interface:"
echo "  URL: http://localhost:8000 (or https if SSL enabled)"
echo "  Username: $ADMIN_USERNAME"
echo "  Password: $(echo $ADMIN_PASSWORD | sed 's/./*/g') (length: ${#ADMIN_PASSWORD})"
echo ""
echo "Extension API Key:"
echo "  Variable: CREDITS_API_KEY"
echo "  Value: ${CREDITS_API_KEY:0:8}...${CREDITS_API_KEY: -8} (length: ${#CREDITS_API_KEY})"
echo ""
echo "JWT Secret Key:"
echo "  SECRET_KEY: ${SECRET_KEY:0:8}...${SECRET_KEY: -8} (length: ${#SECRET_KEY})"
echo ""
echo "Other Configuration:"
echo "  Port: $PORT"
echo "  SSL Enabled: $ENABLE_SSL"
echo "  OpenWebUI DB Path: $OPENWEBUI_DATABASE_PATH"
echo "  Token Expiry: $ACCESS_TOKEN_EXPIRE_MINUTES minutes"
echo ""
echo "For OpenWebUI Extensions (set these in OpenWebUI environment):"
echo "-------------------------------------------------------------"
echo "CREDITS_API_PROTOCOL=$CREDITS_API_PROTOCOL"
echo "CREDITS_API_HOST=$CREDITS_API_HOST"
echo "CREDITS_API_SSL_VERIFY=$CREDITS_API_SSL_VERIFY"
echo "CREDITS_API_KEY=$CREDITS_API_KEY"
echo ""
echo "⚠️  IMPORTANT: Change default passwords and keys before production!"
echo "   The .env file is ignored by git (.gitignore)."
echo ""
echo "To regenerate: ./generate-env.sh"
