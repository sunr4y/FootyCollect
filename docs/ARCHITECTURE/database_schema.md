# Database Schema Documentation

## Overview

FootyCollect uses PostgreSQL as the primary database. The schema is designed to support multiple item types while maintaining data integrity and query performance.

## Core Models

### BaseItem

The foundation model for all collection items.

**Table**: `collection_baseitem`

**Fields**:
- `id` (Primary Key)
- `name` (CharField, max_length=255)
- `description` (TextField, optional)
- `user` (ForeignKey to User)
- `item_type` (CharField) - Type identifier: 'jersey', 'shorts', 'outerwear', 'tracksuit'
- `is_private` (BooleanField) - Privacy flag
- `is_draft` (BooleanField) - Draft status
- `main_img_url` (URLField, optional) - External image URL
- `created_at` (DateTimeField, auto_now_add)
- `updated_at` (DateTimeField, auto_now)

**Indexes**:
- `user_id` + `item_type`
- `is_private` + `is_draft`
- `created_at`

**Relationships**:
- One-to-One with `Jersey`, `Shorts`, `Outerwear`, `Tracksuit`
- Many-to-Many with `Competition`
- Foreign Key to `Club` (team)
- Foreign Key to `Season`
- Foreign Key to `Brand`
- Foreign Key to `TypeK` (kit type)
- Generic Foreign Key to `Photo`

### Jersey

Jersey-specific model using Multi-Table Inheritance.

**Table**: `collection_jersey`

**Fields**:
- `base_item` (OneToOneField to BaseItem, Primary Key)
- `player_name` (CharField, max_length=100, optional)
- `number` (PositiveIntegerField, optional)
- `is_short_sleeve` (BooleanField, default=True)

**Relationships**:
- One-to-One with `BaseItem`

### Shorts

Shorts-specific model.

**Table**: `collection_shorts`

**Fields**:
- `base_item` (OneToOneField to BaseItem, Primary Key)
- `size` (ForeignKey to Size)
- `number` (PositiveIntegerField, optional)
- `is_fan_version` (BooleanField, default=True)

### Outerwear

Outerwear-specific model.

**Table**: `collection_outerwear`

**Fields**:
- `base_item` (OneToOneField to BaseItem, Primary Key)
- `type` (CharField) - Choices: 'hoodie', 'jacket', 'windbreaker', 'crewneck'
- `size` (ForeignKey to Size)

### Tracksuit

Tracksuit-specific model.

**Table**: `collection_tracksuit`

**Fields**:
- `base_item` (OneToOneField to BaseItem, Primary Key)
- `size` (ForeignKey to Size)

## Core App Models

### Club

Football club/team information.

**Table**: `core_club`

**Fields**:
- `id` (Primary Key)
- `name` (CharField, max_length=255)
- `slug` (SlugField, unique)
- `country` (CountryField)
- `logo` (URLField, optional)
- `logo_dark` (URLField, optional)

**Indexes**:
- `slug`
- `name`

### Season

Football season information.

**Table**: `core_season`

**Fields**:
- `id` (Primary Key)
- `year` (CharField, max_length=9) - Format: "2023-24"
- `first_year` (CharField, max_length=4)
- `second_year` (CharField, max_length=4)

**Indexes**:
- `year`

### Competition

Football competition/league information.

**Table**: `core_competition`

**Fields**:
- `id` (Primary Key)
- `name` (CharField, max_length=255)
- `slug` (SlugField, unique)
- `logo` (URLField, optional)
- `logo_dark` (URLField, optional)

**Indexes**:
- `slug`

### Brand

Kit manufacturer/brand information.

**Table**: `core_brand`

**Fields**:
- `id` (Primary Key)
- `name` (CharField, max_length=255)
- `slug` (SlugField, unique)
- `logo` (URLField, optional)
- `logo_dark` (URLField, optional)

**Indexes**:
- `slug`

### TypeK

Kit type (Home, Away, Third, etc.).

**Table**: `core_typek`

