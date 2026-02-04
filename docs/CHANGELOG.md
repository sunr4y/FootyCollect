# Changelog

All notable changes to this project are documented in this file.

## [0.9.1] - 2026-02-04

### Fixed
- SonarQube: refactored view methods to return context explicitly (crud_views, jersey_views)
- SonarQube: simplified get_form_class and unified form_valid return in crud_views
- SonarQube: avoid logging user-controlled data (log lengths/keys and exception type name only)
- SonarQube: removed redundant condition in clean_secondary_colors (QueryDict always has getlist)
- SonarQube: reduced cognitive complexity in _resolve_season (extracted _parse_season_years, _get_or_create_season_by_name)
- SonarQube: defined URL_NAME_ITEM_LIST and CHECKBOX_TOGGLE_CLASS constants
- SonarQube: test assertions corrected (len(output) >= 0 replaced with len(output) > 0 or removed)

### Changed
- item_detail.html: inline onclick/onload/onerror moved to addEventListener (accessibility)
- item_detail.html: status feedback uses <output>; spinners use aria-hidden="true"
- item_form.html: labels associated with controls via for; button groups use span + aria-labelledby

## [0.9.0] - 2026-01-30

### Added
- Complete UI redesign with dark theme and animated jersey cards
- Global kits discovery feed with advanced filtering (brand, club, competition, kit type)
- Redis caching for ItemListView (5min TTL, per-user+page keys)
- Template fragment caching for expensive sections
- Celery background task processing with Redis broker
- AVIF image conversion in background with status tracking
- Scheduled cleanup tasks (orphaned photos every 6h/7d/1d)
- Cloudflare R2 object storage support (alternative to S3)
- migrate_photos_to_remote management command for storage migration
- Local logo caching with AVIF conversion and proxy image view
- Content Security Policy (CSP) with configurable image/script/style sources
- Rate limiting: 100 req/hour on FKAPI + configurable DRF throttles
- X-RateLimit-Limit, X-RateLimit-Remaining, Retry-After headers on 429 responses
- SameSite cookie attributes for session/CSRF cookies
- SecurityHeadersMiddleware with X-Content-Type-Options, X-Frame-Options, X-XSS-Protection
- Audit logging middleware for security events
- E2E tests with Selenium Docker service in CI
- Comprehensive backend tests (API endpoints, models, commands)
- Query optimization tests with N+1 detection (test_item_list_view_query_count_bounded)
- verify_staticfiles management command for pre-deployment checks
- Docker multi-stage build with .dockerignore optimization
- setup_beat_schedule management command for periodic task configuration
- Django 4.2+ collectstatic with S3/R2 support
- ItemQuickViewView for modal quick view of items
- populate_user_collection management command for FKA imports
- UserItemListView at /users/<username>/items/ with permission checks
- fetch_home_kits management command with CDN support
- Item quick view modal integration in feed and item list
- New UI components: alerts, buttons, badges, cards
- Signup template with dark theme
- Custom "Remember me" checkbox with styled appearance
- Get Started CTA buttons with equal width layout
- Responsive home page (3-4 columns) with loading screen
- Logo pagination link to collection in home page
- View full collection link from user profile
- Recent items section on user profile with consistent styling
- Discover Kits navbar link next to Collection
- backfill_logos management command for logo pre-caching
- proxy image view for external images with referer protection
- Logo extraction and storage for clubs and brands
- logo_display_url for consistent logo display across app

### Fixed
- Photo carousel display (CSS preventing items from showing)
- Carousel thumbnail navigation with 80x80px squares synchronized to slides
- Bootstrap JS loading by removing integrity attribute
- AVIF image 404 errors by checking file existence before returning URL
- Country code not being saved in FKAPI jersey creation
- main_color and secondary_colors not being saved in FKAPI flow
- Kit associations not being persisted during jersey creation
- Multiple competitions not being saved (now processes all from FKAPI response)
- Brand dark logo not being extracted from FKAPI data
- User mapping preventing duplicate users on FKA imports
- Empty collection handling in populate_user_collection
- Infinite scroll items not appearing on subsequent pages
- Item card content layout and styling
- Quick view modal padding and logo display cutoff
- Badge overflow and text wrapping issues
- Season lookup to use 'year' field instead of 'name'
- RelatedObjectDoesNotExist errors when accessing unsaved form instance fields
- TypeError when checking 'team' in Kit model instance
- Empty array handling for secondary_colors in JavaScript
- Form validation for color names vs IDs
- Responsive_image template tag to handle AVIF properly
- Item detail page title spacing and year styles
- Edit view now displays full kit data from FKAPI
- Edit view displays existing photos with reorder/delete capability
- Color selector components properly initialized in edit view
- Selenium E2E test localhost vs 0.0.0.0 compatibility
- Cross-Origin-Opener-Policy console warnings in tests
- Item name search improvements in E2E tests
- Test failure handling with proper getattr for response.url

