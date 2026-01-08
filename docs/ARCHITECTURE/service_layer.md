# Service Layer Architecture

## Overview

FootyCollect uses a Service Layer pattern to encapsulate business logic and keep views focused on HTTP concerns.

## Service Registry

Services are accessed through a centralized registry:

```python
from footycollect.collection.services import (
    get_item_service,
    get_photo_service,
    get_collection_service,
)
```

### Available Services

- `ItemService`: Item CRUD operations
- `PhotoService`: Photo upload, processing, and management
- `CollectionService`: Collection-level operations
- `ItemFKAPIService`: External API integration
- `ColorService`: Color management
- `SizeService`: Size management

## Service Interface

All services follow a consistent pattern:

### Stateless Design

Services are stateless classes, instantiated per operation:

```python
service = get_item_service()
item = service.create_item(user, data)
```

### Transaction Management

Services handle database transactions internally:

```python
class ItemService:
    def create_item(self, user, data):
        with transaction.atomic():
            # All database operations in transaction
            base_item = BaseItem.objects.create(...)
            jersey = Jersey.objects.create(...)
            return jersey
```

### Error Handling

Services raise domain-specific exceptions:

```python
class ItemService:
    def create_item(self, user, data):
        if not data.get('name'):
            raise ValueError("Item name is required")
        # ... create item
```

## Service Implementations

### ItemService

Handles item creation, updates, and deletion:

```python
item_service = get_item_service()

# Create item
item = item_service.create_item(user, {
    'name': '2023 Home Jersey',
    'item_type': 'jersey',
    # ... other fields
})

# Update item
item_service.update_item(item, {'name': 'Updated Name'})

# Delete item
item_service.delete_item(item)
```

### PhotoService

Manages photo uploads and processing:

```python
photo_service = get_photo_service()

# Upload photo
photo = photo_service.upload_photo(item, image_file)

# Create photo from URL
photo = photo_service.create_photo_from_url(item, url)

# Set main image
photo_service.set_main_image(item, photo)

# Delete photo
photo_service.delete_photo(photo)
```

### ItemFKAPIService

Integrates with external Football Kit Archive API:

```python
fkapi_service = ItemFKAPIService()

# Process item creation with FKAPI data
item = fkapi_service.process_item_creation(form, user, 'jersey')
```

## Using Services in Views

Views delegate business logic to services:

```python
class JerseyCreateView(CreateView):
    def form_valid(self, form):
        item_service = get_item_service()
        
        try:
            item = item_service.create_item(
                user=self.request.user,
                data=form.cleaned_data
            )
            messages.success(self.request, "Item created successfully")
            return redirect(item)
        except ValueError as e:
            messages.error(self.request, str(e))
            return self.form_invalid(form)
```

## Testing Services

Services are easily testable in isolation:

```python
def test_create_item():
    user = UserFactory()
    item_service = get_item_service()
    
    item = item_service.create_item(user, {
        'name': 'Test Jersey',
        'item_type': 'jersey',
    })
    
    assert item.base_item.name == 'Test Jersey'
    assert item.base_item.user == user
```

## Best Practices

1. **Keep Views Thin**: Views should only handle HTTP concerns
2. **Use Services for Complex Logic**: Simple CRUD can stay in views
3. **Handle Transactions in Services**: Services manage transaction boundaries
4. **Raise Domain Exceptions**: Use domain-specific exceptions for errors
5. **Test Services Independently**: Services should be testable without views

## Service Registry Implementation

The service registry uses a factory pattern:

```python
class ServiceRegistry:
    _services = {}
    
    @classmethod
    def register(cls, name, service_class):
        cls._services[name] = service_class
    
    @classmethod
    def get(cls, name):
        service_class = cls._services.get(name)
        if not service_class:
            raise ValueError(f"Service {name} not found")
        return service_class()

def get_item_service():
    return ServiceRegistry.get('item')
```

This allows for:
- Dependency injection
- Service mocking in tests
- Service replacement for different implementations
