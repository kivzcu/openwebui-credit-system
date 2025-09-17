#!/bin/bash

echo "🧪 OpenWebUI Credit System Security Test"
echo "========================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Load .env if present to use same config as application
if [ -f ".env" ]; then
    # shellcheck disable=SC1091
    source .env
fi

# Test configuration (allow overrides from .env)
CREDITS_API_PROTOCOL="${CREDITS_API_PROTOCOL:-}"
CREDITS_API_HOST="${CREDITS_API_HOST:-}"

# If protocol not set, derive from ENABLE_SSL
if [ -z "$CREDITS_API_PROTOCOL" ]; then
    if [ "${ENABLE_SSL,,}" = "true" ] || [ "${ENABLE_SSL}" = "1" ]; then
        CREDITS_API_PROTOCOL="https"
    else
        CREDITS_API_PROTOCOL="http"
    fi
fi

# If CREDITS_API_HOST not set, use HOST:PORT fallback
if [ -z "$CREDITS_API_HOST" ]; then
    HOST_VAL="${HOST:-localhost}"
    PORT_VAL="${PORT:-8000}"
    CREDITS_API_HOST="$HOST_VAL:$PORT_VAL"
fi

BASE_URL="$CREDITS_API_PROTOCOL://$CREDITS_API_HOST"
API_BASE_URL="$BASE_URL/api/credits"

# Curl common options (show errors but silence progress)
CURLOPTS=(-sS -k --max-time 5)

PORT_VAL="${PORT:-8000}"
# Probe candidate URLs to find an actually reachable base URL (prefer explicit localhost:$PORT)
EFFECTIVE_BASE_URL=""
probe_candidates=(
    "$CREDITS_API_PROTOCOL://localhost:${PORT_VAL}/health"
    "$CREDITS_API_PROTOCOL://127.0.0.1:${PORT_VAL}/health"
    "$CREDITS_API_PROTOCOL://$CREDITS_API_HOST/health"
    "http://localhost:${PORT_VAL}/health"
    "http://127.0.0.1:${PORT_VAL}/health"
)

for c in "${probe_candidates[@]}"; do
    probe_resp=$(curl "${CURLOPTS[@]}" "$c" 2>&1)
    probe_code=$?
    if [ $probe_code -eq 0 ]; then
        EFFECTIVE_BASE_URL=$(echo "$c" | sed 's#/health$##')
        break
    fi
done

if [ -z "$EFFECTIVE_BASE_URL" ]; then
    echo "\n⚠️  Unable to reach any candidate base URL for the credit admin app.\n"
    REACHABLE=false
else
    REACHABLE=true
    BASE_URL="$EFFECTIVE_BASE_URL"
    API_BASE_URL="$BASE_URL/api/credits"
fi

echo "Testing security configuration..."

# Test 1: Health check (public endpoint)
echo -n "1. Testing health check (public): "
resp=$(curl "${CURLOPTS[@]}" "$BASE_URL/health" 2>&1)
code=$?
if [ $code -ne 0 ]; then
    echo -e "${RED}UNREACHABLE${NC} (curl error: ${resp})"
else
    if echo "$resp" | grep -q "healthy"; then
        echo -e "${GREEN}PASS${NC}"
    else
        echo -e "${RED}FAIL${NC} (unexpected response)"
    fi
fi

# Test 2: Admin endpoints without auth (should fail)
echo -n "2. Testing admin endpoint without auth: "
resp=$(curl "${CURLOPTS[@]}" -sS -k -o /dev/null -w '%{http_code}' "$API_BASE_URL/users" 2>&1)
code=$?
if [ $code -ne 0 ]; then
    echo -e "${RED}UNREACHABLE${NC} (curl error: ${resp})"
else
    status="$resp"
    if [ "$status" = "401" ] || [ "$status" = "403" ]; then
        echo -e "${GREEN}PASS${NC} (correctly blocked)"
    else
        echo -e "${RED}FAIL${NC} (expected 401/403, got ${status:-unknown})"
    fi
fi

# Test 3: Extension endpoints without API key (should fail)
echo -n "3. Testing extension endpoint without API key: "
resp=$(curl "${CURLOPTS[@]}" -sS -k -o /dev/null -w '%{http_code}' "$API_BASE_URL/user/test" 2>&1)
code=$?
if [ $code -ne 0 ]; then
    echo -e "${RED}UNREACHABLE${NC} (curl error: ${resp})"
else
    status="$resp"
    if [ "$status" = "401" ] || [ "$status" = "403" ]; then
        echo -e "${GREEN}PASS${NC} (correctly blocked)"
    else
        echo -e "${RED}FAIL${NC} (expected 401/403, got ${status:-unknown})"
    fi
fi

