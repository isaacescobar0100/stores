#!/bin/bash
# Script para inicializar certificados SSL con Let's Encrypt
# Ejecutar en el servidor: bash init-ssl.sh

DOMAIN="vxplay.online"
EMAIL="admin@vxplay.online"

echo "=== Inicializando SSL para $DOMAIN ==="

# Crear directorios
mkdir -p certbot/conf certbot/www

# Crear configuracion temporal de nginx (sin SSL)
cat > nginx-temp.conf << 'EOF'
server {
    listen 80;
    server_name vxplay.online *.vxplay.online;

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        return 200 'OK';
        add_header Content-Type text/plain;
    }
}
EOF

# Backup nginx.conf original
cp nginx.conf nginx.conf.backup

# Usar config temporal
cp nginx-temp.conf nginx.conf

# Reiniciar nginx con config temporal
docker compose up -d nginx

echo "Esperando que nginx inicie..."
sleep 5

# Obtener certificado
docker compose run --rm certbot certonly \
    --webroot \
    --webroot-path=/var/www/certbot \
    --email $EMAIL \
    --agree-tos \
    --no-eff-email \
    -d $DOMAIN \
    -d "*.$DOMAIN"

# Restaurar nginx.conf original con SSL
cp nginx.conf.backup nginx.conf
rm nginx-temp.conf nginx.conf.backup

# Reiniciar todo
docker compose down
docker compose up -d

echo ""
echo "=== SSL Configurado ==="
echo "Accede a https://$DOMAIN"
