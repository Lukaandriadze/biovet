
import os
import django
import json
from decimal import Decimal, InvalidOperation
from pathlib import Path

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from products.models import Product
from categories.models import Category


# fixed_products.json მდებარეობს manage.py-ს გვერდით
json_path = Path(__file__).resolve().parent / "fixed_products.json"

with open(json_path, "r", encoding="utf-8") as file:
    data = json.load(file)

if isinstance(data, dict):
    data = data.get("products", [data])

print(f"JSON-ში ნაპოვნია {len(data)} პროდუქტი\n")

created_count = 0
updated_count = 0
skipped_count = 0

for number, item in enumerate(data, start=1):
    try:
        category_names = item.get("category", [])

        if not isinstance(category_names, list):
            category_names = [category_names] if category_names else []

        category_name = (
            str(category_names[0]).strip()
            if category_names and str(category_names[0]).strip()
            else "სხვა"
        )

        category, _ = Category.objects.get_or_create(
            name=category_name
        )

        images = item.get("images", [])

        if not isinstance(images, list):
            images = [images] if images else []

        img_url = images[0] if images else ""

        # თუ ფასი აკლია ან null-ია, ჩაიწეროს 0
        raw_price = item.get("price")
        price = Decimal(str(raw_price)).quantize(Decimal("0.01")) if raw_price is not None and str(raw_price).strip() else Decimal("0")

        product_id = item.get("id")

        defaults = {
            "category": category,
            "name": str(item.get("name", "")).strip(),
            "price": price,
            "description": item.get("description") or "",
            "img": img_url or "",
            "badge": item.get("badge") or "",
        }

        if not defaults["name"]:
            skipped_count += 1
            print(f"{number}/{len(data)} გამოტოვებულია — სახელი არ აქვს")
            continue

        if product_id is not None:
            product, created = Product.objects.update_or_create(
                id=int(product_id),
                defaults=defaults,
            )
        else:
            product, created = Product.objects.update_or_create(
                name=defaults["name"],
                defaults=defaults,
            )

        if created:
            created_count += 1
            action = "დაემატა"
        else:
            updated_count += 1
            action = "განახლდა"

        print(f"{number}/{len(data)} ✓ {action}: {product.name}")

    except (ValueError, TypeError, OverflowError, InvalidOperation) as error:
        skipped_count += 1
        print(
            f"{number}/{len(data)} ✗ "
            f"ID: {item.get('id', '?')} — {error}"
        )

print("\n============================")
print("ჩატვირთვა დასრულდა!")
print(f"ახალი პროდუქტი: {created_count}")
print(f"განახლებული პროდუქტი: {updated_count}")
print(f"გამოტოვებული პროდუქტი: {skipped_count}")
print("============================")
