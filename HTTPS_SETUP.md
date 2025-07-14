# HTTPS Setup Guide

This guide explains how to set up HTTPS for the OpenWebUI Credit System.

## Quick Start

### Option 1: Docker with Nginx (Recommended for Production)

1. **Generate SSL certificates:**
   ```bash
   cd credit_admin
   
   # For development (self-signed):
   ./setup-ssl.sh
   
   # For production with Let's Encrypt:
   ./setup-ssl-production.sh yourdomain.com your-email@example.com
   ```

2. **Run with Docker Compose:**
   ```bash
   docker-compose -f docker-compose-https.yml up -d
   ```

3. **Access your application:**
   - HTTP: http://localhost (redirects to HTTPS)
   - HTTPS: https://localhost

### Option 2: Direct FastAPI HTTPS (Development Only)

1. **Generate SSL certificates:**
   ```bash
   cd credit_admin
   ./setup-ssl.sh
   ```

2. **Run with SSL enabled:**
   ```bash
   ENABLE_SSL=true python app/main.py
   ```

## Configuration Options

### Environment Variables

- `ENABLE_SSL`: Set to "true" to enable direct SSL in FastAPI
- `SSL_CERT_PATH`: Path to SSL certificate file (default: "ssl/cert.pem")
- `SSL_KEY_PATH`: Path to SSL private key file (default: "ssl/key.pem")

### Docker Compose

The `docker-compose-https.yml` file includes:
- Nginx reverse proxy with SSL termination
- Automatic HTTP to HTTPS redirect
- Security headers
- WebSocket support (if needed)

## Production Deployment

### 1. Domain Setup

Ensure your domain points to your server's IP address.

### 2. Let's Encrypt Certificates

```bash
# Install certbot if not already installed
sudo apt-get update && sudo apt-get install -y certbot

# Generate certificates
./setup-ssl-production.sh yourdomain.com your-email@example.com
```

### 3. Update Configuration

Edit `nginx.conf` to use your domain name:
```nginx
server_name yourdomain.com;
```

### 4. Deploy

```bash
docker-compose -f docker-compose-https.yml up -d
```

## Security Features

The HTTPS setup includes:

- **TLS 1.2 and 1.3 support**
- **Strong cipher suites**
- **Security headers:**
  - X-Frame-Options: DENY
  - X-Content-Type-Options: nosniff
  - X-XSS-Protection: 1; mode=block
  - Strict-Transport-Security (HSTS)
- **Automatic HTTP to HTTPS redirect**

## Certificate Renewal

For Let's Encrypt certificates, renewal is automatically configured via cron job:
```bash
0 2 * * * /usr/bin/certbot renew --quiet && docker-compose -f docker-compose-https.yml restart nginx
```

## Troubleshooting

### Common Issues

1. **Certificate not found:**
   - Ensure SSL certificates are generated in the `ssl/` directory
   - Check file permissions (cert.pem: 644, key.pem: 600)

2. **Port conflicts:**
   - Ensure ports 80 and 443 are not used by other services
   - Stop other web servers if running

3. **Domain validation fails:**
   - Ensure domain DNS points to your server
   - Check firewall settings for ports 80 and 443

### Testing HTTPS

```bash
# Test SSL configuration
curl -I https://localhost
openssl s_client -connect localhost:443 -servername localhost

# Check certificate details
openssl x509 -in ssl/cert.pem -text -noout
```

## Development vs Production

| Feature | Development | Production |
|---------|-------------|------------|
| Certificate | Self-signed | Let's Encrypt |
| Domain | localhost | Real domain |
| Security | Basic | Full security headers |
| Renewal | Manual | Automatic |
| Proxy | Optional | Recommended |

## File Structure

```
credit_admin/
├── ssl/
│   ├── cert.pem          # SSL certificate
│   └── key.pem           # SSL private key
├── nginx.conf            # Nginx configuration
├── docker-compose-https.yml  # HTTPS Docker setup
├── setup-ssl.sh          # Development SSL setup
└── setup-ssl-production.sh   # Production SSL setup
```

