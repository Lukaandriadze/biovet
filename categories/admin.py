from django.contrib import admin
from django.db.models import Count
from django.urls import reverse
from django.utils.html import format_html

from .models import Category


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "icon", "products_link")
    list_display_links = ("id", "name")
    list_editable = ("icon",)
    search_fields = ("name",)
    ordering = ("name",)
    list_per_page = 100

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_products=Count("products"))

    @admin.display(description="პროდუქტები", ordering="_products")
    def products_link(self, obj):
        url = reverse("admin:products_product_changelist") + f"?category__id__exact={obj.pk}"
        return format_html('<a href="{}">{} პროდუქტი →</a>', url, obj._products)
