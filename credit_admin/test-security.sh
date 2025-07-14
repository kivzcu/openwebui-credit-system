#!/bin/bash

echo "🧪 OpenWebUI Credit System Security Test"
echo "========================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test configuration
BASE_URL="https://localhost:8000"
API_BASE_URL="$BASE_URL/api/credits"

echo "Testing security configuration..."

# Test 1: Health check (public endpoint)
echo -n "1. Testing health check (public): "
if curl -s -k "$BASE_URL/health" | grep -q "healthy"; then
    echo -e "${GREEN}PASS${NC}"
else
    echo -e "${RED}FAIL${NC}"
fi

# Test 2: Admin endpoints without auth (should fail)
echo -n "2. Testing admin endpoint without auth: "
if curl -s -k "$API_BASE_URL/users" | grep -q "401"; then
    echo -e "${GREEN}PASS${NC} (correctly blocked)"
else
    echo -e "${RED}FAIL${NC} (should require auth)"
fi

# Test 3: Extension endpoints without API key (should fail)
echo -n "3. Testing extension endpoint without API key: "
if curl -s -k "$API_BASE_URL/user/test" | grep -q "401"; then
    echo -e "${GREEN}PASS${NC} (correctly blocked)"
else
    echo -e "${RED}FAIL${NC} (should require API key)"
fi

# Test 4: SSL configuration
echo -n "4. Testing SSL configuration: "
if curl -s -k -I "$BASE_URL" | grep -q "200 OK"; then
    echo -e "${GREEN}PASS${NC}"
else
    echo -e "${RED}FAIL${NC}"
fi

# Test 5: Login endpoint exists
echo -n "5. Testing login endpoint: "
if curl -s -k "$BASE_URL/auth/login" -X POST | grep -q "detail"; then
    echo -e "${GREEN}PASS${NC}"
else
    echo -e "${RED}FAIL${NC}"
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
echo "CREDITS_API_PROTOCOL=https"
echo "CREDITS_API_HOST=localhost:8000"
echo "CREDITS_API_SSL_VERIFY=false"
echo "CREDITS_API_KEY=\$CREDITS_API_KEY"
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