**Fields**:
- `id` (Primary Key)
- `name` (CharField, max_length=50)

## Supporting Models

### Photo

Generic photo model for items.

**Table**: `collection_photo`

**Fields**:
- `id` (Primary Key)
- `content_type` (ForeignKey to ContentType)
- `object_id` (PositiveIntegerField)
- `content_object` (GenericForeignKey)
- `image` (ImageField)
- `image_avif` (ImageField, optional) - Optimized AVIF version
- `caption` (CharField, max_length=255, optional)
- `order` (PositiveIntegerField, default=0)
- `uploaded_at` (DateTimeField, auto_now_add)
- `user` (ForeignKey to User, optional)

**Indexes**:
- `content_type` + `object_id`
- `order`
- `user_id`

**Relationships**:
- Generic Foreign Key to any model (BaseItem, etc.)

### Size

Size information for items.

**Table**: `collection_size`

**Fields**:
- `id` (Primary Key)
- `name` (CharField, max_length=50) - e.g., "S", "M", "L", "XL"
- `category` (CharField) - Choices: 'jersey', 'shorts', 'outerwear', 'tracksuit'

**Indexes**:
- `category` + `name`

### Color

Color information.

**Table**: `collection_color`

**Fields**:
- `id` (Primary Key)
- `name` (CharField, max_length=100, unique)
- `hex_value` (CharField, max_length=7) - Hexadecimal color value

**Indexes**:
- `name`

## Entity Relationship Diagram

```
BaseItem
├── OneToOne → Jersey
├── OneToOne → Shorts
├── OneToOne → Outerwear
├── OneToOne → Tracksuit
├── ForeignKey → User
├── ForeignKey → Club (team)
├── ForeignKey → Season
├── ForeignKey → Brand
├── ForeignKey → TypeK
├── ManyToMany → Competition
└── GenericRelation → Photo

Photo
├── GenericForeignKey → BaseItem (or other models)
└── ForeignKey → User

Jersey, Shorts, Outerwear, Tracksuit
└── OneToOne → BaseItem (primary_key=True)
```

## Database Indexes

### Performance Indexes

1. **BaseItem Queries**:
   - `(user_id, item_type)` - User's items by type
   - `(is_private, is_draft)` - Public/draft filtering
   - `created_at` - Chronological ordering

2. **Photo Queries**:
   - `(content_type_id, object_id)` - Generic foreign key lookups
   - `order` - Photo ordering

3. **Lookup Tables**:
   - `slug` indexes on Club, Competition, Brand
   - `name` indexes for text searches

## Migration Strategy

### Multi-Table Inheritance

When adding new item types:

1. Create new model with `OneToOneField` to `BaseItem`
2. Add new `item_type` choice to `BaseItem.ITEM_TYPE_CHOICES`
3. Update `BaseItem.save()` if needed for type-specific logic
4. Create migration for new model

### Adding Fields

- Common fields: Add to `BaseItem`
- Type-specific fields: Add to specific model (Jersey, Shorts, etc.)

## Query Patterns

### Get All Items for User

```python
BaseItem.objects.filter(user=user)
```

### Get Specific Item Type

```python
Jersey.objects.select_related('base_item').filter(base_item__user=user)
```

### Get Items with Related Data

```python
BaseItem.objects.select_related(
    'team', 'season', 'brand', 'type'
).prefetch_related(
    'competition', 'photos'
).filter(user=user)
```

## Data Integrity

### Constraints

- `BaseItem.item_type` must match the related model type
- `Jersey.base_item.item_type` must be 'jersey'
- Cascade deletes: Deleting `BaseItem` deletes related specific model
- Unique constraints on slugs for Club, Competition, Brand

### Validation

- `item_type` validation in model `save()` methods
- Photo order validation
- Size category validation

## Backup and Recovery

### Backup Strategy

- Daily automated backups
- Point-in-time recovery enabled
- Backup retention: 30 days

### Recovery Procedures

See [Operations Documentation](../OPERATIONS/maintenance.md) for detailed recovery procedures.
