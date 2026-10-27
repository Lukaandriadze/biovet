import csv

from django.contrib import admin, messages
from django.http import HttpResponse

from .models import Cart, CartItem, Order, OrderItem


# ------------------------------------------------------------------
# კალათა
# ------------------------------------------------------------------
class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    raw_id_fields = ("product",)


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ("user", "items_count", "total", "updated_at")
    search_fields = ("user__username", "user__email")
    raw_id_fields = ("user",)
    inlines = [CartItemInline]
    readonly_fields = ("created_at", "updated_at")

    @admin.display(description="რაოდენობა")
    def items_count(self, obj):
        return obj.get_items_count()

    @admin.display(description="ჯამი (₾)")
    def total(self, obj):
        return obj.get_total()


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ("cart", "product", "quantity")
    search_fields = ("cart__user__username", "product__name")
    raw_id_fields = ("cart", "product")


# ------------------------------------------------------------------
# შეკვეთა
# ------------------------------------------------------------------
def _status_action(status, label):
    @admin.action(description=f"სტატუსი: {label}")
    def action(modeladmin, request, queryset):
        count = queryset.update(status=status)
        modeladmin.message_user(request, f"{count} შეკვეთის სტატუსი: {label}.", messages.SUCCESS)

    action.__name__ = f"set_status_{status}"
    return action


@admin.action(description="CSV-ში ექსპორტი (Excel-ისთვის)")
def export_orders_csv(modeladmin, request, queryset):
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="orders.csv"'
    response.write("\ufeff")
    writer = csv.writer(response)
    writer.writerow([
        "ID", "იუზერი", "შეკვეთის №", "სახელი", "გვარი", "ტელეფონი", "ქალაქი", "მისამართი",
        "გადახდა", "სტატუსი", "პროდუქტების ჯამი", "მიწოდება", "სულ", "თარიღი", "პროდუქტები",
    ])
    for o in queryset.select_related("user").prefetch_related("items"):
        items = "; ".join(f"{i.product_name} x{i.quantity}" for i in o.items.all())
        writer.writerow([
            o.id, o.user.username, o.user_order_number, o.first_name, o.last_name, o.phone,
            o.city, o.address, o.get_payment_method_display(), o.get_status_display(),
            o.products_total, o.delivery_cost, o.total,
            o.created_at.strftime("%Y-%m-%d %H:%M"), items,
        ])
    return response


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    raw_id_fields = ("product",)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        "id", "user_order_number", "user", "full_name", "phone", "city",
        "payment_method", "status", "products_total", "delivery_cost", "total", "created_at",
    )
    list_display_links = ("id", "user_order_number", "user")
    list_editable = ("status",)
    list_filter = ("status", "payment_method", "city", "created_at")
    search_fields = (
        "user__username", "first_name", "last_name", "phone", "email", "address", "city",
        "items__product_name",
    )
    date_hierarchy = "created_at"
    list_per_page = 50
    list_select_related = ("user",)
    raw_id_fields = ("user", "cart")
    inlines = [OrderItemInline]
    save_on_top = True
    readonly_fields = (
        "user_order_number", "created_at", "access_token", "token_expires_at",
        "is_viewed", "telegram_message_id", "telegram_chat_id",
    )
    fieldsets = (
        ("შეკვეთა", {"fields": ("user", "user_order_number", "status", "payment_method", "created_at")}),
        ("მყიდველი", {"fields": ("first_name", "last_name", "phone", "email", "city", "address")}),
        ("ფინანსები", {
            "fields": ("products_total", "delivery_cost", "total", "items_count"),
            "description": "პროდუქტების შეცვლისას ჯამები ავტომატურად გადაითვლება შენახვისას.",
        }),
        ("სისტემური (Telegram / ტოკენი)", {
            "fields": ("cart", "telegram_message_id", "telegram_chat_id", "access_token",
                       "token_expires_at", "is_viewed"),
            "classes": ("collapse",),
        }),
    )
    actions = [
        _status_action("confirmed", "დადასტურებული"),
        _status_action("out_of_stock", "არ არის მარაგში"),
        _status_action("packing", "შეფუთვა"),
        _status_action("shipped", "გაგზავნილი"),
        _status_action("delivered", "მიტანილი"),
        _status_action("cancelled", "გაუქმებული"),
        _status_action("pending", "მოლოდინში"),
        export_orders_csv,
    ]

    @admin.display(description="სახელი, გვარი")
    def full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip()

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        # პროდუქტების ცვლილების შემდეგ ჯამების გადათვლა
        order = form.instance
        items = list(order.items.all())
        if items or change:
            order.products_total = sum(i.product_price * i.quantity for i in items)
            order.items_count = sum(i.quantity for i in items)
            order.total = order.products_total + order.delivery_cost
            order.save(update_fields=["products_total", "items_count", "total"])
