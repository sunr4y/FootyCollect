# FootyCollect Production Deployment Guide

This directory contains configuration files and scripts for deploying FootyCollect to a VPS or similar Linux server.

## Files

- `nginx.conf` - Nginx reverse proxy configuration
- `gunicorn.service` - Systemd service file for Gunicorn
- `deploy.sh` - Automated deployment script
- `setup.sh` - Initial server setup script
- `env.example` - Environment variables template

## Quick Start

### 1. Initial Server Setup

On a fresh Ubuntu/Debian server, run as root:

```bash
# Copy setup script to server
scp deploy/setup.sh root@your-server-ip:/tmp/

# SSH into server
ssh root@your-server-ip

# Run setup script
chmod +x /tmp/setup.sh
/tmp/setup.sh
```

**Important:** The setup script will prompt you to change the PostgreSQL password. Make sure to do this!

### 2. Clone Repository

```bash
# Switch to application user
su - footycollect

# Clone repository
cd /var/www
git clone https://github.com/your-username/FootyCollect.git footycollect
cd footycollect
```

### 3. Setup Virtual Environment

```bash
# Create virtual environment
python3.12 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements/production.txt
```

### 4. Configure Environment Variables

```bash
# Copy environment template
cp deploy/env.example .env

# Edit environment variables
nano .env
```

Fill in all required values, especially:
- `DJANGO_SECRET_KEY` - Generate with: `python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'`
- `DATABASE_URL` - Update with your PostgreSQL password
- `REDIS_URL` - Should be `redis://localhost:6379/0`
- `DJANGO_ALLOWED_HOSTS` - Your domain name
- `SENTRY_DSN` - Your Sentry DSN (optional but recommended)

### 5. Setup Database

```bash
# Activate virtual environment
source venv/bin/activate

# Run migrations
python manage.py migrate

# Create superuser (optional)
python manage.py createsuperuser

# Collect static files
python manage.py collectstatic --noinput
```

### 6. Configure Nginx

```bash
# Copy nginx configuration
sudo cp deploy/nginx.conf /etc/nginx/sites-available/footycollect

# Edit configuration to match your domain (replace footycollect.pro with your domain)
sudo nano /etc/nginx/sites-available/footycollect
# Replace all instances of "footycollect.pro" with your actual domain name

# Enable site
sudo ln -s /etc/nginx/sites-available/footycollect /etc/nginx/sites-enabled/

# Test nginx configuration
sudo nginx -t

# Reload nginx
sudo systemctl reload nginx
```

### 7. Setup SSL with Let's Encrypt

```bash
# Install certbot (if not already installed)
sudo apt-get install certbot python3-certbot-nginx

# Obtain SSL certificate (replace with your domain)
sudo certbot --nginx -d your-domain.com -d www.your-domain.com

# Certbot will automatically configure nginx and set up auto-renewal
```

### 8. Configure Gunicorn Service

```bash
# Copy systemd service file
sudo cp deploy/gunicorn.service /etc/systemd/system/

# Edit service file to match your paths
sudo nano /etc/systemd/system/gunicorn.service

# Reload systemd
sudo systemctl daemon-reload

# Enable and start Gunicorn
sudo systemctl enable gunicorn
sudo systemctl start gunicorn

# Check status
sudo systemctl status gunicorn
```

### 9. Verify Deployment

```bash
# Check Gunicorn logs
sudo journalctl -u gunicorn -f

# Check Nginx logs
sudo tail -f /var/log/nginx/footycollect_error.log

# Test health endpoints
curl http://localhost:8000/health/
curl http://localhost:8000/ready/
```

## Deployment Process

After initial setup, use the deployment script for updates:

```bash
# SSH into server
ssh footycollect@your-server-ip

# Navigate to project directory
cd /var/www/footycollect

# Run deployment script
./deploy/deploy.sh
```

The deployment script will:
1. Backup the database
2. Pull latest code (if using git)
3. Update dependencies
4. Run migrations
5. Collect static files
6. Run Django system checks
7. Restart Gunicorn
8. Reload Nginx
9. Perform health checks

## Maintenance

### View Logs

```bash
# Gunicorn logs
sudo journalctl -u gunicorn -f

# Nginx access logs
sudo tail -f /var/log/nginx/footycollect_access.log

# Nginx error logs
sudo tail -f /var/log/nginx/footycollect_error.log

# Application logs (if configured)
tail -f /var/www/footycollect/logs/*.log
```

### Restart Services

```bash
# Restart Gunicorn
sudo systemctl restart gunicorn

# Reload Nginx (no downtime)
sudo systemctl reload nginx

# Restart Nginx (with brief downtime)
sudo systemctl restart nginx
```

### Database Backups

Database backups are automatically created during deployment. Manual backup:

```bash
sudo -u postgres pg_dump footycollect_db > /var/www/footycollect/backups/db_backup_$(date +%Y%m%d_%H%M%S).sql
```

### Update Dependencies

```bash
cd /var/www/footycollect
source venv/bin/activate
pip install --upgrade -r requirements/production.txt
sudo systemctl restart gunicorn
```

## Security Checklist

- [ ] Firewall configured (UFW)
- [ ] Fail2ban enabled
- [ ] SSL/TLS certificate installed
- [ ] Strong database password set
- [ ] SECRET_KEY is unique and secure
- [ ] DEBUG=False in production
- [ ] ALLOWED_HOSTS configured
- [ ] Regular security updates enabled
- [ ] Database backups automated
- [ ] Monitoring/alerting configured

## Troubleshooting

### Gunicorn won't start

```bash
# Check service status
sudo systemctl status gunicorn

# Check logs
sudo journalctl -u gunicorn -n 50

# Verify virtual environment
ls -la /var/www/footycollect/venv/bin/gunicorn

# Check permissions
ls -la /var/www/footycollect
```

### Nginx 502 Bad Gateway

```bash
# Check if Gunicorn is running
sudo systemctl status gunicorn

# Check Gunicorn is listening on port 8000
sudo netstat -tlnp | grep 8000

# Check Nginx error logs
sudo tail -f /var/log/nginx/footycollect_error.log
```

### Database connection errors

```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Test database connection
sudo -u postgres psql -d footycollect_db -U footycollect

# Verify DATABASE_URL in .env file
cat /var/www/footycollect/.env | grep DATABASE_URL
```

### Static files not loading

```bash
# Verify static files collected
ls -la /var/www/footycollect/staticfiles/

# Check Nginx configuration
sudo nginx -t

# Verify Nginx can access static files
sudo ls -la /var/www/footycollect/staticfiles/
```

## Support

For issues or questions, please open an issue on GitHub.
