# ADR 0002: Service Layer Pattern

## Status

Accepted

## Context

FootyCollect has complex business logic that involves:
- Multiple model interactions
- External API integration
- Image processing
- Transaction management
- Error handling

Views were becoming bloated with business logic, making the code hard to test and maintain.

## Decision

We implement a Service Layer pattern to encapsulate business logic, keeping views thin and focused on HTTP concerns.

### Structure

```
footycollect/collection/services/
├── __init__.py              # Service registry
├── service_registry.py      # Service factory pattern
├── item_service.py          # Item CRUD operations
├── photo_service.py         # Photo management
├── collection_service.py    # Collection operations
├── item_fkapi_service.py   # External API integration
└── ...
```

### Principles

1. **Single Responsibility**: Each service handles one domain concern
2. **Stateless**: Services are stateless classes, instantiated per operation
3. **Transaction Management**: Services handle database transactions
4. **Error Handling**: Services raise domain-specific exceptions
5. **Testability**: Services are easily testable in isolation

## Implementation

### Service Registry Pattern

Services are accessed through a registry to enable:
- Dependency injection
- Testing with mocks
- Service replacement

```python
from footycollect.collection.services import get_item_service

item_service = get_item_service()
item = item_service.create_item(user, data)
```

### Service Interface

All services follow a consistent interface:

```python
class ItemService:
    def create_item(self, user, data):
        """Create a new item with validation and related objects."""
        with transaction.atomic():
            # Business logic here
            pass
    
    def update_item(self, item, data):
        """Update an existing item."""
        pass
    
    def delete_item(self, item):
        """Delete an item and related objects."""
        pass
```

## Consequences

### Advantages

1. **Separation of Concerns**: Views handle HTTP, services handle business logic
2. **Reusability**: Services can be used from views, management commands, tasks
3. **Testability**: Business logic can be tested without HTTP layer
4. **Maintainability**: Changes to business logic are localized
5. **Transaction Management**: Services handle complex transactions

### Disadvantages

1. **Additional Layer**: More code to maintain
2. **Learning Curve**: Team needs to understand service pattern
3. **Potential Over-Engineering**: Simple operations might not need services

### Mitigation

- Use services for complex operations, keep simple CRUD in views
- Document service usage patterns
- Provide examples in documentation

## Examples

### View Using Service

```python
class JerseyCreateView(CreateView):
    def form_valid(self, form):
        item_service = get_item_service()
        item = item_service.create_item(
            user=self.request.user,
            data=form.cleaned_data
        )
        return redirect(item)
```

### Service Implementation

```python
class ItemService:
    def create_item(self, user, data):
        with transaction.atomic():
            base_item = BaseItem.objects.create(
                user=user,
                name=data['name'],
                # ... other fields
            )
            jersey = Jersey.objects.create(
                base_item=base_item,
                player_name=data.get('player_name'),
                # ... jersey-specific fields
            )
            return jersey
```

## References

- [Service Layer Pattern](https://martinfowler.com/eaaCatalog/serviceLayer.html)
- [Django Service Layer Example](https://www.cosmicpython.com/book/chapter_02_repository.html)
