from django.shortcuts import render
from django.db.models import Sum, Count, F
from orders.models import Order, OrderItem
from datetime import date, timedelta

def dashboard(request):
    """
    Расширенная аналитика с возможностью выбрать период (в днях).
    По умолчанию 30 дней.
    Выводим:
    - Кол-во заказов
    - Суммарная выручка
    - Детальный список заказов (адрес, телефон, статус, товары)
    """

    # 1. Считываем период (days) из GET-параметра, иначе 30
    days_str = request.GET.get('days', '30')
    try:
        days = int(days_str)
    except ValueError:
        days = 30  # fallback

    # 2. Вычисляем дату, начиная с которой берём заказы
    today = date.today()
    start_date = today - timedelta(days=days)

    # 3. Фильтруем заказы, созданные после start_date
    #    (Можно фильтровать по статусу, если нужно)
    orders_qs = Order.objects.filter(created_at__gte=start_date)

    # 4. Подсчитываем общее кол-во заказов за период
    total_orders = orders_qs.count()

    # 5. Считаем суммарную выручку, идём по OrderItem
    order_items = OrderItem.objects.filter(order__in=orders_qs)
    total_revenue = sum(item.quantity * item.product.price for item in order_items)

    # Пример: можно получить популярность товаров:
    # product_popularity = (
    #     order_items.values('product__name')
    #     .annotate(total_qty=Sum('quantity'))
    #     .order_by('-total_qty')[:5]
    # )

    # 6. Передаём всё в шаблон
    context = {
        'days': days,  # чтобы в шаблоне отобразить или использовать
        'orders': orders_qs,  # передадим, чтобы отобразить детальнее
        'total_orders': total_orders,
        'total_revenue': total_revenue,
        # 'product_popularity': product_popularity,
    }
    return render(request, 'analytics/dashboard.html', context)