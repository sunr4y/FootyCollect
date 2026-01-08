#!/bin/bash
# Deployment script for FootyCollect
# Run this script from the project root on the server

set -e

# Configuration
APP_DIR="/var/www/footycollect"
APP_USER="footycollect"
VENV_DIR="$APP_DIR/venv"
BACKUP_DIR="$APP_DIR/backups"
LOG_DIR="$APP_DIR/logs"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as correct user
if [ "$USER" != "$APP_USER" ] && [ "$EUID" -ne 0 ]; then
    log_error "Please run as $APP_USER or root"
    exit 1
fi

# Check if we're in the right directory
if [ ! -f "manage.py" ]; then
    log_error "manage.py not found. Are you in the project root?"
    exit 1
fi

log_info "Starting deployment..."

# Create necessary directories
mkdir -p "$BACKUP_DIR"
mkdir -p "$LOG_DIR"

# Backup database
log_info "Backing up database..."
if [ -f "$VENV_DIR/bin/python" ]; then
    BACKUP_FILE="$BACKUP_DIR/db_backup_$(date +%Y%m%d_%H%M%S).sql"
    sudo -u postgres pg_dump footycollect_db > "$BACKUP_FILE"
    log_info "Database backup created: $BACKUP_FILE"

    # Keep only last 7 backups
    ls -t "$BACKUP_DIR"/db_backup_*.sql | tail -n +8 | xargs -r rm
else
    log_warn "Virtual environment not found, skipping database backup"
fi

# Activate virtual environment and update dependencies
log_info "Updating dependencies..."
if [ -f "$VENV_DIR/bin/activate" ]; then
    source "$VENV_DIR/bin/activate"
    pip install --upgrade pip
    pip install -r requirements/production.txt
else
    log_error "Virtual environment not found at $VENV_DIR"
    exit 1
fi

# Pull latest code (if using git)
if [ -d ".git" ]; then
    log_info "Pulling latest code..."
    git fetch origin
    git reset --hard origin/main
fi

# Run migrations
log_info "Running database migrations..."
python manage.py migrate --noinput

# Collect static files
log_info "Collecting static files..."
python manage.py collectstatic --noinput --clear

# Run Django checks
log_info "Running Django system checks..."
python manage.py check --deploy || {
    log_error "Django checks failed!"
    exit 1
}

# Restart Gunicorn
log_info "Restarting Gunicorn..."
if systemctl is-active --quiet gunicorn; then
    sudo systemctl restart gunicorn
    log_info "Gunicorn restarted"
else
    log_warn "Gunicorn service not running. Start it with: sudo systemctl start gunicorn"
fi

# Reload Nginx
log_info "Reloading Nginx..."
if systemctl is-active --quiet nginx; then
    sudo systemctl reload nginx
    log_info "Nginx reloaded"
else
    log_warn "Nginx not running"
fi

# Check service status
log_info "Checking service status..."
if systemctl is-active --quiet gunicorn; then
    log_info "✓ Gunicorn is running"
else
    log_error "✗ Gunicorn is not running"
    exit 1
fi

if systemctl is-active --quiet nginx; then
    log_info "✓ Nginx is running"
else
    log_error "✗ Nginx is not running"
    exit 1
fi

# Health check
log_info "Performing health check..."
sleep 2
if curl -f -s http://localhost:8000/health/ > /dev/null; then
    log_info "✓ Health check passed"
else
    log_error "✗ Health check failed"
    exit 1
fi

log_info "Deployment completed successfully!"
log_info "Check logs at: $LOG_DIR"
