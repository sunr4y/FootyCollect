#!/bin/bash
# Initial server setup script for FootyCollect on VPS
# Run this script as root on a fresh Ubuntu/Debian server

set -e

echo "=== FootyCollect Production Server Setup ==="
echo "This script will set up a fresh server for FootyCollect deployment"
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root (use sudo)"
    exit 1
fi

# Update system
echo "Updating system packages..."
apt-get update
apt-get upgrade -y

# Install required packages
echo "Installing required packages..."
apt-get install -y \
    python3.12 \
    python3.12-venv \
    python3-pip \
    postgresql \
    postgresql-contrib \
    redis-server \
    nginx \
    certbot \
    python3-certbot-nginx \
    git \
    curl \
    build-essential \
    libpq-dev \
    python3-dev \
    supervisor \
    ufw \
    fail2ban

# Create application user
echo "Creating application user..."
if ! id "footycollect" &>/dev/null; then
    useradd -m -s /bin/bash footycollect
    echo "User 'footycollect' created"
else
    echo "User 'footycollect' already exists"
fi

# Create application directory
echo "Creating application directory..."
APP_DIR="/var/www/footycollect"
mkdir -p "$APP_DIR"
chown footycollect:footycollect "$APP_DIR"

# Create directories for static files and media
mkdir -p "$APP_DIR/staticfiles"
mkdir -p "$APP_DIR/media"
chown -R footycollect:footycollect "$APP_DIR"

# Setup PostgreSQL
echo "Setting up PostgreSQL..."
sudo -u postgres psql <<EOF
CREATE USER footycollect WITH PASSWORD 'CHANGE_THIS_PASSWORD';
CREATE DATABASE footycollect_db OWNER footycollect;
ALTER USER footycollect CREATEDB;
\q
EOF

echo "⚠️  IMPORTANT: Change the PostgreSQL password in the command above!"
echo "⚠️  Run: sudo -u postgres psql -c \"ALTER USER footycollect WITH PASSWORD 'your-secure-password';\""

# Configure Redis
echo "Configuring Redis..."
sed -i 's/^supervised no/supervised systemd/' /etc/redis/redis.conf
systemctl restart redis

# Configure firewall
echo "Configuring firewall..."
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow 'Nginx Full'
ufw --force enable

# Configure fail2ban
echo "Configuring fail2ban..."
systemctl enable fail2ban
systemctl start fail2ban

# Setup log rotation
echo "Setting up log rotation..."
cat > /etc/logrotate.d/footycollect <<EOF
/var/www/footycollect/logs/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 footycollect footycollect
    sharedscripts
}
EOF

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Next steps:"
echo "1. Clone your repository to $APP_DIR"
echo "2. Create virtual environment: python3.12 -m venv $APP_DIR/venv"
echo "3. Copy deploy/.env.example to $APP_DIR/.env and configure it"
echo "4. Install dependencies: $APP_DIR/venv/bin/pip install -r requirements/production.txt"
echo "5. Run migrations: $APP_DIR/venv/bin/python manage.py migrate"
echo "6. Collect static files: $APP_DIR/venv/bin/python manage.py collectstatic --noinput"
echo "7. Copy deploy/nginx.conf to /etc/nginx/sites-available/footycollect"
echo "8. Enable nginx site: ln -s /etc/nginx/sites-available/footycollect /etc/nginx/sites-enabled/"
echo "9. Copy deploy/gunicorn.service to /etc/systemd/system/"
echo "10. Setup SSL: certbot --nginx -d footycollect.pro -d www.footycollect.pro"
echo "11. Start services: systemctl enable gunicorn && systemctl start gunicorn"
echo "12. Reload nginx: systemctl reload nginx"
echo ""
