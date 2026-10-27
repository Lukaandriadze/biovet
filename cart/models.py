from django.db import models, transaction
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models import Max
import secrets

from products.models import Product


class Cart(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="cart"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s Cart"

    def get_total(self):
        return sum(item.total_price() for item in self.items.all())

    def get_items_count(self):
        return sum(item.quantity for item in self.items.all())

    def is_empty(self):
        return not self.items.exists()

    def clear(self):
        self.items.all().delete()


class CartItem(models.Model):
    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name="items"
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="cart_items"
    )
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ('cart', 'product')
        ordering = ['id']

    def total_price(self):
        return self.product.price * self.quantity

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"


# ============================================================
# 🔥 ORDER
# ============================================================
class Order(models.Model):
    PAYMENT_CHOICES = [
        ('cash', 'ნაღდი ფული'),
        ('card', 'ბარათი'),
        ('transfer', 'საბანკო გადარიცხვა'),
    ]

    STATUS_CHOICES = [
        ('pending', 'მოლოდინში'),
        ('confirmed', 'დადასტურებული'),
        ('out_of_stock', 'არ არის მარაგში'),
        ('packing', 'შეფუთვა'),
        ('shipped', 'გაგზავნილი'),
        ('delivered', 'მიტანილი'),
        ('cancelled', 'გაუქმებული'),
    ]

    cart = models.ForeignKey(
        Cart,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='orders',
        verbose_name='მომხმარებელი'
    )

    user_order_number = models.PositiveIntegerField(
        default=0,
        verbose_name='შეკვეთის ნომერი (იუზერის)'
    )

    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=30)
    email = models.EmailField(blank=True)
    address = models.TextField()
    city = models.CharField(max_length=100, blank=True)

    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_CHOICES,
        default='cash'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )

    # 🔥 ფინანსური ველები
    products_total = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name='პროდუქტების ჯამი'
    )
    delivery_cost = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name='მიწოდების ღირებულება'
    )
    total = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        verbose_name='სულ გადასახდელი'
    )
    items_count = models.PositiveIntegerField(default=0)

    # 🔥 Telegram ველები
    telegram_message_id = models.BigIntegerField(
        null=True, blank=True, verbose_name="Telegram message ID"
    )
    telegram_chat_id = models.CharField(
        max_length=50, blank=True, null=True, verbose_name="Telegram chat ID"
    )

    access_token = models.CharField(
        max_length=64,
        unique=True,
        blank=True,
        null=True,
        db_index=True
    )
    token_expires_at = models.DateTimeField(blank=True, null=True)
    is_viewed = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'შეკვეთა'
        verbose_name_plural = 'შეკვეთები'

    def __str__(self):
        return f"#{self.user_order_number} — {self.user.username} — ₾{self.total}"

    def save(self, *args, **kwargs):
        if not self.user_order_number:
            with transaction.atomic():
                # იუზერის რიგს ვბლოკავთ, რომ ორმა ერთდროულმა შეკვეთამ ერთი ნომერი არ აიღოს
                User.objects.select_for_update().filter(pk=self.user_id).first()
                last_order = (
                    Order.objects
                    .filter(user=self.user)
                    .aggregate(max_num=Max('user_order_number'))
                )
                self.user_order_number = (last_order['max_num'] or 0) + 1
                super().save(*args, **kwargs)
            return

        super().save(*args, **kwargs)

    def generate_token(self, minutes=10):
        self.access_token = secrets.token_urlsafe(32)
        self.token_expires_at = timezone.now() + timezone.timedelta(minutes=minutes)
        self.is_viewed = False
        self.save(update_fields=['access_token', 'token_expires_at', 'is_viewed'])
        return self.access_token

    def is_token_valid(self):
        if not self.access_token or self.is_viewed:
            return False
        if not self.token_expires_at:
            return False
        return timezone.now() <= self.token_expires_at

    def mark_viewed(self):
        self.is_viewed = True
        self.save(update_fields=['is_viewed'])

    def save_items_from_cart(self, cart):
        bulk_items = []
        for cart_item in cart.items.select_related('product').all():
            bulk_items.append(OrderItem(
                order=self,
                product=cart_item.product,
                product_name=cart_item.product.name,
                product_price=cart_item.product.price,
                quantity=cart_item.quantity,
            ))
        if bulk_items:
            OrderItem.objects.bulk_create(bulk_items)


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='order_items'
    )

    product_name = models.CharField(max_length=200)
    product_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ['id']
        verbose_name = 'შეკვეთის პროდუქტი'
        verbose_name_plural = 'შეკვეთის პროდუქტები'

    @property
    def total_price(self):
        return self.product_price * self.quantity

    def __str__(self):
        return f"{self.product_name} x {self.quantity}"