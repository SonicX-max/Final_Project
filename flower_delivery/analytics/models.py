from django.db import models
from orders.models import Order

class SalesReport(models.Model):
    # Для примера - отчёт за конкретную дату
    date = models.DateField()
    total_orders = models.IntegerField()
    total_revenue = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Отчёт за {self.date}"