# Test 4: SSL configuration
echo -n "4. Testing SSL configuration: "
if [ "$CREDITS_API_PROTOCOL" != "https" ]; then
    echo -e "${YELLOW}SKIPPED${NC} (protocol not https)"
else
    resp=$(curl "${CURLOPTS[@]}" -I "$BASE_URL" 2>&1)
    code=$?
    if [ $code -ne 0 ]; then
        echo -e "${RED}UNREACHABLE${NC} (curl error: ${resp})"
    else
        if echo "$resp" | grep -q "HTTP/"; then
            echo -e "${GREEN}PASS${NC}"
        else
            echo -e "${RED}FAIL${NC} (no HTTP response)"
        fi
    fi
fi

# Test 5: Login endpoint exists
echo -n "5. Testing login endpoint: "
resp=$(curl "${CURLOPTS[@]}" -s -k "$BASE_URL/auth/login" -X POST 2>&1)
code=$?
if [ $code -ne 0 ]; then
    echo -e "${RED}UNREACHABLE${NC} (curl error: ${resp})"
else
    if echo "$resp" | grep -q "detail"; then
        echo -e "${GREEN}PASS${NC}"
    else
        echo -e "${RED}FAIL${NC} (unexpected response)"
    fi
fi

echo ""
echo "Security Configuration Summary:"
echo "------------------------------"

# Check environment variables
echo -n "Admin Username: "
if [ -n "$ADMIN_USERNAME" ]; then
    echo -e "${GREEN}$ADMIN_USERNAME${NC}"
else
    echo -e "${YELLOW}admin (default)${NC}"
fi

echo -n "Admin Password: "
if [ -n "$ADMIN_PASSWORD" ]; then
    if [ "$ADMIN_PASSWORD" = "admin123" ]; then
        echo -e "${RED}DEFAULT PASSWORD - CHANGE IMMEDIATELY!${NC}"
    else
        echo -e "${GREEN}Custom password set${NC}"
    fi
else
    echo -e "${RED}admin123 (default) - CHANGE IMMEDIATELY!${NC}"
fi

echo -n "Secret Key: "
if [ -n "$SECRET_KEY" ]; then
    echo -e "${GREEN}Set (${#SECRET_KEY} characters)${NC}"
else
    echo -e "${YELLOW}Auto-generated${NC}"
fi

echo -n "API Key: "
if [ -n "$CREDITS_API_KEY" ]; then
    echo -e "${GREEN}Set (${#CREDITS_API_KEY} characters)${NC}"
else
    echo -e "${YELLOW}Auto-generated${NC}"
fi

echo ""
echo "Extension Configuration:"
echo "----------------------"
echo "Set these in your OpenWebUI environment:"
echo ""
# Determine values to suggest for OpenWebUI
suggest_protocol="${CREDITS_API_PROTOCOL:-$([[ "${ENABLE_SSL,,}" = "true" ]] && echo https || echo http)}"

# Prefer explicit CREDITS_API_HOST if set; otherwise derive from BASE_URL or HOST:PORT
if [ -n "${CREDITS_API_HOST:-}" ]; then
    suggest_host="$CREDITS_API_HOST"
else
    # Use BASE_URL if it's been detected, otherwise fallback to HOST:PORT
    if [ -n "${BASE_URL:-}" ]; then
        # strip protocol
        suggest_host=$(echo "$BASE_URL" | sed -E 's#^https?://##')
    else
        host_val="${HOST:-localhost}"
        port_val="${PORT:-8000}"
        suggest_host="$host_val:$port_val"
    fi
fi

# SSL verify default (allow override)
suggest_ssl_verify="${CREDITS_API_SSL_VERIFY:-false}"

# Mask the API key for display if set
if [ -n "${CREDITS_API_KEY:-}" ]; then
    key="${CREDITS_API_KEY}"
    masked_key="${key:0:8}...${key: -8}"
else
    masked_key="(not set)"
fi

echo "CREDITS_API_PROTOCOL=${suggest_protocol}"
echo "CREDITS_API_HOST=${suggest_host}"
echo "CREDITS_API_SSL_VERIFY=${suggest_ssl_verify}"
echo "CREDITS_API_KEY=${masked_key}"
echo ""

if [ "$ADMIN_PASSWORD" = "admin123" ] || [ -z "$ADMIN_PASSWORD" ]; then
    echo -e "${RED}⚠️  SECURITY WARNING: Change default admin password!${NC}"
    echo "   Run: export ADMIN_PASSWORD='your_secure_password'"
fi

echo ""
echo "To start the secure application:"
echo "  ENABLE_SSL=true python app/main.py"
echo ""
echo "Access the admin interface at: $BASE_URL"
echo "Default login: admin / admin123 (change immediately!)"
