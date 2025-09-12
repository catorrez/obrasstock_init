#!/bin/bash

# Script to generate Let's Encrypt SSL certificate for obrasstock.etvholding.com
# Make sure your domain points to this server before running!

set -e

echo "🔐 Generating Let's Encrypt SSL certificate for obrasstock.etvholding.com..."

# Check if domain resolves to this server
echo "⚠️  IMPORTANT: Make sure obrasstock.etvholding.com points to this server!"
echo "You can check with: nslookup obrasstock.etvholding.com"
echo ""
read -p "Is obrasstock.etvholding.com pointing to this server? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Please configure your DNS first and run this script again."
    exit 1
fi

# Check if certbot volumes exist, if not we need to use the existing method
if [ ! -d "/var/lib/letsencrypt" ]; then
    echo "📋 Using Docker run method for SSL generation..."
    
    # Create temporary HTTP-only config for Let's Encrypt challenge
    cat > /dockers/obrasstock/docker/nginx/conf.d/temp-obrasstock-ssl.conf << 'EOF'
server {
    listen 80;
    server_name obrasstock.etvholding.com;
    
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }
    
    location / {
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 300;
        proxy_pass http://web:8000;
    }
}
EOF

    # Check if we have a docker-compose setup that includes certbot
    if docker-compose config | grep -q certbot; then
        echo "🔄 Using docker-compose certbot service..."
        docker-compose run --rm certbot certbot certonly \
            --webroot \
            --webroot-path=/var/www/certbot \
            --email admin@etvholding.com \
            --agree-tos \
            --no-eff-email \
            -d obrasstock.etvholding.com
    else
        echo "🔄 Using standalone certbot container..."
        docker run -it --rm \
            -v /etc/letsencrypt:/etc/letsencrypt \
            -v /var/lib/letsencrypt:/var/lib/letsencrypt \
            -v /dockers/obrasstock/data/certbot:/var/www/certbot \
            certbot/certbot certonly \
            --webroot \
            --webroot-path=/var/www/certbot \
            --email admin@etvholding.com \
            --agree-tos \
            --no-eff-email \
            -d obrasstock.etvholding.com
    fi

    # Remove temporary config
    echo "🧹 Removing temporary config..."
    rm -f /dockers/obrasstock/docker/nginx/conf.d/temp-obrasstock-ssl.conf
else
    echo "🔄 Using system certbot..."
    certbot certonly \
        --webroot \
        --webroot-path=/var/www/certbot \
        --email admin@etvholding.com \
        --agree-tos \
        --no-eff-email \
        -d obrasstock.etvholding.com
fi

# Now update the nginx configuration to use the new certificate
echo "📝 Updating nginx configuration to use dedicated certificate..."

# Create backup of current production config
cp /dockers/obrasstock/docker/nginx/conf.d/production.conf /dockers/obrasstock/docker/nginx/conf.d/production.conf.backup

# Update the obrasstock section to use its own certificate
sed -i '/# Owner domain - obrasstock.etvholding.com/,/^$/s|ssl_certificate /etc/letsencrypt/live/adminos.etvholding.com/|ssl_certificate /etc/letsencrypt/live/obrasstock.etvholding.com/|g' /dockers/obrasstock/docker/nginx/conf.d/production.conf

# Test nginx config
echo "🧪 Testing nginx configuration..."
docker-compose exec nginx nginx -t

if [ $? -eq 0 ]; then
    # Reload nginx with new SSL configuration
    echo "🔄 Reloading nginx with new SSL certificate..."
    docker-compose exec nginx nginx -s reload
    
    echo "🎉 SSL certificate generated successfully!"
    echo "🌐 obrasstock.etvholding.com should now have its own trusted SSL certificate!"
else
    echo "❌ Nginx configuration test failed. Restoring backup..."
    mv /dockers/obrasstock/docker/nginx/conf.d/production.conf.backup /dockers/obrasstock/docker/nginx/conf.d/production.conf
    exit 1
fi

echo ""
echo "📅 The certificate will expire in 90 days. Set up auto-renewal with:"
echo "   0 12 * * * /dockers/obrasstock/renew-ssl.sh"