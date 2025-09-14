"""
Service for user-related business logic.

This service handles complex business operations related to users,
including profile data, statistics, and user management.
"""

from django.contrib.auth import get_user_model
from django.db.models import QuerySet

from footycollect.collection.services import get_item_service

User = get_user_model()


class UserService:
    """
    Service for user-related business logic.

    This service handles complex operations related to user management,
    including profile data, statistics, and user interactions.
    """

    def __init__(self):
        self.item_service = get_item_service()

    def get_user_profile_data(self, user: User, requesting_user: User = None) -> dict:
        """
        Get comprehensive profile data for a user.

        Args:
            user: User whose profile data to get
            requesting_user: User requesting the data (for privacy checks)

        Returns:
            Dictionary with profile data
        """
        # Check if profile should be visible
        show_details = not user.is_private or user == requesting_user

        if not show_details:
            return {
                "show_details": False,
                "user": user,
            }

        # Get user's items using service
        user_items = self.item_service.get_user_items(user)

        # Calculate stats
        total_items = user_items.count()
        total_teams = user_items.filter(club__isnull=False).values("club").distinct().count()
        total_competitions = user_items.filter(competitions__isnull=False).values("competitions").distinct().count()

        # Get recent items for display
        recent_items = user_items.select_related("club", "brand", "season").order_by("-created_at")[:5]

        return {
            "show_details": True,
            "user": user,
            "total_items": total_items,
            "total_teams": total_teams,
            "total_competitions": total_competitions,
            "recent_items": recent_items,
        }

    def get_user_statistics(self, user: User) -> dict:
        """
        Get detailed statistics for a user.

        Args:
            user: User to get statistics for

        Returns:
            Dictionary with user statistics
        """
        user_items = self.item_service.get_user_items(user)

        return {
            "total_items": user_items.count(),
            "total_teams": user_items.filter(club__isnull=False).values("club").distinct().count(),
            "total_competitions": (
                user_items.filter(competitions__isnull=False).values("competitions").distinct().count()
            ),
            "items_by_type": self._get_items_by_type(user_items),
            "items_by_year": self._get_items_by_year(user_items),
        }

    def _get_items_by_type(self, items: QuerySet) -> dict:
        """
        Get item count by type.

        Args:
            items: QuerySet of items

        Returns:
            Dictionary with item counts by type
        """
        from django.db.models import Count

        return dict(
            items.values("item_type").annotate(count=Count("id")).values_list("item_type", "count"),
        )

    def _get_items_by_year(self, items: QuerySet) -> dict:
        """
        Get item count by year.

        Args:
            items: QuerySet of items

        Returns:
            Dictionary with item counts by year
        """
        from django.db.models import Count
        from django.db.models.functions import ExtractYear

        return dict(
            items.annotate(year=ExtractYear("created_at"))
            .values("year")
            .annotate(count=Count("id"))
            .values_list("year", "count"),
        )

    def can_view_profile(self, profile_user: User, requesting_user: User = None) -> bool:
        """
        Check if a user can view another user's profile.

        Args:
            profile_user: User whose profile is being viewed
            requesting_user: User requesting to view the profile

        Returns:
            True if the profile can be viewed, False otherwise
        """
        if not profile_user.is_private:
            return True

        return profile_user == requesting_user

    def get_public_users(self, limit: int = 20) -> QuerySet[User]:
        """
        Get list of public users.

        Args:
            limit: Maximum number of users to return

        Returns:
            QuerySet of public users
        """
        return User.objects.filter(is_private=False).order_by("-date_joined")[:limit]

    def get_user_activity_summary(self, user: User) -> dict:
        """
        Get activity summary for a user.

        Args:
            user: User to get activity for

        Returns:
            Dictionary with activity summary
        """
        user_items = self.item_service.get_user_items(user)

        return {
            "total_items": user_items.count(),
            "recent_activity": user_items.order_by("-created_at")[:10],
            "most_common_club": self._get_most_common_club(user_items),
            "most_common_competition": self._get_most_common_competition(user_items),
        }

    def _get_most_common_club(self, items: QuerySet) -> str | None:
        """
        Get the most common club for a user's items.

        Args:
            items: QuerySet of items

        Returns:
            Name of the most common club or None
        """
        from django.db.models import Count

        club_counts = (
            items.filter(club__isnull=False).values("club__name").annotate(count=Count("id")).order_by("-count")
        )

        if club_counts:
            return club_counts.first()["club__name"]
        return None

    def _get_most_common_competition(self, items: QuerySet) -> str | None:
        """
        Get the most common competition for a user's items.

        Args:
            items: QuerySet of items

        Returns:
            Name of the most common competition or None
        """
        from django.db.models import Count

        competition_counts = (
            items.filter(competitions__isnull=False)
            .values("competitions__name")
            .annotate(count=Count("id"))
            .order_by("-count")
        )

        if competition_counts:
            return competition_counts.first()["competitions__name"]
        return None
