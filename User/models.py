# User/models.py
import secrets
from datetime import timedelta

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

MAX_CODE_ATTEMPTS = 5
CODE_LIFETIME_MINUTES = 15
RESEND_COOLDOWN_SECONDS = 30


class EmailVerificationCode(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    code = models.CharField(max_length=6)
    attempts = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_expired(self):
        return timezone.now() > self.created_at + timedelta(minutes=CODE_LIFETIME_MINUTES)

    def is_locked(self):
        return self.attempts >= MAX_CODE_ATTEMPTS

    def can_resend(self):
        return timezone.now() >= self.created_at + timedelta(seconds=RESEND_COOLDOWN_SECONDS)

    @staticmethod
    def generate_code():
        # კრიპტოგრაფიულად უსაფრთხო 6-ციფრიანი კოდი
        return f"{secrets.randbelow(900000) + 100000}"

    def __str__(self):
        return f"{self.user.username}"
