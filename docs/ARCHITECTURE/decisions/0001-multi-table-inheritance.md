# ADR 0001: Multi-Table Inheritance for Item Types

## Status

Accepted

## Context

FootyCollect needs to support multiple types of football memorabilia items (jerseys, shorts, outerwear, tracksuits) that share common attributes (name, description, photos, user ownership) but also have type-specific fields (jersey number, shorts size, outerwear type, etc.).

We needed to choose a data modeling approach that:
- Allows code reuse for common functionality
- Supports type-specific fields and behavior
- Maintains good query performance
- Is maintainable and extensible

## Decision

We use Django's Multi-Table Inheritance (MTI) pattern with a `BaseItem` model and separate models for each item type.

### Structure

```python
BaseItem (abstract base)
├── Jersey (OneToOne with BaseItem)
├── Shorts (OneToOne with BaseItem)
├── Outerwear (OneToOne with BaseItem)
└── Tracksuit (OneToOne with BaseItem)
```

### Implementation

- `BaseItem`: Contains all common fields (name, description, user, photos, etc.)
- Specific models: Each item type has a `OneToOneField` to `BaseItem` as primary key
- `item_type` field: String field on `BaseItem` to identify the specific type
- Custom managers: `BaseItemManager` for base queries, `MTIManager` for type-specific queries

## Consequences

### Advantages

1. **Clear Separation**: Common and type-specific fields are clearly separated
2. **Type Safety**: Each item type has its own model with type-specific fields
3. **Query Flexibility**: Can query all items via `BaseItem` or specific types
4. **Extensibility**: Easy to add new item types without modifying existing code
5. **Django ORM Support**: Works well with Django's ORM and admin

### Disadvantages

1. **JOIN Queries**: Accessing type-specific fields requires JOINs
2. **Complexity**: More complex than single-table inheritance
3. **Migration Overhead**: Adding fields requires migrations on multiple tables

### Mitigation

- Use `select_related()` for efficient JOIN queries
- Custom managers handle common query patterns
- Service layer abstracts complexity from views

## Examples

### Creating an Item

```python
# Create base item
base = BaseItem.objects.create(
    name="2023 Home Jersey",
    user=user,
    item_type="jersey"
)

# Create specific item
jersey = Jersey.objects.create(
    base_item=base,
    player_name="Messi",
    number=10
)
```

### Querying Items

```python
# All items
all_items = BaseItem.objects.all()

# Specific type
jerseys = Jersey.objects.all()

# With type-specific fields
jerseys_with_number = Jersey.objects.select_related('base_item').filter(number=10)
```

## References

- [Django Multi-Table Inheritance](https://docs.djangoproject.com/en/stable/topics/db/models/#multi-table-inheritance)
- [Django Model Inheritance Patterns](https://docs.djangoproject.com/en/stable/topics/db/models/#model-inheritance)
