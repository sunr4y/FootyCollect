"""
Repository for item-related database operations.

This repository handles all database operations related to items,
including jerseys, shorts, outerwear, and other item types.
"""

from django.contrib.auth import get_user_model
from django.db.models import Q, QuerySet

from footycollect.collection.models import BaseItem

from .base_repository import BaseRepository

User = get_user_model()


class ItemRepository(BaseRepository):
    """
    Repository for item-related database operations.

    This repository provides specialized methods for working with items
    and their related data.
    """

    def __init__(self):
        super().__init__(BaseItem)

    def get_user_items(self, user: User, item_type: str | None = None) -> QuerySet[BaseItem]:
        """
        Get all items belonging to a specific user.

        Args:
            user: User instance
            item_type: Optional item type filter (jersey, shorts, etc.)

        Returns:
            QuerySet of user's items
        """
        queryset = self.model.objects.filter(user=user)

        if item_type:
            queryset = queryset.filter(item_type=item_type)

        return queryset.select_related("user", "club", "season", "brand").prefetch_related("photos")

    def get_public_items(self, item_type: str | None = None) -> QuerySet[BaseItem]:
        """
        Get all public (non-draft, non-private) items.

        Args:
            item_type: Optional item type filter

        Returns:
            QuerySet of public items
        """
        queryset = self.model.objects.filter(is_draft=False, is_private=False)

        if item_type and item_type != "jersey":
            # For now, only support jerseys in this repository
            return self.model.objects.none()

        return queryset.select_related("user", "club", "season", "brand").prefetch_related("photos")

    def search_items(self, query: str, user: User | None = None) -> QuerySet[BaseItem]:
        """
        Search items by name, description, or related fields.

        Args:
            query: Search query string
            user: Optional user to limit search to their items

        Returns:
            QuerySet of matching items
        """
        search_filter = Q(description__icontains=query)

        if user:
            queryset = self.model.objects.filter(user=user)
        else:
            queryset = self.model.objects.filter(is_draft=False, is_private=False)

        return (
            queryset.filter(search_filter).select_related("user", "club", "season", "brand").prefetch_related("photos")
        )

    def get_items_by_club(self, club_id: int, user: User | None = None) -> QuerySet[BaseItem]:
        """
        Get items by club ID.

        Args:
            club_id: Club primary key
            user: Optional user to limit to their items

        Returns:
            QuerySet of items for the specified club
        """
        queryset = self.model.objects.filter(club_id=club_id)
        queryset = queryset.filter(user=user) if user else queryset.filter(is_draft=False, is_private=False)

        return queryset.select_related("user", "club", "season", "brand").prefetch_related("photos")

    def get_items_by_season(self, season_id: int, user: User | None = None) -> QuerySet[BaseItem]:
        """
        Get items by season ID.

        Args:
            season_id: Season primary key
            user: Optional user to limit to their items

        Returns:
            QuerySet of items for the specified season
        """
        queryset = self.model.objects.filter(season_id=season_id)
        queryset = queryset.filter(user=user) if user else queryset.filter(is_draft=False, is_private=False)

        return queryset.select_related("user", "club", "season", "brand").prefetch_related("photos")

    def get_items_by_brand(self, brand_id: int, user: User | None = None) -> QuerySet[BaseItem]:
        """
        Get items by brand ID.

        Args:
            brand_id: Brand primary key
            user: Optional user to limit to their items

        Returns:
            QuerySet of items for the specified brand
        """
        queryset = self.model.objects.filter(brand_id=brand_id)
        queryset = queryset.filter(user=user) if user else queryset.filter(is_draft=False, is_private=False)

        return queryset.select_related("user", "club", "season", "brand").prefetch_related("photos")

    def get_recent_items(self, limit: int = 10, user: User | None = None) -> QuerySet[BaseItem]:
        """
        Get the most recently created items.

        Args:
            limit: Maximum number of items to return
            user: Optional user to limit to their items

        Returns:
            QuerySet of recent items
        """
        queryset = self.model.objects.all()
        queryset = queryset.filter(user=user) if user else queryset.filter(is_draft=False, is_private=False)

        return (
            queryset.select_related("user", "club", "season", "brand")
            .prefetch_related("photos")
            .order_by("-created_at")[:limit]
        )

    def get_user_item_count(self, user: User) -> int:
        """
        Get the total number of items for a user.

        Args:
            user: User instance

        Returns:
            Total number of items
        """
        return self.model.objects.filter(user=user).count()

    def get_user_item_count_by_type(self, user: User) -> dict:
        """
        Get the count of items by type for a user.

        Args:
            user: User instance

        Returns:
            Dictionary with item type counts
        """
        counts = {}

        # Count each item type using STI structure (all items in BaseItem table)
        counts["jersey"] = BaseItem.objects.filter(user=user, item_type="jersey").count()
        counts["shorts"] = BaseItem.objects.filter(user=user, item_type="shorts").count()
        counts["outerwear"] = BaseItem.objects.filter(user=user, item_type="outerwear").count()
        counts["tracksuit"] = BaseItem.objects.filter(user=user, item_type="tracksuit").count()
        counts["pants"] = BaseItem.objects.filter(user=user, item_type="pants").count()
        counts["other"] = BaseItem.objects.filter(user=user, item_type="other").count()

        return counts
