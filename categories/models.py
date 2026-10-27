# categories/models.py
from django.db import models


class Category(models.Model):
    name = models.CharField(max_length=255)
    icon = models.CharField(
        max_length=100,
        blank=True,
        help_text="FontAwesome icon class, e.g. fa-solid fa-dog"
    )

    class Meta:
        verbose_name = "კატეგორია"
        verbose_name_plural = "კატეგორიები"

    def __str__(self):
        return self.name