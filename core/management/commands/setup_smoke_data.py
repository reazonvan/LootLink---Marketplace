import os
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError, transaction
from django.utils import timezone

from accounts.models import Profile
from listings.models import Category, Game, Listing


class Command(BaseCommand):
    help = (
        "Create/update QA smoke users and baseline marketplace data "
        "for automated browser checks."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--seller-username",
            default=os.getenv("SMOKE_SELLER_USERNAME", "qa_smoke_seller"),
            help="Username for seller smoke account",
        )
        parser.add_argument(
            "--seller-email",
            default=os.getenv("SMOKE_SELLER_EMAIL", "qa_smoke_seller@lootlink.local"),
            help="Email for seller smoke account",
        )
        parser.add_argument(
            "--seller-password",
            default=os.getenv("SMOKE_SELLER_PASSWORD", ""),
            help="Password for seller smoke account (required when creating new user)",
        )
        parser.add_argument(
            "--buyer-username",
            default=os.getenv("SMOKE_BUYER_USERNAME", "qa_smoke_buyer"),
            help="Username for buyer smoke account",
        )
        parser.add_argument(
            "--buyer-email",
            default=os.getenv("SMOKE_BUYER_EMAIL", "qa_smoke_buyer@lootlink.local"),
            help="Email for buyer smoke account",
        )
        parser.add_argument(
            "--buyer-password",
            default=os.getenv("SMOKE_BUYER_PASSWORD", ""),
            help="Password for buyer smoke account (required when creating new user)",
        )
        parser.add_argument(
            "--game-name",
            default="Smoke Test Game",
            help="Game name for smoke listing data",
        )
        parser.add_argument(
            "--category-name",
            default="Smoke Category",
            help="Category name for smoke listing data",
        )
        parser.add_argument(
            "--listing-title",
            default="[SMOKE] Baseline listing for automation",
            help="Title for baseline smoke listing",
        )

    def _upsert_user(self, username: str, email: str, password: str, label: str):
        user_model = get_user_model()
        username = (username or "").strip()
        email = (email or "").strip().lower()

        if not username:
            raise CommandError(f"{label}: username must not be empty")
        if not email:
            raise CommandError(f"{label}: email must not be empty")

        try:
            with transaction.atomic():
                user, created = user_model.objects.get_or_create(
                    username=username,
                    defaults={
                        "email": email,
                        "is_active": True,
                    },
                )
        except IntegrityError as exc:
            raise CommandError(f"{label}: failed to create/update user {username}: {exc}") from exc

        changed_fields: list[str] = []
        if user.email.lower() != email:
            user.email = email
            changed_fields.append("email")
        if not user.is_active:
            user.is_active = True
            changed_fields.append("is_active")

        if created and not password:
            raise CommandError(
                f"{label}: user '{username}' does not exist yet. "
                f"Provide --{label}-password or SMOKE_{label.upper()}_PASSWORD."
            )
        if password:
            user.set_password(password)
            # Password hash is not included in update_fields on purpose.
            changed_fields.append("password")

        if changed_fields:
            user.save()

        profile, _ = Profile.objects.get_or_create(user=user)
        profile_changed = False
        if not profile.is_verified:
            profile.is_verified = True
            profile.verification_date = timezone.now()
            profile_changed = True
        if profile_changed:
            profile.save(update_fields=["is_verified", "verification_date", "updated_at"])

        return user, created

    def handle(self, *args, **options):
        seller_username = options["seller_username"]
        seller_email = options["seller_email"]
        seller_password = options["seller_password"]
        buyer_username = options["buyer_username"]
        buyer_email = options["buyer_email"]
        buyer_password = options["buyer_password"]

        game_name = options["game_name"]
        category_name = options["category_name"]
        listing_title = options["listing_title"]

        seller, seller_created = self._upsert_user(
            seller_username, seller_email, seller_password, label="seller"
        )
        buyer, buyer_created = self._upsert_user(
            buyer_username, buyer_email, buyer_password, label="buyer"
        )

        if seller.pk == buyer.pk:
            raise CommandError("seller and buyer must be different accounts")

        game, game_created = Game.objects.get_or_create(
            name=game_name,
            defaults={
                "description": "Automatically created game for smoke/e2e checks",
                "is_active": True,
                "order": 9999,
            },
        )
        if not game.is_active:
            game.is_active = True
            game.save(update_fields=["is_active"])

        category, category_created = Category.objects.get_or_create(
            game=game,
            name=category_name,
            defaults={
                "description": "Automatically created category for smoke/e2e checks",
                "is_active": True,
                "order": 9999,
                "icon": "bi-check2-circle",
            },
        )
        if not category.is_active:
            category.is_active = True
            category.save(update_fields=["is_active"])

        listing, listing_created = Listing.objects.get_or_create(
            seller=seller,
            title=listing_title,
            defaults={
                "game": game,
                "category": category,
                "description": "Baseline listing used by automated smoke checks in CI/CD.",
                "price": Decimal("10.00"),
                "status": "active",
            },
        )

        listing_changed = False
        if listing.game_id != game.id:
            listing.game = game
            listing_changed = True
        if listing.category_id != category.id:
            listing.category = category
            listing_changed = True
        if listing.status != "active":
            listing.status = "active"
            listing_changed = True
        if listing.price <= 0:
            listing.price = Decimal("10.00")
            listing_changed = True
        if len((listing.description or "").strip()) < 20:
            listing.description = "Baseline listing used by automated smoke checks in CI/CD."
            listing_changed = True
        if listing_changed:
            listing.save()

        self.stdout.write(self.style.SUCCESS("Smoke data setup completed"))
        self.stdout.write(f"- Seller: {seller.username} (created={seller_created})")
        self.stdout.write(f"- Buyer: {buyer.username} (created={buyer_created})")
        self.stdout.write(f"- Game: {game.name} (created={game_created})")
        self.stdout.write(f"- Category: {category.name} (created={category_created})")
        self.stdout.write(f"- Baseline listing ID: {listing.id} (created={listing_created})")
