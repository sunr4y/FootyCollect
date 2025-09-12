# Service Layer Architecture

This directory contains the service layer implementation for the FootyCollect application. The service layer provides a clean separation between the presentation layer (views) and the data layer (models/repositories).

## Architecture Overview

The service layer follows these principles:

1. **Single Responsibility**: Each service handles one specific domain
2. **Dependency Injection**: Services can be easily mocked for testing
3. **Business Logic Encapsulation**: Complex business operations are encapsulated in services
4. **Repository Pattern**: Services use repositories for data access

## Service Structure

### Core Services

- **`CollectionService`**: Main facade service that orchestrates operations across multiple services
- **`ItemService`**: Handles business logic for items (jerseys, etc.)
- **`PhotoService`**: Manages photo-related operations
- **`ColorService`**: Handles color management and statistics
- **`SizeService`**: Manages size-related operations

### Service Registry

The `ServiceRegistry` provides dependency injection capabilities:

```python
from footycollect.collection.services import get_collection_service

# Get service instance
collection_service = get_collection_service()
```

## Usage Examples

### Basic Service Usage

```python
from footycollect.collection.services import get_item_service, get_color_service

# Get services
item_service = get_item_service()
color_service = get_color_service()

# Use services
items = item_service.get_user_items(user)
colors = color_service.get_colors_for_item_form()
```

### Collection Service (Facade)

```python
from footycollect.collection.services import get_collection_service

# Get main service
collection_service = get_collection_service()

# Get dashboard data
dashboard_data = collection_service.get_collection_dashboard_data(user)

# Search collection
results = collection_service.search_collection(user, "barcelona")
```

### Service Registry for Testing

```python
from footycollect.collection.services import ServiceRegistry

# Create test registry
test_registry = ServiceRegistry()

# Register mock services
test_registry.register_service('item_service', MockItemService())
test_registry.register_service('color_service', MockColorService())

# Use in tests
item_service = test_registry.get_item_service()
```

## Service Methods

### ItemService

- `get_user_items(user)`: Get all items for a user
- `get_public_items()`: Get all public items
- `search_items(user, query, filters)`: Search items
- `create_item(user, item_data)`: Create new item
- `update_item(item, item_data)`: Update existing item
- `delete_item(item)`: Delete item
- `get_item_analytics(user)`: Get item analytics

### PhotoService

- `create_photo(item, photo_file)`: Create photo for item
- `update_photo(photo, photo_data)`: Update photo
- `delete_photo(photo_id)`: Delete photo
- `get_photos_for_item(item)`: Get all photos for item
- `get_photo_analytics()`: Get photo analytics

### ColorService

- `get_colors_for_item_form()`: Get colors for forms
- `get_color_statistics()`: Get color statistics
- `search_colors(query)`: Search colors
- `create_custom_color(name, hex_value)`: Create custom color
- `get_color_usage_analytics()`: Get usage analytics

### SizeService

- `get_sizes_for_item_form()`: Get sizes for forms
- `get_size_statistics()`: Get size statistics
- `search_sizes(query)`: Search sizes
- `create_custom_size(name, category)`: Create custom size
- `get_size_usage_analytics()`: Get usage analytics

### CollectionService (Facade)

- `get_collection_dashboard_data(user)`: Get dashboard data
- `get_collection_analytics(user)`: Get collection analytics
- `search_collection(user, query, filters)`: Search entire collection
- `get_collection_statistics()`: Get global statistics
- `create_item_with_photos(user, item_data, photo_files)`: Create item with photos
- `update_item_with_photos(item, item_data, photo_files, remove_photo_ids)`: Update item with photos

## Testing

Services are designed to be easily testable:

```python
from unittest.mock import Mock
from footycollect.collection.services import ItemService

def test_item_service():
    # Create mock repository
    mock_repository = Mock()

    # Create service with mock
    service = ItemService(item_repository=mock_repository)

    # Test service methods
    result = service.get_user_items(user)

    # Verify repository was called
    mock_repository.get_user_items.assert_called_once_with(user)
```

## Best Practices

1. **Always use services in views**: Don't access repositories directly from views
2. **Use the service registry**: For dependency injection and testing
3. **Keep services focused**: Each service should handle one domain
4. **Handle errors gracefully**: Services should handle and log errors appropriately
5. **Use type hints**: All service methods should have proper type hints
6. **Document complex operations**: Add docstrings for complex business logic

## Migration from Direct Model Access

To migrate from direct model access to services:

1. Replace `Model.objects.filter()` with service methods
2. Replace `Model.objects.create()` with service methods
3. Replace direct model operations with service operations
4. Update tests to use service mocks

Example migration:

```python
# Before (direct model access)
items = Jersey.objects.filter(user=user, is_draft=False)
color = Color.objects.get(name="Red")

# After (using services)
item_service = get_item_service()
color_service = get_color_service()

items = item_service.get_user_items(user)
color = color_service.get_color_by_name("Red")
```
