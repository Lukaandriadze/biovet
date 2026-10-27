
import os
import sys
import json
from pathlib import Path
from decimal import Decimal, InvalidOperation

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django
django.setup()

from django.db import transaction
from products.models import Product
from categories.models import Category


def import_products():
    json_path = Path(__file__).resolve().parent / "fixed_products.json"

    if not json_path.exists():
        raise FileNotFoundError(f"JSON ვერ მოიძებნა: {json_path}")

    with json_path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if isinstance(data, dict):
        data = data.get("products", [])

    if not isinstance(data, list):
        raise ValueError("JSON უნდა შეიცავდეს პროდუქტების სიას.")

    created = 0
    updated = 0
    skipped = 0

    fields = {field.name for field in Product._meta.get_fields()}
    price_field = Product._meta.get_field("price")
    integer_price = price_field.get_internal_type() in (
        "IntegerField",
        "PositiveIntegerField",
        "BigIntegerField",
        "PositiveBigIntegerField",
    )

    with transaction.atomic():
        for index, item in enumerate(data, start=1):
            try:
                if not isinstance(item, dict):
                    skipped += 1
                    continue

                name = str(item.get("name") or "").strip()
                if not name:
                    skipped += 1
                    print(f"{index}: სახელი არ აქვს — გამოტოვებულია")
                    continue

                categories = item.get("category", [])
                if not isinstance(categories, list):
                    categories = [categories] if categories else []

                category_name = next(
                    (
                        str(value).strip()
                        for value in categories
                        if value is not None and str(value).strip()
                    ),
                    "სხვა",
                )

                category, _ = Category.objects.get_or_create(
                    name=category_name
                )

                images = item.get("images", [])
                if not isinstance(images, list):
                    images = [images] if images else []

                image = next(
                    (
                        str(value).strip()
                        for value in images
                        if value and str(value).strip()
                    ),
                    "",
                )

                raw_price = item.get("price")
                price = Decimal(str(raw_price or 0).strip())

                if not price.is_finite() or price < 0:
                    raise ValueError("არასწორი ფასი")

                if integer_price:
                    if price != price.to_integral_value():
                        raise ValueError(
                            f"ფასი მთელი რიცხვი უნდა იყოს: {price}"
                        )
                    price = int(price)

                defaults = {
                    "name": name,
                    "price": price,
                }

                if "description" in fields:
                    defaults["description"] = item.get("description") or ""

                if "badge" in fields:
                    defaults["badge"] = item.get("badge") or ""

                if "category" in fields:
                    defaults["category"] = category

                if "img" in fields:
                    defaults["img"] = image
                elif "image" in fields:
                    defaults["image"] = image

                product_id = item.get("id")

                if product_id is not None:
                    product, was_created = Product.objects.update_or_create(
                        id=int(product_id),
                        defaults=defaults,
                    )
                else:
                    product, was_created = Product.objects.update_or_create(
                        name=name,
                        defaults=defaults,
                    )

                if was_created:
                    created += 1
                else:
                    updated += 1

                print(
                    f"{index}/{len(data)} "
                    f"{'დაემატა' if was_created else 'განახლდა'}: {name}"
                )

            except (
                ValueError,
                TypeError,
                InvalidOperation,
                OverflowError,
            ) as error:
                skipped += 1
                print(
                    f"{index}/{len(data)} გამოტოვებულია: {error}"
                )

    print("\n========== იმპორტის შედეგი ==========")
    print(f"JSON-ში სულ: {len(data)}")
    print(f"ახალი პროდუქტი: {created}")
    print(f"განახლებული: {updated}")
    print(f"გამოტოვებული: {skipped}")
    print(f"ბაზაში არსებული სულ: {Product.objects.count()}")
    print("=====================================")


if __name__ == "__main__":
    import_products()
