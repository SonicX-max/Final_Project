# accounts/models.py
from django.db import models
from django.contrib.auth.models import AbstractUser

class CustomUser(AbstractUser):
    phone = models.CharField(max_length=20, blank=True, null=True, verbose_name="Телефон")
    address = models.CharField(max_length=255, blank=True, null=True, verbose_name="Адрес")
    telegram_id = models.BigIntegerField(blank=True, null=True, verbose_name="Telegram ID")

    def __str__(self):
        return self.username