
import json
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from products.models import Product
from categories.models import Category


class Command(BaseCommand):
    help = "Load products from fixed_products.json"

    def handle(self, *args, **options):
        # პროექტის მთავარ საქაღალდეში არსებული fixed_products.json
        json_path = Path(__file__).resolve().parents[3] / "fixed_products.json"

        if not json_path.exists():
            raise CommandError(f"JSON file not found: {json_path}")

        try:
            with json_path.open("r", encoding="utf-8") as file:
                data = json.load(file)
        except (json.JSONDecodeError, OSError) as error:
            raise CommandError(f"Could not read JSON: {error}")

        if isinstance(data, dict):
            data = data.get("products", [data])

        if not isinstance(data, list):
            raise CommandError("JSON must contain a list of products.")

        created_count = 0
        updated_count = 0
        skipped_count = 0

        with transaction.atomic():
            for item in data:
                if not isinstance(item, dict) or not item.get("name"):
                    skipped_count += 1
                    continue

                try:
                    name = str(item["name"]).strip()
                    price = Decimal(str(item.get("price") or 0)).quantize(Decimal("0.01"))

                    if price < 0:
                        skipped_count += 1
                        continue

                    category_names = item.get("category", [])
                    if not isinstance(category_names, list):
                        category_names = [category_names] if category_names else []

                    category_name = (
                        str(category_names[0]).strip()
                        if category_names and str(category_names[0]).strip()
                        else "სხვა"
                    )
                    category_obj, _ = Category.objects.get_or_create(
                        name=category_name
                    )

                    images = item.get("images", [])
                    if not isinstance(images, list):
                        images = [images] if images else []

                    image_url = ""
                    if images and isinstance(images[0], str):
                        image_url = images[0]

                    defaults = {
                        "name": name,
                        "price": price,
                        "description": item.get("description", ""),
                        "img": image_url,
                        "category": category_obj,
                        "badge": item.get("badge", ""),
                    }

                    product_id = item.get("id")

                    if product_id is not None:
                        product, created = Product.objects.update_or_create(
                            id=int(product_id),
                            defaults=defaults,
                        )
                    else:
                        product, created = Product.objects.update_or_create(
                            name=name,
                            defaults=defaults,
                        )

                    if created:
                        created_count += 1
                    else:
                        updated_count += 1

                except (ValueError, TypeError, OverflowError, InvalidOperation) as error:
                    skipped_count += 1
                    self.stderr.write(
                        f"Skipped product {item.get('id', '?')}: {error}"
                    )

        self.stdout.write(
            self.style.SUCCESS(
                f"Finished! Created: {created_count}, "
                f"updated: {updated_count}, skipped: {skipped_count}"
            )
        )
