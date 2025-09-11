#!/bin/bash

# Script to generate Let's Encrypt SSL certificates
# Make sure your domains point to this server before running!

set -e

echo "🔐 Generating Let's Encrypt SSL certificates..."

# Check if domains resolve to this server
echo "⚠️  IMPORTANT: Make sure adminos.etvholding.com and appos.etvholding.com point to this server!"
echo "You can check with: nslookup adminos.etvholding.com"
echo ""
read -p "Are the domains pointing to this server? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Please configure your DNS first and run this script again."
    exit 1
fi

# Temporarily disable production config
echo "📋 Temporarily disabling production SSL config..."
mv /dockers/obrasstock/docker/nginx/conf.d/production.conf /dockers/obrasstock/docker/nginx/conf.d/production.conf.backup || true

# Create temporary HTTP-only config for Let's Encrypt challenge
cat > /dockers/obrasstock/docker/nginx/conf.d/temp-ssl.conf << 'EOF'
server {
    listen 80;
    server_name adminos.etvholding.com appos.etvholding.com;
    
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

# Restart nginx with temporary config
echo "🔄 Restarting nginx with temporary HTTP config..."
docker-compose restart nginx

# Wait for nginx to be ready
sleep 5

# Generate certificates for both domains
echo "🔑 Generating certificate for adminos.etvholding.com..."
docker-compose run --rm certbot certbot certonly \
    --webroot \
    --webroot-path=/var/www/certbot \
    --email admin@etvholding.com \
    --agree-tos \
    --no-eff-email \
    -d adminos.etvholding.com

echo "🔑 Generating certificate for appos.etvholding.com..."
docker-compose run --rm certbot certbot certonly \
    --webroot \
    --webroot-path=/var/www/certbot \
    --email admin@etvholding.com \
    --agree-tos \
    --no-eff-email \
    -d appos.etvholding.com

# Remove temporary config
echo "🧹 Removing temporary config..."
rm /dockers/obrasstock/docker/nginx/conf.d/temp-ssl.conf

# Restore production config
echo "✅ Enabling production SSL config..."
mv /dockers/obrasstock/docker/nginx/conf.d/production.conf.backup /dockers/obrasstock/docker/nginx/conf.d/production.conf

# Test nginx config
echo "🧪 Testing nginx configuration..."
docker-compose exec nginx nginx -t

# Reload nginx with SSL
echo "🔄 Reloading nginx with SSL certificates..."
docker-compose reload nginx || docker-compose restart nginx

echo "🎉 SSL certificates generated successfully!"
echo "🌐 Your sites should now have trusted SSL certificates:"
echo "   https://adminos.etvholding.com"
echo "   https://appos.etvholding.com"
echo ""
echo "📅 Set up auto-renewal with:"
echo "   0 12 * * * /dockers/obrasstock/renew-ssl.sh"