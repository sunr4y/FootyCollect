"""
Django management command to populate database with user collections from FootballKitArchive API.

This command:
1. Calls POST /api/user-collection/{userid}/scrape to start scraping
2. Waits for scraping to complete or uses cached data
3. Maps API data to Django models (User, BaseItem, Jersey, Club, Brand, Season, etc.)
4. Creates Photo objects from entry images
"""

import logging
import time

import requests
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.text import slugify

from footycollect.api.client import FKAPIClient
from footycollect.collection.models import BaseItem, Color, Jersey, Photo, Size
from footycollect.core.models import Brand, Club, Competition, Kit, Season, TypeK

User = get_user_model()
logger = logging.getLogger(__name__)

logging.getLogger("PIL.TiffImagePlugin").setLevel(logging.WARNING)


class Command(BaseCommand):
    help = "Populate database with user collections from FootballKitArchive API"

    def _raise_scraping_error(self, message: str) -> None:
        """Helper to raise CommandError for scraping errors."""
        raise CommandError(message)

    def add_arguments(self, parser):
        parser.add_argument(
            "userid",
            type=int,
            nargs="?",
            help="User ID from FootballKitArchive",
        )
        parser.add_argument(
            "--target-username",
            type=str,
            help="Username in our system to assign items to (default: creates new user)",
        )
        parser.add_argument(
            "--wait-timeout",
            type=int,
            default=120,
            help="Maximum time to wait for scraping (seconds, default: 120)",
        )
        parser.add_argument(
            "--page-size",
            type=int,
            default=20,
            help="Page size for paginated requests (default: 20)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Dry run mode - don't create any objects",
        )
        parser.add_argument(
            "--json-file",
            type=str,
            help="Path to JSON file with collection data (for testing)",
        )

    def handle(self, *args, **options):  # noqa: PLR0915
        userid = options.get("userid")
        target_username = options.get("target_username")
        wait_timeout = options["wait_timeout"]
        page_size = options["page_size"]
        dry_run = options["dry_run"]
        json_file = options.get("json_file")

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN MODE - No objects will be created"))

        if json_file:
            self.stdout.write(f"Reading collection data from file: {json_file}")
            import json
            from pathlib import Path

            with Path(json_file).open(encoding="utf-8") as f:
                response_data = json.load(f)
            collection_data = response_data.get("data", response_data)
            user_info = response_data.get("user")
            if not userid:
                entries = collection_data.get("entries", [])
                if entries:
                    userid = entries[0].get("userid")
        else:
            if not userid:
                msg = "userid is required when not using --json-file"
                raise CommandError(msg)
            self.stdout.write(f"Starting collection population for user ID: {userid}")
            collection_data, user_info = self._fetch_user_collection(userid, wait_timeout, page_size)
            if not collection_data:
                msg = "Failed to fetch user collection"
                raise CommandError(msg)

        entries = collection_data.get("entries", [])
        self.stdout.write(f"Found {len(entries)} entries to process")

        if not userid:
            msg = "Could not determine userid from data"
            raise CommandError(msg)

        target_user = self._get_or_create_target_user(
            target_username,
            userid,
            user_info,
            dry_run=dry_run,
        )

        created_count = 0
        skipped_count = 0
        error_count = 0

        for idx, entry in enumerate(entries, 1):
            entry_id = entry.get("id", "unknown")
            kit_name = entry.get("kit", {}).get("team_name", "Unknown")
            try:
                self.stdout.write(f"\n[{idx}/{len(entries)}] Processing entry {entry_id} - {kit_name}...")
                if self._process_entry(entry, target_user, dry_run=dry_run):
                    created_count += 1
                    self.stdout.write(self.style.SUCCESS(f"  ✓ Entry {entry_id} processed successfully"))
                else:
                    skipped_count += 1
                    self.stdout.write(self.style.WARNING(f"  ⚠ Entry {entry_id} skipped"))
            except Exception as e:
                error_count += 1
                logger.exception("Error processing entry %s", entry_id)
                self.stdout.write(self.style.ERROR(f"  ✗ Error processing entry {entry_id}: {e!s}"))

        self.stdout.write(
            self.style.SUCCESS(f"\nCompleted: {created_count} created, {skipped_count} skipped, {error_count} errors")
        )

    def _fetch_user_collection(  # noqa: PLR0915
        self,
        userid: int,
        wait_timeout: int,
        page_size: int,
    ) -> tuple[dict | None, dict | None]:
        """Fetch user collection from API with pagination. Returns (collection_data, user_info)."""
        client = FKAPIClient()

        self.stdout.write(f"Starting scrape for user {userid}...")
        try:
            try:
                scrape_response = client.scrape_user_collection(userid)
            except Exception as e:
                logger.exception("Error calling scrape_user_collection for userid %s", userid)
                msg = f"Failed to start scraping: {e!s}"
                raise CommandError(msg) from e

            if not scrape_response:
                logger.error("scrape_user_collection returned None for userid %s", userid)
                msg = f"Failed to start scraping: No response from API (userid: {userid})"
                self._raise_scraping_error(msg)

            self.stdout.write(f"Scrape response: {scrape_response}")

            if scrape_response.get("status") == "error" or "error" in scrape_response:
                error_msg = scrape_response.get("error", "Unknown error")
                msg = f"Failed to start scraping: {error_msg}"
                self._raise_scraping_error(msg)

            task_id = scrape_response.get("task_id")
            if task_id:
                self.stdout.write(f"Scraping started (task_id: {task_id}), waiting...")
            else:
                self.stdout.write("Scrape request accepted, waiting for completion...")

            start_time = time.time()
            while time.time() - start_time < wait_timeout:
                get_response = client.get_user_collection(userid, page=1, page_size=page_size, use_cache=False)

                if get_response:
                    if get_response.get("status") == "processing" or get_response.get("status") == "pending":
                        time.sleep(1)
                        continue

                    data = get_response.get("data", {})
                    if data.get("entries"):
                        self.stdout.write("Collection ready")
                        break
                else:
                    time.sleep(1)
                    continue

            all_entries = []
            user_info = None
            page = 1

            if time.time() - start_time >= wait_timeout:
                msg = f"Timeout waiting for scraping to complete after {wait_timeout}s"
                self._raise_scraping_error(msg)

            while True:
                self.stdout.write(f"Fetching page {page}...")
                try:
                    page_response = client.get_user_collection(userid, page=page, page_size=page_size, use_cache=False)
                except Exception:
                    import traceback

                    tb = traceback.format_exc()
                    self.stdout.write(self.style.ERROR(f"Error fetching page {page}:\n{tb}"))
                    logger.exception("Error fetching page %s", page)
                    break
                else:
                    if not page_response:
                        self.stdout.write(f"Page {page} returned no data, stopping pagination")
                        break

                    data = page_response.get("data", {})
                    if page == 1:
                        user_info = page_response.get("user")

                    page_entries = data.get("entries", [])
                    if not page_entries:
                        self.stdout.write(f"No more entries on page {page}, stopping pagination")
                        break

                    all_entries.extend(page_entries)
                    self.stdout.write(
                        f"  Fetched page {page} ({len(page_entries)} entries, total: {len(all_entries)})"
                    )

                    pagination = page_response.get("pagination", {})
                    total_pages = pagination.get("total_pages", 1)
                    if page >= total_pages:
                        break

                    page += 1

            if not all_entries:
                msg = "No entries found in collection"
                self._raise_scraping_error(msg)
            return {"entries": all_entries}, user_info  # noqa: TRY300
        except Exception:
            import traceback

            tb = traceback.format_exc()
            self.stdout.write(self.style.ERROR(f"Error in _fetch_user_collection:\n{tb}"))
            logger.exception("Error in _fetch_user_collection")
            raise

    def _get_or_create_target_user(
        self,
        target_username: str | None,
        fka_userid: int,
        user_info: dict | None,
        *,
        dry_run: bool,
    ) -> User:
        """Get or create target user in our system."""
        if target_username:
            user, created = User.objects.get_or_create(username=target_username)
            if created and not dry_run:
                self.stdout.write(f"Created user: {target_username}")
            return user

        username = None
        avatar_url = None

        if user_info:
            username = user_info.get("username")
            avatar_url = user_info.get("avatar") or user_info.get("avatar_url") or user_info.get("photo")

        if not username:
            username = f"fka_user_{fka_userid}"

        user, created = User.objects.get_or_create(username=username)

        if created and not dry_run:
            user.email = f"{username}@footballkitarchive.com"
            if avatar_url:
                self._download_user_avatar(user, avatar_url, dry_run=dry_run)
            user.save()
            self.stdout.write(f"Created user: {username}")
        elif not dry_run and avatar_url and not user.avatar:
            self._download_user_avatar(user, avatar_url, dry_run=dry_run)
            user.save()

        return user

    def _download_user_avatar(self, user: User, avatar_url: str, *, dry_run: bool) -> None:
        """Download and set user avatar."""
        if not avatar_url or dry_run:
            return

        try:
            if not avatar_url.startswith("http"):
                if avatar_url.startswith("/"):
                    avatar_url = f"https://www.footballkitarchive.com{avatar_url}"
                else:
                    avatar_url = f"https://www.footballkitarchive.com/{avatar_url}"

            response = requests.get(avatar_url, timeout=30, stream=True)
            response.raise_for_status()

            from django.core.files.base import ContentFile

            file_extension = avatar_url.split(".")[-1].split("?")[0] if "." in avatar_url else "jpg"
            filename = f"avatar_{user.username}.{file_extension}"

            user.avatar.save(
                filename,
                ContentFile(response.content),
                save=False,
            )
            self.stdout.write(f"  Downloaded avatar for user {user.username}")

        except Exception as e:
            self.stdout.write(self.style.WARNING(f"  Warning: Could not download avatar: {e!s}"))
            logger.exception("Error downloading avatar %s", avatar_url)

    def _process_entry(self, entry: dict, user: User, *, dry_run: bool) -> bool:
        """Process a single entry and create corresponding objects."""
        kit_data = entry.get("kit", {})
        if not kit_data:
            logger.warning("Entry %s has no kit data", entry.get("id"))
            return False

        with transaction.atomic():
            brand = self._get_or_create_brand(kit_data.get("brand_name"), kit_data, dry_run=dry_run)
            club = self._get_or_create_club(kit_data, dry_run=dry_run)
            season = self._get_or_create_season(kit_data.get("season"), dry_run=dry_run)
            type_k = self._get_or_create_type_k(kit_data.get("type"), dry_run=dry_run)
            competition = self._get_or_create_competition(kit_data.get("league"), dry_run=dry_run)
            kit = self._get_or_create_kit(
                kit_data,
                club,
                season,
                brand,
                type_k,
                competition,
                dry_run=dry_run,
            )
            size = self._get_or_create_size(entry.get("size"), dry_run=dry_run)

            base_item = self._create_base_item(
                entry,
                kit_data,
                user,
                brand,
                club,
                season,
                competition,
                kit,
                dry_run=dry_run,
            )
            if not base_item:
                return False

            if hasattr(base_item, "jersey") and base_item.jersey:
                logger.info("Item already exists, skipping creation of Jersey and photos")
                return True

            jersey = self._create_jersey(entry, base_item, kit, size, dry_run=dry_run)
            if not jersey:
                return False

            self._create_photos(entry.get("images", []), base_item, user, dry_run=dry_run)

            if dry_run:
                transaction.set_rollback(True)

            return True

    def _get_or_create_brand(
        self,
        brand_name: str | None,
        kit_data: dict | None = None,
        *,
        dry_run: bool = False,
    ) -> Brand | None:
        """Get or create Brand."""
        if not brand_name:
            return None

        logo_url = None
        logo_dark_url = None
        brand_id_fka = None

        if kit_data:
            brand_data = kit_data.get("brand")
            if isinstance(brand_data, dict):
                brand_id_fka = brand_data.get("id")
                logo_url = brand_data.get("logo")
                logo_dark_url = brand_data.get("logo_dark")

        if logo_url and "not_found.png" in logo_url:
            logo_url = None
        if logo_dark_url and "not_found.png" in logo_dark_url:
            logo_dark_url = None

        brand, created = Brand.objects.get_or_create(
            name=brand_name,
            defaults={
                "slug": slugify(brand_name),
                "id_fka": brand_id_fka,
                "logo": logo_url or "",
                "logo_dark": logo_dark_url or "",
            },
        )
        if created and not dry_run:
            logger.info("Created brand: %s", brand_name)
        else:
            updated = False
            if not dry_run and brand_id_fka and not brand.id_fka:
                brand.id_fka = brand_id_fka
                updated = True
            if not dry_run and logo_url and not brand.logo:
                brand.logo = logo_url
                updated = True
            if not dry_run and logo_dark_url and not brand.logo_dark:
                brand.logo_dark = logo_dark_url
                updated = True
            if updated:
                brand.save()
        return brand

    def _get_or_create_club(self, kit_data: dict, *, dry_run: bool) -> Club | None:
        """Get or create Club."""
        team_name = kit_data.get("team_name")
        if not team_name:
            return None

        logo_url = None
        logo_dark_url = None
        club_id_fka = None
        country_code = None

        club_data = kit_data.get("club")
        if isinstance(club_data, dict):
            club_id_fka = club_data.get("id")
            logo_url = club_data.get("logo")
            logo_dark_url = club_data.get("logo_dark")
            country_code = club_data.get("country")

        if not country_code:
            league = kit_data.get("league", {})
            country_name = league.get("country") if isinstance(league, dict) else None
            country_code = self._convert_country_name_to_code(country_name) if country_name else None

        if logo_url and "not_found.png" in logo_url:
            logo_url = None
        if logo_dark_url and "not_found.png" in logo_dark_url:
            logo_dark_url = None

        club, created = Club.objects.get_or_create(
            name=team_name,
            defaults={
                "slug": slugify(team_name),
                "id_fka": club_id_fka,
                "country": country_code,
                "logo": logo_url or "",
                "logo_dark": logo_dark_url or "",
            },
        )
        if created and not dry_run:
            logger.info("Created club: %s", team_name)
        else:
            updated = False
            if not dry_run and club_id_fka and not club.id_fka:
                club.id_fka = club_id_fka
                updated = True
            if not dry_run and country_code and club.country != country_code:
                club.country = country_code
                updated = True
            if not dry_run and logo_url and not club.logo:
                club.logo = logo_url
                updated = True
            if not dry_run and logo_dark_url and not club.logo_dark:
                club.logo_dark = logo_dark_url
                updated = True
            if updated:
                club.save()
        return club

    def _get_or_create_season(self, season_str: str | None, *, dry_run: bool) -> Season | None:
        """Get or create Season."""
        if not season_str:
            return None

        parts = season_str.split("-") if "-" in season_str else [season_str]
        first_year = parts[0]
        second_year = parts[1] if len(parts) > 1 else ""

        season, created = Season.objects.get_or_create(
            year=season_str,
            defaults={
                "first_year": first_year,
                "second_year": second_year,
            },
        )
        if created and not dry_run:
            logger.info("Created season: %s", season_str)
        return season

    def _get_or_create_type_k(self, type_name: str | None, *, dry_run: bool) -> TypeK | None:
        """Get or create TypeK."""
        if not type_name:
            return None

        type_k, created = TypeK.objects.get_or_create(
            name=type_name,
            defaults={"category": "match"},
        )
        if created and not dry_run:
            logger.info("Created TypeK: %s", type_name)
        return type_k

    def _get_or_create_competition(
        self,
        league_data: dict | None,
        *,
        dry_run: bool,
    ) -> Competition | None:
        """Get or create Competition."""
        if not league_data or not isinstance(league_data, dict):
            return None

        league_name = league_data.get("name")
        if not league_name:
            return None

        competition, created = Competition.objects.get_or_create(
            name=league_name,
            defaults={
                "slug": slugify(league_name),
                "id_fka": league_data.get("id"),
            },
        )
        if created and not dry_run:
            logger.info("Created competition: %s", league_name)
        return competition

    def _get_or_create_kit(
        self,
        kit_data: dict,
        club: Club | None,
        season: Season | None,
        brand: Brand | None,
        type_k: TypeK | None,
        competition: Competition | None,
        *,
        dry_run: bool,
    ) -> Kit | None:
        """Get or create Kit."""
        kit_id_fka = kit_data.get("id")
        kit_name = f"{kit_data.get('team_name', '')} {kit_data.get('type', '')} {kit_data.get('season', '')}".strip()

        if kit_id_fka:
            existing_kit = Kit.objects.filter(id_fka=kit_id_fka).first()
            if existing_kit:
                return existing_kit

        kit_slug = slugify(kit_name)

        lookup_params = {"slug": kit_slug}
        defaults = {
            "name": kit_name,
            "id_fka": kit_id_fka,
            "team": club,
            "season": season,
            "brand": brand,
            "type": type_k,
            "main_img_url": kit_data.get("image_url", ""),
        }

        kit, created = Kit.objects.get_or_create(**lookup_params, defaults=defaults)
        if created and not dry_run:
            if competition:
                kit.competition.add(competition)
            logger.info("Created kit: %s", kit_name)
        elif not dry_run and competition and competition not in kit.competition.all():
            kit.competition.add(competition)

        return kit

    def _get_or_create_size(self, size_str: str | None, *, dry_run: bool) -> Size | None:
        """Get or create Size. If no size provided, use random size from pool."""
        if not size_str:
            sizes = list(Size.objects.all())
            if sizes:
                import random

                random_size = random.choice(sizes)  # noqa: S311
                if not dry_run:
                    logger.info("No size provided, using random size: %s", random_size.name)
                return random_size
            return None

        size, created = Size.objects.get_or_create(
            name=size_str.upper(),
            defaults={"category": "tops"},
        )
        if created and not dry_run:
            logger.info("Created size: %s", size_str)
        return size

    def _create_base_item(
        self,
        entry: dict,
        kit_data: dict,
        user: User,
        brand: Brand | None,
        club: Club | None,
        season: Season | None,
        competition: Competition | None,
        kit: Kit | None,
        *,
        dry_run: bool,
    ) -> BaseItem | None:
        """Create BaseItem. Checks for duplicates based on user and kit."""
        if not brand:
            logger.warning("Cannot create BaseItem without brand")
            return None

        if kit and not dry_run:
            existing_jersey = (
                Jersey.objects.filter(base_item__user=user, kit=kit).select_related("base_item", "kit").first()
            )

            if existing_jersey:
                entry_id = entry.get("id", "unknown")
                logger.info(
                    "Item already exists for user %s and kit %s (entry %s), skipping", user.username, kit.id, entry_id
                )
                return existing_jersey.base_item

        item_name = f"{kit_data.get('team_name', '')} {kit_data.get('type', '')} {kit_data.get('season', '')}".strip()

        condition_map = {
            "new": 10,
            "very-good": 9,
            "good": 8,
            "fair": 7,
            "poor": 6,
        }
        condition_value = condition_map.get(entry.get("condition", "good"), 8)

        detailed_condition_map = {
            "new": "BNWT",
            "very-good": "VERY_GOOD",
            "good": "GOOD",
            "fair": "FAIR",
            "poor": "POOR",
        }
        detailed_condition = detailed_condition_map.get(entry.get("condition", "good"), "GOOD") or "GOOD"

        tags = entry.get("tags", [])
        kit_type = entry.get("kit_type", "")
        is_replica = kit_type in ["replica", "fan-version"] or "replica" in tags

        design_map = {
            "plain": "PLAIN",
            "stripes": "STRIPES",
            "graphic": "GRAPHIC",
            "single stripe": "SINGLE_STRIPE",
            "hoops": "HOOPS",
        }
        design = design_map.get(kit_data.get("design", ""), "")

        main_color = self._get_or_create_color(kit_data.get("kitcolor1"), dry_run=dry_run)
        secondary_colors = []
        for color_name in [kit_data.get("kitcolor2"), kit_data.get("kitcolor3")]:
            if color_name:
                color = self._get_or_create_color(color_name, dry_run=dry_run)
                if color:
                    secondary_colors.append(color)

        country = None
        if club and club.country:
            country = club.country
        else:
            league = kit_data.get("league", {})
            country_name = league.get("country") if isinstance(league, dict) else None
            if country_name:
                country = self._convert_country_name_to_code(country_name)

        if dry_run:
            return BaseItem(
                item_type="jersey",
                name=item_name,
                user=user,
                brand=brand,
                club=club,
                season=season,
                condition=condition_value,
                detailed_condition=detailed_condition,
                description=entry.get("notes", ""),
                is_replica=is_replica,
                design=design,
                main_color=main_color,
                country=country,
                is_draft=False,
            )

        base_item = BaseItem.objects.create(
            item_type="jersey",
            name=item_name,
            user=user,
            brand=brand,
            club=club,
            season=season,
            condition=condition_value,
            detailed_condition=detailed_condition,
            description=entry.get("notes", ""),
            is_replica=is_replica,
            design=design,
            main_color=main_color,
            country=country,
            is_draft=False,
        )

        if competition:
            base_item.competitions.add(competition)
        if secondary_colors:
            base_item.secondary_colors.set(secondary_colors)

        return base_item

    def _convert_country_name_to_code(self, country_name: str | None) -> str | None:
        """Convert country name to ISO 3166-1 alpha-2 code using django-countries."""
        if not country_name:
            return None

        try:
            from django_countries import countries

            country_name_lower = country_name.lower().strip()

            for code, name in countries:
                if name.lower() == country_name_lower or str(name).lower() == country_name_lower:
                    return code

            country_map = {
                "usa": "US",
                "united states": "US",
                "united kingdom": "GB",
                "uk": "GB",
                "england": "GB",
                "south korea": "KR",
                "czech republic": "CZ",
            }

            country_code = country_map.get(country_name_lower)
            if country_code:
                return country_code
            logger.warning("Could not convert country name '%s' to code, using None", country_name)
            return None  # noqa: TRY300

        except ImportError:
            logger.warning("django-countries not available, cannot convert country name '%s'", country_name)
            return None

    def _get_or_create_color(self, color_name: str | None, *, dry_run: bool) -> Color | None:
        """Get or create Color."""
        if not color_name:
            return None

        color_name_clean = color_name.lower().strip()
        color_name_map = {
            "sky blue": "SKY_BLUE",
            "off-white": "OFF_WHITE",
            "claret": "CLARET",
            "navy": "NAVY",
            "gray": "GRAY",
            "grey": "GRAY",
            "gold": "GOLD",
            "silver": "SILVER",
        }

        mapped_name = color_name_map.get(color_name_clean, color_name.upper().replace(" ", "_"))

        hex_value = Color.COLOR_MAP.get(mapped_name, "#000000")

        color, created = Color.objects.get_or_create(
            name=mapped_name,
            defaults={"hex_value": hex_value},
        )
        if created and not dry_run:
            logger.info("Created color: %s", mapped_name)
        return color

    def _create_jersey(
        self,
        entry: dict,
        base_item: BaseItem,
        kit: Kit | None,
        size: Size | None,
        *,
        dry_run: bool,
    ) -> Jersey | None:
        """Create Jersey."""
        if not size:
            logger.warning("Cannot create Jersey without size")
            return None

        kit_type = entry.get("kit_type", "authentic")
        is_fan_version = kit_type in ["fan-version", "replica"]

        tags = entry.get("tags", [])
        is_signed = "signed" in tags

        is_short_sleeve = True

        player_name = entry.get("player_name", "")
        player_number = entry.get("player_number", "")
        number = None
        if player_number:
            from contextlib import suppress

            with suppress(ValueError, TypeError):
                number = int(player_number)

        has_nameset = bool(player_name or player_number)

        if dry_run:
            return Jersey(
                base_item=base_item,
                kit=kit,
                size=size,
                is_fan_version=is_fan_version,
                is_signed=is_signed,
                has_nameset=has_nameset,
                player_name=player_name,
                number=number,
                is_short_sleeve=is_short_sleeve,
            )

        return Jersey.objects.create(
            base_item=base_item,
            kit=kit,
            size=size,
            is_fan_version=is_fan_version,
            is_signed=is_signed,
            has_nameset=has_nameset,
            player_name=player_name,
            number=number,
            is_short_sleeve=is_short_sleeve,
        )

    def _create_photos(
        self,
        images: list[dict],
        base_item: BaseItem,
        user: User,
        *,
        dry_run: bool,
    ) -> None:
        """Create Photo objects from entry images."""
        if not images:
            return

        for idx, image_data in enumerate(images):
            image_url = image_data.get("url") or image_data.get("preview_url") or image_data.get("thumbnail_url")
            if not image_url:
                continue

            if not image_url.startswith("http"):
                if image_url.startswith("/"):
                    image_url = f"https://www.footballkitarchive.com{image_url}"
                else:
                    image_url = f"https://www.footballkitarchive.com/{image_url}"

            if dry_run:
                self.stdout.write(f"  Would download photo {idx + 1}: {image_url}")
                continue

            try:
                response = requests.get(image_url, timeout=30, stream=True)
                response.raise_for_status()

                from django.core.files.base import ContentFile

                photo = Photo(
                    content_object=base_item,
                    user=user,
                    order=image_data.get("order", idx),
                    caption="",
                )

                file_extension = image_url.split(".")[-1].split("?")[0] if "." in image_url else "jpg"
                filename = f"photo_{base_item.id}_{idx}.{file_extension}"

                photo.image.save(
                    filename,
                    ContentFile(response.content),
                    save=False,
                )
                photo.save()
                self.stdout.write(f"  Created photo {idx + 1} for item {base_item.id}")
                logger.info("Created photo for item %s", base_item.id)

            except Exception as e:
                self.stdout.write(self.style.WARNING(f"  Warning: Could not download image {idx + 1}: {e!s}"))
                logger.exception("Error downloading image %s", image_url)
