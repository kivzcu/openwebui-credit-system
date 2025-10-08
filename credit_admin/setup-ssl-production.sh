#!/bin/bash

# Production SSL setup with Let's Encrypt
# This script helps set up proper SSL certificates for production


DOMAIN=${1:-localhost}
EMAIL=${2:-admin@example.com}

# Small helpers
err() { echo "\nERROR: $*" >&2; }
info() { echo "$*"; }


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
    
    # Pre-check: ensure domain resolves to this machine
    IP_ONLINE=$(getent hosts $DOMAIN | awk '{print $1}' || true)
    if [ -z "$IP_ONLINE" ]; then
        err "Domain $DOMAIN does not resolve in /etc/hosts or DNS. Please ensure it points to this server before running this script."
        exit 2
    fi

    # Check whether port 80 is in use locally
    if ss -ltn "sport = :80" | grep -q LISTEN; then
        info "Port 80 is currently in use on this host. Attempting to detect running webserver and use certbot plugin."

        # Try to detect nginx or apache
        WEBSERVER=""
        if pgrep -x nginx >/dev/null 2>&1; then
            WEBSERVER="nginx"
        elif pgrep -x apache2 >/dev/null 2>&1 || pgrep -x httpd >/dev/null 2>&1; then
            WEBSERVER="apache"
        fi

        if [ -n "$WEBSERVER" ]; then
            info "Detected webserver: $WEBSERVER. Using certbot --$WEBSERVER plugin."
            # If nginx detected, try to install a site config from the repo and enable it
            if [ "$WEBSERVER" = "nginx" ]; then
                info "Installing nginx site template for $DOMAIN"
                SITE_SRC="$(pwd)/nginx_site_template.conf"
                SITE_DEST="/etc/nginx/sites-available/$DOMAIN.conf"
                if [ -f "$SITE_SRC" ]; then
                    sudo sed "s/__DOMAIN__/$DOMAIN/g" "$SITE_SRC" | sudo tee "$SITE_DEST" > /dev/null
                    sudo ln -sf "$SITE_DEST" "/etc/nginx/sites-enabled/$DOMAIN.conf"
                    sudo nginx -t && sudo systemctl reload nginx || true
                else
                    info "No site template found in repo; skipping site install"
                fi
            fi

            echo "Generating Let's Encrypt certificate using plugin ($WEBSERVER)..."
            if ! sudo certbot --$WEBSERVER -d "$DOMAIN" --email "$EMAIL" --agree-tos --no-eff-email -n; then
                err "certbot ($WEBSERVER plugin) failed to obtain a certificate for $DOMAIN."
                err "Check that the domain points to this server and that the webserver configuration allows the ACME challenge paths."
                err "See /var/log/letsencrypt/letsencrypt.log for details."
                exit 4
            fi
            # reload nginx to pick up new certs if nginx used
            if [ "$WEBSERVER" = "nginx" ]; then
                sudo systemctl reload nginx || true
            fi
        else
            info "No supported webserver detected, and port 80 is in use. Certbot standalone requires port 80 free."
            info "Either stop the service using port 80 (eg. nginx) temporarily, or configure that service to proxy ACME challenges to certbot."
            exit 3
        fi
    else
        # Port 80 is free: use standalone
        echo "Generating Let's Encrypt certificate..."
        if ! sudo certbot certonly --standalone --preferred-challenges http \
            --email "$EMAIL" \
            --agree-tos \
            --no-eff-email \
            -d "$DOMAIN" -n; then
            err "certbot failed to obtain a certificate for $DOMAIN."
            err "Check that the domain points to this server, port 80 is reachable from the internet, and there are no firewalls blocking inbound HTTP."
            err "See /var/log/letsencrypt/letsencrypt.log for details."
            exit 4
        fi
    fi

    # Copy certificates to ssl directory (only if they exist)
    CHAIN="/etc/letsencrypt/live/$DOMAIN/fullchain.pem"
    KEY="/etc/letsencrypt/live/$DOMAIN/privkey.pem"
    if [ ! -f "$CHAIN" ] || [ ! -f "$KEY" ]; then
        err "Expected certificate files not found after certbot run:"
        err "  $CHAIN"
        err "  $KEY"
        exit 5
    fi

    sudo cp "$CHAIN" ssl/cert.pem
    sudo cp "$KEY" ssl/key.pem

    # Set proper ownership and permissions
    sudo chown "$USER:$USER" ssl/cert.pem ssl/key.pem
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
