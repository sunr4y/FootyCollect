# Migration to Multi-Table Inheritance (MTI)

## Overview

This document outlines the migration from the current abstract `BaseItem` model to Multi-Table Inheritance (MTI) structure.

## Current Structure (Abstract Inheritance)

```
BaseItem (abstract)
├── Jersey
├── Shorts
├── Outerwear
├── Tracksuit
├── Pants
└── OtherItem
```

**Problems:**
- Each model has its own table with all fields duplicated
- No shared table for common fields
- Difficult to query across all item types
- Inefficient storage and queries

## New Structure (Multi-Table Inheritance)

```
BaseItem (concrete table)
├── Jersey (OneToOneField to BaseItem)
├── Shorts (OneToOneField to BaseItem)
├── Outerwear (OneToOneField to BaseItem)
├── Tracksuit (OneToOneField to BaseItem)
├── Pants (OneToOneField to BaseItem)
└── OtherItem (OneToOneField to BaseItem)
```

**Benefits:**
- Common fields stored in `BaseItem` table
- Specific fields stored in child tables
- Better query performance
- Easier to query across all item types
- More efficient storage

## Key Changes

### 1. BaseItem Model Changes

**Before:**
```python
class BaseItem(models.Model):
    class Meta:
        abstract = True  # No table created
```

**After:**
```python
class BaseItem(models.Model):
    item_type = models.CharField(max_length=20, choices=ITEM_TYPE_CHOICES)
    name = models.CharField(max_length=200)
    # ... other common fields

    class Meta:
        # No abstract = True, so table is created
        ordering = ["-created_at"]
```

### 2. Child Model Changes

**Before:**
```python
class Jersey(BaseItem):
    # Inherits all BaseItem fields
    kit = models.ForeignKey(Kit, ...)
    size = models.ForeignKey(Size, ...)
    # ... other jersey fields
```

**After:**
```python
class Jersey(models.Model):
    base_item = models.OneToOneField(
        BaseItem,
        on_delete=models.CASCADE,
        related_name='jersey',
        primary_key=True
    )
    # Only jersey-specific fields
    kit = models.ForeignKey(Kit, ...)
    size = models.ForeignKey(Size, ...)
    # ... other jersey fields
```

## Migration Strategy

### Phase 1: Create New Models
1. Create `models_mti.py` with new structure
2. Test new models in isolation
3. Create data migration scripts

### Phase 2: Data Migration
1. Create migration to add new tables
2. Migrate existing data from old structure to new structure
3. Verify data integrity

### Phase 3: Update Code
1. Update forms to work with new structure
2. Update views to use new models
3. Update templates if needed
4. Update tests

### Phase 4: Cleanup
1. Remove old models
2. Remove old migrations
3. Update documentation

## Data Migration Script

```python
# management/commands/migrate_to_mti.py
from django.core.management.base import BaseCommand
from django.db import transaction

class Command(BaseCommand):
    def handle(self, *args, **options):
        with transaction.atomic():
            # Migrate Jersey data
            for old_jersey in OldJersey.objects.all():
                # Create BaseItem
                base_item = BaseItem.objects.create(
                    item_type='jersey',
                    name=old_jersey.name or f"{old_jersey.brand} {old_jersey.club} Jersey",
                    user=old_jersey.user,
                    brand=old_jersey.brand,
                    club=old_jersey.club,
                    # ... copy all common fields
                )

                # Create Jersey
                Jersey.objects.create(
                    base_item=base_item,
                    kit=old_jersey.kit,
                    size=old_jersey.size,
                    # ... copy jersey-specific fields
                )

            # Repeat for other item types...
```

## Code Changes Required

### 1. Forms
```python
# Before
class JerseyForm(forms.ModelForm):
    class Meta:
        model = Jersey
        fields = ['name', 'brand', 'club', 'size', ...]

# After
class JerseyForm(forms.ModelForm):
    class Meta:
        model = Jersey
        fields = ['size', 'kit', 'is_fan_version', ...]  # Only jersey fields

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Handle BaseItem fields separately
```

### 2. Views
```python
# Before
def create_jersey(request):
    if request.method == 'POST':
        form = JerseyForm(request.POST)
        if form.is_valid():
            jersey = form.save()
            return redirect('jersey_detail', pk=jersey.pk)

# After
def create_jersey(request):
    if request.method == 'POST':
        form = JerseyForm(request.POST)
        base_form = BaseItemForm(request.POST)
        if form.is_valid() and base_form.is_valid():
            base_item = base_form.save()
            jersey = form.save(commit=False)
            jersey.base_item = base_item
            jersey.save()
            return redirect('jersey_detail', pk=base_item.pk)
```

### 3. Queries
```python
# Before
jerseys = Jersey.objects.filter(user=user)

# After
jerseys = BaseItem.objects.filter(user=user, item_type='jersey')
# Or
jerseys = Jersey.objects.select_related('base_item').filter(base_item__user=user)
```

## Testing Strategy

1. **Unit Tests**: Test each model individually
2. **Integration Tests**: Test forms and views with new structure
3. **Data Migration Tests**: Test migration scripts
4. **Performance Tests**: Compare query performance

## Rollback Plan

1. Keep old models as backup
2. Create rollback migration script
3. Test rollback procedure
4. Document rollback steps

## Timeline

- **Week 1**: Create new models and test structure
- **Week 2**: Create data migration scripts
- **Week 3**: Update forms and views
- **Week 4**: Testing and deployment

## Risks and Mitigation

**Risk**: Data loss during migration
**Mitigation**: Comprehensive backups and testing

**Risk**: Performance issues
**Mitigation**: Performance testing and optimization

**Risk**: Breaking existing functionality
**Mitigation**: Extensive testing and gradual rollout
