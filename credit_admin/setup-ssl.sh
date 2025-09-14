#!/bin/bash

# Create SSL directory
mkdir -p ssl

# Generate self-signed certificate for development/testing
# For production, replace with proper SSL certificates from Let's Encrypt or a CA
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout ssl/key.pem \
    -out ssl/cert.pem \
    -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost" \
    -addext "subjectAltName = DNS:localhost, IP:147.228.121.27"

echo "Self-signed SSL certificate generated in ssl/ directory"
echo "For production, replace with proper SSL certificates"

# Set proper permissions
chmod 600 ssl/key.pem
chmod 644 ssl/cert.pem


