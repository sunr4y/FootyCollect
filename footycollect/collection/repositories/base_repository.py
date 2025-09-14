"""
Base repository class implementing the Repository pattern.

This class provides common database operations and serves as a base
for all other repository classes in the application.
"""

from typing import Any, TypeVar

from django.db import models
from django.db.models import QuerySet

ModelType = TypeVar("ModelType", bound=models.Model)


class BaseRepository:
    """
    Base repository class that provides common database operations.

    This class implements the Repository pattern to abstract data access
    and provide a clean interface for database operations.
    """

    def __init__(self, model: type[ModelType]):
        """
        Initialize the repository with a Django model.

        Args:
            model: The Django model class this repository manages
        """
        self.model = model

    def get_by_id(self, pk: Any) -> ModelType | None:
        """
        Get a single object by its primary key.

        Args:
            pk: Primary key value

        Returns:
            Model instance or None if not found
        """
        try:
            return self.model.objects.get(pk=pk)
        except self.model.DoesNotExist:
            return None

    def get_by_field(self, field_name: str, value: Any) -> ModelType | None:
        """
        Get a single object by a specific field value.

        Args:
            field_name: Name of the field to filter by
            value: Value to match

        Returns:
            Model instance or None if not found
        """
        try:
            filter_kwargs = {field_name: value}
            return self.model.objects.get(**filter_kwargs)
        except self.model.DoesNotExist:
            return None

    def get_all(self) -> QuerySet[ModelType]:
        """
        Get all objects of this model type.

        Returns:
            QuerySet of all model instances
        """
        return self.model.objects.all()

    def filter(self, **kwargs) -> QuerySet[ModelType]:
        """
        Filter objects by given criteria.

        Args:
            **kwargs: Filter criteria

        Returns:
            QuerySet of filtered model instances
        """
        return self.model.objects.filter(**kwargs)

    def create(self, **kwargs) -> ModelType:
        """
        Create a new object with the given data.

        Args:
            **kwargs: Field values for the new object

        Returns:
            Created model instance
        """
        return self.model.objects.create(**kwargs)

    def update(self, pk: Any, **kwargs) -> ModelType | None:
        """
        Update an object by its primary key.

        Args:
            pk: Primary key value
            **kwargs: Field values to update

        Returns:
            Updated model instance or None if not found
        """
        try:
            obj = self.model.objects.get(pk=pk)
        except self.model.DoesNotExist:
            return None
        else:
            for field, value in kwargs.items():
                setattr(obj, field, value)
            obj.save()
            return obj

    def delete(self, pk: Any) -> bool:
        """
        Delete an object by its primary key.

        Args:
            pk: Primary key value

        Returns:
            True if deleted, False if not found
        """
        try:
            obj = self.model.objects.get(pk=pk)
        except self.model.DoesNotExist:
            return False
        else:
            obj.delete()
            return True

    def exists(self, **kwargs) -> bool:
        """
        Check if an object exists with the given criteria.

        Args:
            **kwargs: Filter criteria

        Returns:
            True if object exists, False otherwise
        """
        return self.model.objects.filter(**kwargs).exists()

    def count(self, **kwargs) -> int:
        """
        Count objects matching the given criteria.

        Args:
            **kwargs: Filter criteria

        Returns:
            Number of matching objects
        """
        return self.model.objects.filter(**kwargs).count()

    def bulk_create(self, objects: list[ModelType], **kwargs) -> list[ModelType]:
        """
        Create multiple objects in a single database query.

        Args:
            objects: List of model instances to create
            **kwargs: Additional arguments for bulk_create

        Returns:
            List of created model instances
        """
        return self.model.objects.bulk_create(objects, **kwargs)

    def bulk_update(self, objects: list[ModelType], fields: list[str], **kwargs) -> int:
        """
        Update multiple objects in a single database query.

        Args:
            objects: List of model instances to update
            fields: List of field names to update
            **kwargs: Additional arguments for bulk_update

        Returns:
            Number of updated objects
        """
        return self.model.objects.bulk_update(objects, fields, **kwargs)
