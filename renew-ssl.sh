#!/bin/bash

# Script to renew Let's Encrypt SSL certificates
# Add to crontab: 0 12 * * * /dockers/obrasstock/renew-ssl.sh

set -e

cd /dockers/obrasstock

echo "🔄 $(date): Checking for SSL certificate renewal..."

# Try to renew certificates
if docker-compose run --rm certbot certbot renew --quiet; then
    echo "🔄 $(date): Certificate renewal check completed"
    
    # Test nginx config
    if docker-compose exec nginx nginx -t; then
        # Reload nginx to use any new certificates
        docker-compose exec nginx nginx -s reload
        echo "✅ $(date): Nginx reloaded successfully"
    else
        echo "❌ $(date): Nginx config test failed"
        exit 1
    fi
else
    echo "⚠️ $(date): Certificate renewal check failed"
    exit 1
fi

echo "✅ $(date): SSL renewal process completed"