#!/bin/bash

echo "🔒 Security Vulnerability Fix Validation"
echo "========================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

BASE_URL="${1:-https://localhost:8000}"

echo -e "${BLUE}Testing security fixes for credential exposure vulnerability...${NC}"
echo ""

# Test 1: Check if security headers are present
echo -n "1. Testing security headers: "
HEADERS=$(curl -s -k -I "$BASE_URL" 2>/dev/null)
if [ $? -ne 0 ] || echo "$HEADERS" | grep -q "405 Method Not Allowed"; then
    # If HEAD fails, try GET with headers only
    HEADERS=$(curl -s -k --head "$BASE_URL" 2>/dev/null)
    if [ $? -ne 0 ]; then
        # If still fails, try GET and extract headers
        HEADERS=$(curl -s -k -D - -o /dev/null "$BASE_URL" 2>/dev/null)
    fi
fi

if echo "$HEADERS" | grep -qi "x-content-type-options\|x-frame-options\|x-xss-protection"; then
    echo -e "${GREEN}PASS${NC} (Security headers detected)"
else
    echo -e "${RED}FAIL${NC} (Missing security headers)"
    echo "    Headers received:"
    echo "$HEADERS" | grep -iE "^(x-|strict-transport)" | sed 's/^/    /'
fi

# Test 2: Check if main.js contains credential clearing function
echo -n "2. Testing client-side protection: "
if grep -q "clearCredentialsFromURL" credit_admin/app/static/main.js 2>/dev/null; then
    echo -e "${GREEN}PASS${NC} (Credential clearing function found)"
else
    echo -e "${RED}FAIL${NC} (Missing credential clearing function)"
fi

# Test 3: Check if SecurityMiddleware is implemented
echo -n "3. Testing server-side protection: "
if grep -q "SecurityMiddleware" credit_admin/app/main.py 2>/dev/null; then
    echo -e "${GREEN}PASS${NC} (Security middleware found)"
else
    echo -e "${RED}FAIL${NC} (Missing security middleware)"
fi

# Test 4: Check CSP header in HTML
echo -n "4. Testing Content Security Policy: "
if grep -q "Content-Security-Policy" credit_admin/app/static/index.html 2>/dev/null; then
    echo -e "${GREEN}PASS${NC} (CSP header found)"
else
    echo -e "${RED}FAIL${NC} (Missing CSP header)"
fi

# Test 5: Check if HTTPS is enabled (if SSL files exist)
echo -n "5. Testing HTTPS configuration: "
if [ -f "credit_admin/ssl/cert.pem" ] && [ -f "credit_admin/ssl/key.pem" ]; then
    echo -e "${GREEN}PASS${NC} (SSL certificates found)"
elif [ "$ENABLE_SSL" = "true" ]; then
    echo -e "${YELLOW}PARTIAL${NC} (SSL enabled but certificates may be missing)"
else
    echo -e "${YELLOW}WARNING${NC} (HTTPS not configured - consider enabling)"
fi

echo ""
echo -e "${BLUE}Security Configuration Check:${NC}"
echo "----------------------------"

# Check environment variables
echo -n "Admin Password: "
if [ -n "$ADMIN_PASSWORD" ] && [ "$ADMIN_PASSWORD" != "admin123" ]; then
    echo -e "${GREEN}Custom password set${NC}"
elif [ "$ADMIN_PASSWORD" = "admin123" ]; then
    echo -e "${RED}DEFAULT PASSWORD - CHANGE IMMEDIATELY!${NC}"
else
    echo -e "${YELLOW}Using default (admin123) - CHANGE IMMEDIATELY!${NC}"
fi

echo -n "Secret Key: "
if [ -n "$SECRET_KEY" ]; then
    echo -e "${GREEN}Set (${#SECRET_KEY} characters)${NC}"
else
    echo -e "${YELLOW}Auto-generated (consider setting manually)${NC}"
fi

echo -n "API Key: "
if [ -n "$CREDITS_API_KEY" ]; then
    echo -e "${GREEN}Set (${#CREDITS_API_KEY} characters)${NC}"
else
    echo -e "${YELLOW}Using default (change for production)${NC}"
fi

echo ""
echo -e "${BLUE}Immediate Actions Required:${NC}"
echo "-------------------------"
echo "1. 🔑 Change default admin password if not already done"
echo "2. 🔒 Generate unique SECRET_KEY and CREDITS_API_KEY"
echo "3. 🚀 Restart the application to apply security fixes"
echo "4. 📊 Monitor logs for security warnings"
echo "5. 🔍 Review access logs for any credential exposure"

echo ""
echo -e "${BLUE}To apply security environment variables:${NC}"
echo 'export ADMIN_PASSWORD="your_secure_password_here"'
echo 'export SECRET_KEY="$(openssl rand -hex 32)"'
echo 'export CREDITS_API_KEY="$(openssl rand -hex 32)"'

echo ""
echo -e "${BLUE}To start with security fixes:${NC}"
echo "cd credit_admin"
echo "ENABLE_SSL=true python app/main.py"

echo ""
if [ -f "SECURITY_INCIDENT_RESPONSE.md" ]; then
    echo -e "${BLUE}📖 For detailed security information, see: SECURITY_INCIDENT_RESPONSE.md${NC}"
else
    echo -e "${YELLOW}⚠️  Detailed security documentation not found${NC}"
fi

echo ""
echo -e "${GREEN}✅ Security fix validation completed!${NC}"
