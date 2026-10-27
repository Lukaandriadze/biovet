from django.conf import settings
from django.db import models
from django.contrib.auth.models import User
from categories.models import Category


class Product(models.Model):
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name="products",
        verbose_name="კატეგორია",
    )
    name = models.CharField("დასახელება", max_length=255)
    price = models.DecimalField("ფასი (₾)", max_digits=10, decimal_places=2)
    description = models.TextField("აღწერა", blank=True)
    img = models.URLField("სურათის ბმული", max_length=1000, blank=True)
    image = models.ImageField(
        "სურათი (ატვირთვა)", upload_to="products/", blank=True,
        help_text="თუ სურათს ატვირთავ, ის ბმულს ანაცვლებს.",
    )
    badge = models.CharField("ბეჯი", max_length=50, blank=True)
    is_active = models.BooleanField(
        "ჩანს საიტზე", default=True,
        help_text="გამორთვისას პროდუქტი საიტზე აღარ ჩანს, მაგრამ არ იშლება.",
    )
    created_at = models.DateTimeField("დამატების თარიღი", auto_now_add=True)

    class Meta:
        verbose_name = "პროდუქტი"
        verbose_name_plural = "პროდუქტები"
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # ატვირთული სურათი -> img ველში, რომ შაბლონებს ცვლილება არ დასჭირდეს
        upload_prefix = f"{settings.MEDIA_URL}products/"
        new_img = self.img
        if self.image:
            new_img = self.image.url
        elif self.img.startswith(upload_prefix):
            new_img = ""
        if new_img != self.img:
            self.img = new_img
            super().save(update_fields=['img'])


class Profile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile"
    )
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    address = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = "პროფილი"
        verbose_name_plural = "პროფილები"

    def __str__(self):
        return self.user.username