### Changed
- Refactored jersey_views from ~1500 lines to <400 lines
- Extracted 5 dedicated view modules (list, detail, crud, jersey_crud, demo)
- Extracted 3 jersey view mixins (fkapi_data, entity_processing, form_data, kit_data_processing)
- Extracted PhotoProcessorMixin to dedicated module
- Refactored forms from 1230 lines to 126 lines (83% reduction)
- Extracted JerseyForm to forms_jersey_base.py
- Extracted JerseyFKAPIForm to forms_jersey_fkapi.py
- Extracted item forms to forms_items.py
- Created unified ItemFKAPIService (removed duplicate jersey_fkapi_service.py)
- Created dedicated FKAPIKitProcessor for kit-specific logic
- Cache configuration: DummyCache for DEBUG and test settings
- Cookie configuration: SESSION_COOKIE_SAMESITE and CSRF_COOKIE_SAMESITE (default Lax)
- Footer query optimization with prefetch_related
- ItemListView query optimization with prefetch base_item__tags
- ItemDetailView now prefetches related item types to avoid N+1
- Home page layout with animated jersey cards background
- Error page templates (403, 404, 500) with dark theme
- Login/logout templates with dark theme styling
- Feed infinite scroll selector to proper Array.from(newItemsGrid.children)
- Item collection view with UserItemListView
- User profile design unified with collection items page
- collection.css with shared styles for collection, user profile, feed
- All console.log statements removed (9+ files)
- All verbose logging removed from jersey_views and related files
- Pre-commit configuration more selective (file filters optimized)
- djLint restricted to footycollect templates
- Pip caching in pytest GitHub Actions job
- Celery eager execution for test environment
- boto3/botocore logging reduced to WARNING level
- Storage validation checks to support both S3 and R2

### Removed
- unused demo/test views
- jersey_fkapi_service.py (merged into ItemFKAPIService)
- Duplicate Pillow from requirements
- CSP and security middleware from #175 (re-implemented in #204 properly)
- All console.log debug statements
- Debug print() statements
- Commented-out code blocks
- Verbose logger.debug and logger.info from views/mixins

### Security
- Rate limiting on all FKAPI endpoints (100 requests/hour per IP)
- SecurityHeadersMiddleware with comprehensive headers
- SecurityAuditMiddleware for security event logging
- Content Security Policy configuration (django-csp 4.0)
- 429.html template for rate limit errors
- X-RateLimit headers on API responses
- SameSite cookie attributes (Lax by default)
- Input validation and escaping in responsive_image tag
- Feed seed validation using ORM
- External image URL validation
- ALLOWED_EXTERNAL_IMAGE_HOSTS configuration
- Auth requirement for dropzone upload
- Narrow task exception handling
- CSP headers: img-src, script-src, style-src, font-src, connect-src, frame-ancestors, form-action
- Referrer-Policy and Permissions-Policy headers

### Dependencies
- Added: celery, django-celery-beat, redis, django-csp
- Updated: Pillow (image processing)
- Updated env.example with 20+ new environment variables

### Database Migrations
- New is_processing_photos BooleanField on BaseItem
- New logo_file, logo_dark_file FileField on Club and Brand
- All migrations are safe and non-destructive

### Tests
- 750+ total tests passing (up from 673)
- Added E2E tests with Selenium in CI
- Added comprehensive backend tests (API, models, commands)
- Added query optimization tests with N+1 detection
- Added 12 security tests for headers and CSP
- All pytest checks passing
- All ruff linting passing
- All djLint checks passing

### Issues Closed
Closes #165, #166, #117, #151, #177, #171, #160, #194, #119, #193, #132, #192, #149, #121, #150, #152, #162, #191

---

## [] - Previous release NONE
