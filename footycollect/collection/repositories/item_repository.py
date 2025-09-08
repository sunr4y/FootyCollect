"""
Repository for item-related database operations.

This repository handles all database operations related to items,
including jerseys, shorts, outerwear, and other item types.
"""

from django.contrib.auth import get_user_model
from django.db.models import Q, QuerySet

from footycollect.collection.models import BaseItem, Jersey, OtherItem, Outerwear, Pants, Shorts, Tracksuit

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
            # Filter by specific item type
            if item_type == "jersey":
                queryset = queryset.filter(jersey__isnull=False)
            elif item_type == "shorts":
                queryset = queryset.filter(shorts__isnull=False)
            elif item_type == "outerwear":
                queryset = queryset.filter(outerwear__isnull=False)
            elif item_type == "tracksuit":
                queryset = queryset.filter(tracksuit__isnull=False)
            elif item_type == "pants":
                queryset = queryset.filter(pants__isnull=False)
            elif item_type == "other":
                queryset = queryset.filter(otheritem__isnull=False)

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

        if item_type:
            if item_type == "jersey":
                queryset = queryset.filter(jersey__isnull=False)
            elif item_type == "shorts":
                queryset = queryset.filter(shorts__isnull=False)
            elif item_type == "outerwear":
                queryset = queryset.filter(outerwear__isnull=False)
            elif item_type == "tracksuit":
                queryset = queryset.filter(tracksuit__isnull=False)
            elif item_type == "pants":
                queryset = queryset.filter(pants__isnull=False)
            elif item_type == "other":
                queryset = queryset.filter(otheritem__isnull=False)

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
        search_filter = Q(name__icontains=query) | Q(description__icontains=query)

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

        # Count each item type
        counts["jersey"] = Jersey.objects.filter(user=user).count()
        counts["shorts"] = Shorts.objects.filter(user=user).count()
        counts["outerwear"] = Outerwear.objects.filter(user=user).count()
        counts["tracksuit"] = Tracksuit.objects.filter(user=user).count()
        counts["pants"] = Pants.objects.filter(user=user).count()
        counts["other"] = OtherItem.objects.filter(user=user).count()

        return counts
