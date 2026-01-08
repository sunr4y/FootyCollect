# FootyCollect

A Django-based web application for managing your football memorabilia collection.

[![Built with Cookiecutter Django](https://img.shields.io/badge/built%20with-Cookiecutter%20Django-ff69b4.svg?logo=cookiecutter)](https://github.com/cookiecutter/cookiecutter-django/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![codecov](https://codecov.io/gh/sunr4y/footycollect/branch/main/graph/badge.svg)](https://codecov.io/gh/sunr4y/footycollect)

**License**: MIT

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [Development](#development)
- [API Documentation](#api-documentation)
- [Testing](#testing)
- [Deployment](#deployment)
- [Documentation](#documentation)

## Overview

FootyCollect is a comprehensive platform for football memorabilia collectors to catalog, organize, and manage their collections. The application supports various item types including jerseys, shorts, outerwear, and tracksuits, with integration to external football kit databases.

### Key Features

- **Multi-Item Type Support**: Manage jerseys, shorts, outerwear, and tracksuits
- **External API Integration**: Fetch kit data from Football Kit Archive API
- **Photo Management**: Upload and organize photos for each item
- **Advanced Search**: Filter and search your collection
- **User Profiles**: Personal collections with privacy controls
- **RESTful API**: Complete API for programmatic access

## Architecture

FootyCollect follows a clean architecture pattern with clear separation of concerns:

### Service Layer Pattern

The application uses a service layer to encapsulate business logic, keeping views thin and models focused on data representation. Services handle:

- Item creation and management
- Photo processing and optimization
- External API integration
- Collection operations

See [Architecture Documentation](docs/ARCHITECTURE/system_design.md) for details.

### Multi-Table Inheritance (MTI)

Item types (Jersey, Shorts, Outerwear, Tracksuit) use Django's Multi-Table Inheritance pattern:

- `BaseItem`: Common fields and behavior for all items
- Specific models: Item-type-specific fields and logic
- One-to-one relationship between `BaseItem` and specific item models

See [Architecture Decision Records](docs/ARCHITECTURE/decisions/) for design rationale.

### Technology Stack

- **Backend**: Django 5.0+ with Django REST Framework
- **Database**: PostgreSQL
- **Cache**: Redis
- **Task Queue**: Celery
- **Frontend**: Django Templates with Cotton Components, Bootstrap 5, Alpine.js, HTMX
- **API Documentation**: drf-spectacular (OpenAPI/Swagger)

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 14+
- Redis 6+

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/sunr4y/FootyCollect.git
   cd FootyCollect/footycollect
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements/local.txt
   ```

4. **Set up environment variables**:
   ```bash
   cp .envs/.local/.django .envs/.local/.django.local
   cp .envs/.local/.postgres .envs/.local/.postgres.local
   # Edit the .local files with your configuration
   ```

5. **Run migrations**:
   ```bash
   python manage.py migrate
   ```

6. **Create a superuser**:
   ```bash
   python manage.py createsuperuser
   ```

7. **Collect static files**:
   ```bash
   python manage.py collectstatic --noinput
   ```

8. **Start the development server**:
   ```bash
   python manage.py runserver
   ```

The application will be available at `http://127.0.0.1:8000`

### Docker Setup

For a complete development environment with all services:

```bash
docker compose -f docker-compose.local.yml up
```

This starts:
- Django application
- PostgreSQL database
- Redis cache
- Celery worker
- Celery beat
- Mailpit (email testing)

## Development

### Project Structure

```
footycollect/
├── config/              # Django settings and configuration
│   ├── settings/        # Environment-specific settings
│   └── checks.py        # Production validation checks
├── footycollect/        # Main application code
│   ├── api/            # API client for external services
│   ├── collection/     # Collection app (items, photos, etc.)
│   ├── core/           # Core models (clubs, seasons, etc.)
│   └── users/          # User management
├── deploy/             # Production deployment files
├── docs/               # Sphinx documentation
└── tests/              # Test suite
```

### Code Quality

- **Linting**: Ruff for code formatting and linting
- **Type Checking**: mypy for static type analysis
- **Testing**: pytest with coverage reporting

Run quality checks:

```bash
# Format code
ruff format .

# Lint code
ruff check .

# Type checking
mypy footycollect

# Run tests
pytest
```

### Database Migrations

Create migrations:
```bash
python manage.py makemigrations
```

Apply migrations:
```bash
python manage.py migrate
```

### Celery Tasks

Start Celery worker:
```bash
celery -A config.celery_app worker -l info
```

Start Celery beat (periodic tasks):
```bash
celery -A config.celery_app beat
```

## API Documentation

Interactive API documentation is available at:

- **Swagger UI**: `/api/docs/` (development only)
- **OpenAPI Schema**: `/api/schema/`

The API uses OpenAPI 3.0 specification generated by drf-spectacular. All endpoints are documented with request/response schemas, authentication requirements, and examples.

### API Endpoints

- `/api/` - Internal server APIs (DRF)
- `/fkapi/` - External API proxy endpoints

See [API Documentation](docs/ARCHITECTURE/api_documentation.md) for detailed endpoint documentation.

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
coverage run -m pytest
coverage html
open htmlcov/index.html

# Run specific test file
pytest footycollect/collection/tests/test_models.py
```

### Test Structure

Tests are organized by app and functionality:
- `test_models.py` - Model tests
- `test_views.py` - View tests
- `test_services.py` - Service layer tests
- `test_forms.py` - Form validation tests

## Deployment

FootyCollect can be deployed to any VPS or cloud platform. See the [Deployment Guide](deploy/README.md) for detailed instructions.

### Production Checklist

- [ ] Set `DEBUG=False` in production settings
- [ ] Configure `ALLOWED_HOSTS`
- [ ] Set secure `SECRET_KEY`
- [ ] Configure database connection
- [ ] Set up Redis for caching
- [ ] Configure static file serving
- [ ] Set up SSL/TLS certificates
- [ ] Configure email backend
- [ ] Set up monitoring (Sentry)
- [ ] Run production checks: `python manage.py check --deploy`

### Environment Variables

Required production environment variables:

- `DJANGO_SECRET_KEY` - Django secret key
- `DATABASE_URL` - PostgreSQL connection string
- `REDIS_URL` - Redis connection string
- `DJANGO_ALLOWED_HOSTS` - Comma-separated list of allowed hosts
- `FKA_API_IP` - Football Kit Archive API IP
- `API_KEY` - API key for external services

See `deploy/env.example` for a complete list.

## Documentation

### Available Documentation

- [Architecture Overview](docs/ARCHITECTURE/system_design.md)
- [API Documentation](docs/ARCHITECTURE/api_documentation.md)
- [Service Layer Design](docs/ARCHITECTURE/system_design.md#service-layer)
- [Multi-Table Inheritance](docs/ARCHITECTURE/decisions/0001-multi-table-inheritance.md)
- [Deployment Guide](deploy/README.md)
- [Development Setup](docs/DEVELOPMENT/setup_guide.md)
- [Coding Standards](docs/DEVELOPMENT/coding_standards.md)

### Architecture Decision Records (ADRs)

ADRs document key architectural decisions:

- [0001: Multi-Table Inheritance for Items](docs/ARCHITECTURE/decisions/0001-multi-table-inheritance.md)
- [0002: Service Layer Pattern](docs/ARCHITECTURE/decisions/0002-service-layer-pattern.md)

### Generating Documentation

Sphinx documentation can be built and served:

```bash
docker compose -f docker-compose.local.yml up docs
```

Documentation will be available at `http://127.0.0.1:7000`

## Contributing

1. Create a feature branch
2. Make your changes
3. Run tests and linting
4. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Support

For issues and questions:
- GitHub Issues: https://github.com/sunr4y/FootyCollect/issues
- Documentation: See `docs/` directory
