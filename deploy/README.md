# FootyCollect Production Deployment Guide

This directory contains configuration files and scripts for deploying FootyCollect to a VPS or similar Linux server.

## Files

- `nginx.conf` - Nginx reverse proxy configuration
- `gunicorn.service` - Systemd service file for Gunicorn
- `deploy.sh` - Automated deployment script
- `setup.sh` - Initial server setup script
- `env.example` - Environment variables template (production / full reference)

## Environment templates (why two?)

- **`deploy/env.example`** – Full production template: single reference with all variables (Django, DB, Redis, SendGrid, Sentry, S3/R2, FKAPI, etc.). Use on bare metal (copy to `.env` on the server) or as reference to fill `.envs/.production/.django` and `.envs/.production/.postgres` for Docker production.
- **`.envs/.local/.django.example`** – Local development only. Copy to `.envs/.local/.django`. Read by `config/settings/base.py` and used by `docker-compose.local.yml` and local env (postgres in `.envs/.local/.postgres`). Mostly local overrides (USE_DOCKER, REDIS_URL with `redis:6379`, STORAGE_BACKEND=local, Flower, FKAPI). For the full variable list, see `deploy/env.example`.

## Deployment with Docker (production)

Build and run the full stack (Django, Postgres, Redis, Traefik, Celery) with Docker Compose. Build context must be the **repository root**.

```bash
# From repository root
docker compose -f docker-compose.production.yml build

# Env files required: .envs/.production/.django and .envs/.production/.postgres
# Copy deploy/env.example and adjust; split vars into those two files as needed.

docker compose -f docker-compose.production.yml up -d
```

- **Images:** `compose/production/django/Dockerfile` (multi-stage), Postgres, Nginx, Traefik, AWS CLI for backups.
- **Entrypoint:** Waits for Postgres, then runs the given command (`/start` runs collectstatic + Gunicorn).
- **Static/media in production:** S3/R2 via `config.settings.production`; collectstatic runs at container start and uploads to object storage.

## Quick Start (bare metal)

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

## Static and media files (S3 / CDN)

When using production settings with S3 (or Cloudflare R2), static and media files are served from object storage and optionally a CDN.

### Verification

Before or after deployment, verify static files configuration and that `collectstatic` would run correctly:

```bash
source venv/bin/activate

# Check STORAGES config and run collectstatic in dry-run (no upload)
python manage.py verify_staticfiles

# Only check config, skip dry-run
python manage.py verify_staticfiles --skip-dry-run
```

### Collecting static files to S3

With production settings (`config.settings.production`), `collectstatic` uploads to the configured bucket. [Collectfasta](https://github.com/jasongi/collectfasta) is used to speed up uploads by only transferring changed files.

```bash
# Collect static files to S3 (or R2)
python manage.py collectstatic --noinput

# Optional: clear existing files in the static/ prefix before uploading
python manage.py collectstatic --noinput --clear
```

Required environment variables for S3:

- **AWS S3**: `DJANGO_AWS_ACCESS_KEY_ID`, `DJANGO_AWS_SECRET_ACCESS_KEY`, `DJANGO_AWS_STORAGE_BUCKET_NAME`, and optionally `DJANGO_AWS_S3_REGION_NAME`, `DJANGO_AWS_S3_CUSTOM_DOMAIN`
- **Cloudflare R2**: `STORAGE_BACKEND=r2`, `CLOUDFLARE_ACCESS_KEY_ID`, `CLOUDFLARE_SECRET_ACCESS_KEY`, `CLOUDFLARE_BUCKET_NAME`, `CLOUDFLARE_R2_ENDPOINT_URL`, and optionally `CLOUDFLARE_R2_CUSTOM_DOMAIN`

### R2 CORS (fonts/static from custom domain)

If admin or static fonts from your R2 custom domain are blocked by CORS, add CORS on the bucket: Dashboard → R2 → bucket → Settings → CORS Policy → Add CORS policy (paste a JSON array). Or with Wrangler: `npx wrangler r2 bucket cors set <BUCKET_NAME> --file deploy/r2-cors-wrangler.json`. After changing CORS, purge cache for the custom domain if using Cloudflare cache.

### File permissions and CDN

- Static files use `public-read` ACL so they are accessible via the bucket URL or custom domain (CDN).
- Media files (user uploads) use the default bucket ACL; ensure the bucket policy or CDN allows access if they are served publicly.
- `STATIC_URL` and `MEDIA_URL` are set from the configured custom domain or bucket endpoint in `config/settings/production.py`.

## Support

For issues or questions, please open an issue on GitHub.
