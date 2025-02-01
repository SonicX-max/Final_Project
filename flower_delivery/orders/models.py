from django.db import models
from django.conf import settings
from django.utils.timezone import now  # Используем Django-aware datetime
from products.models import Product

ORDER_STATUS_CHOICES = [
    ('new', 'Новый'),
    ('processing', 'Обрабатывается'),
    ('delivered', 'Доставлен'),
    ('cancelled', 'Отменён'),
]

class Order(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name="Пользователь")
    products = models.ManyToManyField(Product, through='OrderItem', verbose_name="Товары")
    status = models.CharField(max_length=20, choices=ORDER_STATUS_CHOICES, default='new', verbose_name="Статус")
    created_at = models.DateTimeField(default=now, verbose_name="Дата заказа")  # Используем now() вместо auto_now_add
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    address = models.CharField(max_length=255, blank=True, null=True, verbose_name="Адрес доставки")
    phone = models.CharField(max_length=20, blank=True, null=True, verbose_name="Телефон")

    def get_total_price(self):
        """Подсчет общей стоимости заказа"""
        return sum(item.product.price * item.quantity for item in self.orderitem_set.all())

    def __str__(self):
        return f"Заказ #{self.id} от {self.user.username}"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"