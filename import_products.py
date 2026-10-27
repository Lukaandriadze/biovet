
import os
import json
import django

from pathlib import Path
from decimal import Decimal, InvalidOperation

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.db import transaction
from products.models import Product
from categories.models import Category


def import_products():
    json_path = Path(__file__).resolve().parent / "fixed_products.json"

    if not json_path.exists():
        raise FileNotFoundError(
            f"JSON ფაილი ვერ მოიძებნა: {json_path}"
        )

    with open(json_path, "r", encoding="utf-8") as file:
        data = json.load(file)

    if isinstance(data, dict):
        data = data.get("products", [data])

    if not isinstance(data, list):
        raise ValueError("JSON უნდა შეიცავდეს პროდუქტების სიას.")

    print(f"\nJSON-ში ნაპოვნია {len(data)} პროდუქტი\n")

    created_count = 0
    updated_count = 0
    skipped_count = 0

    with transaction.atomic():
        for number, item in enumerate(data, start=1):
            try:
                if not isinstance(item, dict):
                    skipped_count += 1
                    print(f"{number}/{len(data)} — გამოტოვებულია: არასწორი ჩანაწერი")
                    continue

                name = str(item.get("name") or "").strip()

                if not name:
                    skipped_count += 1
                    print(f"{number}/{len(data)} — გამოტოვებულია: სახელი არ აქვს")
                    continue

                # კატეგორია
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

                # სურათი
                images = item.get("images", [])

                if not isinstance(images, list):
                    images = [images] if images else []

                image_url = next(
                    (
                        str(value).strip()
                        for value in images
                        if value and str(value).strip()
                    ),
                    "",
                )

                # ფასი
                raw_price = item.get("price")

                try:
                    price = (
                        Decimal(str(raw_price).strip())
                        if raw_price is not None
                        and str(raw_price).strip()
                        else Decimal("0")
                    )
                except (InvalidOperation, ValueError):
                    skipped_count += 1
                    print(
                        f"{number}/{len(data)} — გამოტოვებულია "
                        f"{name}: არასწორი ფასი"
                    )
                    continue

                if not price.is_finite() or price < 0:
                    skipped_count += 1
                    print(
                        f"{number}/{len(data)} — გამოტოვებულია "
                        f"{name}: არასწორი ფასი"
                    )
                    continue

                defaults = {
                    "category": category,
                    "name": name,
                    "price": price,
                    "description": item.get("description") or "",
                    "img": image_url,
                    "badge": item.get("badge") or "",
                }

                product_id = item.get("id")

                if product_id is not None:
                    product_id = int(product_id)

                    product, created = Product.objects.update_or_create(
                        id=product_id,
                        defaults=defaults,
                    )
                else:
                    product, created = Product.objects.update_or_create(
                        name=name,
                        defaults=defaults,
                    )

                if created:
                    created_count += 1
                    action = "დაემატა"
                else:
                    updated_count += 1
                    action = "განახლდა"

                print(
                    f"{number}/{len(data)} ✓ "
                    f"{action}: {product.name}"
                )

            except (
                ValueError,
                TypeError,
                OverflowError,
                InvalidOperation,
            ) as error:
                skipped_count += 1
                print(
                    f"{number}/{len(data)} ✗ "
                    f"ID: {item.get('id', '?')} — {error}"
                )

    print("\n================================")
    print("პროდუქტების ჩატვირთვა დასრულდა!")
    print(f"ახალი პროდუქტი: {created_count}")
    print(f"განახლებული პროდუქტი: {updated_count}")
    print(f"გამოტოვებული პროდუქტი: {skipped_count}")
    print(f"სულ ბაზაში არსებული პროდუქტი: {Product.objects.count()}")
    print("================================\n")


if __name__ == "__main__":
    import_products()
