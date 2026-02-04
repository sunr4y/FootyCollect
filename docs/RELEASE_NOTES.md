# FootyCollect Release Notes - Version 0.9.1

**Release Date:** January 31, 2026  
**Status:** ✅ Stable Release

---

## Overview

Patch release focused on code quality (SonarQube findings) and accessibility improvements. No new features or breaking changes.

---

## Code Quality (SonarQube)

- Refactored view methods to return context explicitly and reduce complexity
- Simplified `get_form_class` and unified `form_valid` return paths in CRUD views
- Replaced user-controlled data in logs (length/counts and exception type names only)
- Fixed redundant condition in `clean_secondary_colors` (QueryDict always has `getlist`)
- Reduced cognitive complexity in `_resolve_season` via extracted helpers
- Introduced constants for repeated literals (`URL_NAME_ITEM_LIST`, `CHECKBOX_TOGGLE_CLASS`)
- Corrected test assertions: removed redundant `len(output) >= 0` checks

---

## Accessibility

- **item_detail.html:** Moved inline `onclick` from Retry buttons and thumbnails to `addEventListener`; moved image `onload`/`onerror` to JS with `data-fallback-src` and `data-hide-on-error`
- **item_detail.html:** Replaced `div` with `role="status"` by `<output>`; spinners use `aria-hidden="true"`
- **item_form.html:** Associated form labels with controls via `for`; button groups use `<span>` + `aria-labelledby` for correct semantics

---

## Getting Started

No new env vars or commands. Upgrade as usual: pull, migrate if needed, restart app and workers.

---

# FootyCollect Release Notes - Version 0.9.0

**Release Date:** January 30, 2026  
**Status:** ✅ Stable Release  
**Total Changes:** 30 PRs, 108 commits

---

## Overview

Version 0.9 is our first stable release with proper changelog management. Major milestone featuring complete UI redesign, global kits feed, Redis caching, security hardening, and background task processing.

---

## Major Features

### 🎨 Complete UI Redesign
- Modern dark theme with animated jersey cards
- Redesigned home page with bulk kits display
- Improved error pages (403, 404, 500)
- Enhanced auth flows (signup, login)
- New UI components: alerts, buttons, badges, cards
- Responsive layout optimizations

### 🌍 Global Kits Feed
- Browse and discover football kits from community
- Advanced filtering: brand, club, competition, kit type
- Quick view modal for kit details
- Integration with FootballKitArchive API
- Infinite scroll pagination


### ⚡ Performance Optimization
- Redis caching for ItemListView (5min TTL)
- Eliminated N+1 queries in list views
- Template fragment caching
- Query optimization with prefetch_related
- CI/CD pip caching

### 🔐 Security Enhancements
- Rate limiting: 100 req/hour on FKAPI endpoints
- Content Security Policy (CSP) headers
- Security headers: X-Content-Type-Options, X-Frame-Options, X-XSS-Protection
- SameSite cookie attributes
- Audit logging middleware
- Rate limit headers on API responses

### ⚙️ Background Task Processing
- Celery integration with Redis broker
- Async AVIF image conversion
- Photo processing status tracking
- Scheduled maintenance tasks
- Real-time frontend polling

### ☁️ Cloud Storage & CDN
- Cloudflare R2 support (alternative to S3)
- Photo migration tools
- Local logo caching with AVIF
- Proxy image view for external images
- Custom domain support for CDN

### 📦 Code Quality
- Massive refactoring: 5000+ lines
- Extracted 20+ new modules
- jersey_views: 1500→400 lines (-73%)
- forms: 1230→126 lines (-89%)
- Unified FKAPI service layer

---

## Bug Fixes

- FKAPI jersey creation - country/colors/kit/competitions (#177, #178, #179)
- Edit view missing kit data and photos (#160)
- Infinite scroll pagination (#209)
- Brand logo handling (#181)
- User mapping preventing duplicates (#195)
- AVIF image 404 errors (#178)
- UI polish and styling (#209)

---

## Statistics

| Metric | Value |
|--------|-------|
| PRs Merged | 30 |
| Commits | 108 |
| Tests Passing | 750+ |
| Issues Closed | 18 |
| Lines Refactored | 5000+ |
| New Modules | 20+ |
| Breaking Changes | 0 |

---

## Getting Started

### New Management Commands
```bash
python manage.py fetch_home_kits
python manage.py populate_user_collection <username>
python manage.py setup_beat_schedule
python manage.py verify_staticfiles
python manage.py migrate_photos_to_remote
python manage.py backfill_logos
```

### New Management Commands

```bash
DJANGO_DRF_USER_THROTTLE_RATE=1000/hour
DJANGO_DRF_ANON_THROTTLE_RATE=100/hour
DJANGO_CSP_IMG_SRC='self' cdn.example.com
DJANGO_CSP_SCRIPT_SRC='self'
DJANGO_SESSION_COOKIE_SAMESITE=Lax
CLOUDFLARE_R2_CUSTOM_DOMAIN=https://cdn.example.com

```

### Deployment Steps

```bash
# Migrations
python manage.py migrate

# Setup periodic tasks
python manage.py setup_beat_schedule

# Pre-fetch kits
python manage.py fetch_home_kits

# Collect static files
python manage.py collectstatic --noinput

# Start Celery
celery -A config worker -l info &
celery -A config beat -l info &

```

### New Management Commands

```bash
```