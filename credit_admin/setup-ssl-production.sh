#!/bin/bash

# Production SSL setup with Let's Encrypt
# This script helps set up proper SSL certificates for production

DOMAIN=${1:-localhost}
EMAIL=${2:-admin@example.com}

echo "Setting up SSL certificates for domain: $DOMAIN"

# Create SSL directory
mkdir -p ssl

if [ "$DOMAIN" = "localhost" ]; then
    echo "⚠️  Using localhost - generating self-signed certificate for development"
    ./setup-ssl.sh
else
    echo "🔒 Setting up Let's Encrypt certificate for production domain: $DOMAIN"
    
    # Check if certbot is installed
    if ! command -v certbot &> /dev/null; then
        echo "Installing certbot..."
        if command -v apt-get &> /dev/null; then
            sudo apt-get update
            sudo apt-get install -y certbot
        elif command -v yum &> /dev/null; then
            sudo yum install -y certbot
        else
            echo "Please install certbot manually for your system"
            exit 1
        fi
    fi
    
    # Generate certificate
    echo "Generating Let's Encrypt certificate..."
    sudo certbot certonly --standalone --preferred-challenges http \
        --email $EMAIL \
        --agree-tos \
        --no-eff-email \
        -d $DOMAIN
    
    # Copy certificates to ssl directory
    sudo cp /etc/letsencrypt/live/$DOMAIN/fullchain.pem ssl/cert.pem
    sudo cp /etc/letsencrypt/live/$DOMAIN/privkey.pem ssl/key.pem
    
    # Set proper ownership and permissions
    sudo chown $USER:$USER ssl/cert.pem ssl/key.pem
    chmod 644 ssl/cert.pem
    chmod 600 ssl/key.pem
    
    echo "✅ Let's Encrypt certificate installed successfully"
    
    # Create renewal cron job
    echo "Setting up automatic renewal..."
    (crontab -l 2>/dev/null; echo "0 2 * * * /usr/bin/certbot renew --quiet && docker-compose -f docker-compose-https.yml restart nginx") | crontab -
fi

echo ""
echo "SSL setup complete!"
echo ""
echo "To run with HTTPS:"
echo "  Development: ENABLE_SSL=true python app/main.py"
echo "  Production:  docker-compose -f docker-compose-https.yml up -d"
echo ""
echo "Your application will be available at:"
echo "  HTTP:  http://$DOMAIN"
echo "  HTTPS: https://$DOMAIN"