## Extension Configuration for HTTPS

The OpenWebUI extensions have been updated to support HTTPS endpoints. Configure them using environment variables:

### Environment Variables

Set these in your OpenWebUI environment (`.env` file or system environment):

```bash
# API Protocol (http or https)
CREDITS_API_PROTOCOL=https

# API Host and Port
CREDITS_API_HOST=localhost:8000

# SSL Verification (set to true for production with valid certificates)
CREDITS_API_SSL_VERIFY=false
```

### Configuration Examples

**Development with self-signed certificates:**
```bash
CREDITS_API_PROTOCOL=https
CREDITS_API_HOST=localhost:8000
CREDITS_API_SSL_VERIFY=false
```

**Production with valid SSL certificates:**
```bash
CREDITS_API_PROTOCOL=https
CREDITS_API_HOST=yourdomain.com
CREDITS_API_SSL_VERIFY=true
```

**HTTP fallback (if HTTPS is not available):**
```bash
CREDITS_API_PROTOCOL=http
CREDITS_API_HOST=localhost:8000
CREDITS_API_SSL_VERIFY=false
```

### Updated Extensions

All three extensions now support HTTPS:
- `credit_charging_filter.py` - Charges credits for token usage
- `credit_management_enough_credits.py` - Checks if user has enough credits
- `credit_management_models.py` - Shows model pricing information

### SSL Certificate Considerations

- **Self-signed certificates**: Set `CREDITS_API_SSL_VERIFY=false`
- **Let's Encrypt or CA certificates**: Set `CREDITS_API_SSL_VERIFY=true`
- **Corporate environments**: May require custom certificate handling

## Security Configuration

### Authentication

The admin interface is now secured with JWT-based authentication:

**Default Credentials (⚠️ CHANGE IN PRODUCTION!):**
- Username: `admin`
- Password: `admin123`

**Environment Variables:**
```bash
# Admin authentication
ADMIN_USERNAME=admin
ADMIN_PASSWORD=your_secure_password_here
SECRET_KEY=your_jwt_secret_key_here
ACCESS_TOKEN_EXPIRE_MINUTES=30

# API security for extensions
CREDITS_API_KEY=your_api_key_here
```

### API Security

All admin endpoints require JWT authentication, and extension endpoints require an API key:

**Admin Endpoints (require JWT token):**
- `/api/credits/users` - Get all users
- `/api/credits/models` - Get all models  
- `/api/credits/groups` - Get all groups
- `/api/credits/update` - Update user credits
- `/api/credits/models/update` - Update model pricing
- `/api/credits/groups/update` - Update group settings
- `/api/credits/sync-*` - Manual sync operations

**Extension Endpoints (require API key):**
- `/api/credits/user/{user_id}` - Get specific user credits
- `/api/credits/model/{model_id}` - Get specific model pricing
- `/api/credits/deduct-tokens` - Deduct credits for token usage

### Setting Up Security

1. **Generate secure credentials:**
   ```bash
   # Generate a strong secret key
   export SECRET_KEY=$(openssl rand -hex 32)
   
   # Generate API key for extensions
   export CREDITS_API_KEY=$(openssl rand -hex 32)
   
   # Set admin password
   export ADMIN_PASSWORD="your_very_secure_password"
   ```

2. **Configure OpenWebUI extensions:**
   ```bash
   # Add to OpenWebUI environment
   CREDITS_API_PROTOCOL=https
   CREDITS_API_HOST=localhost:8000
   CREDITS_API_SSL_VERIFY=false
   CREDITS_API_KEY=your_api_key_here
   ```

3. **View current configuration:**
   ```bash
   cd credit_admin
   ./show-security-config.sh
   ```

### Access Control

- **Admin Interface**: Requires login at `/` with username/password
- **API Documentation**: Available at `/docs` (requires authentication)
- **Health Check**: Public endpoint for monitoring
- **Extension APIs**: Require API key in `X-API-Key` header
