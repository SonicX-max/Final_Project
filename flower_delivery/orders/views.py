import os
import sys
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from products.models import Product
from .models import Order, OrderItem

# Установка корневого пути проекта
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

@login_required
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, pk=product_id)
    order, created = Order.objects.get_or_create(user=request.user, status='new')
    order_item, item_created = OrderItem.objects.get_or_create(order=order, product=product)
    if not item_created:
        order_item.quantity += 1
        order_item.save()
    return redirect('order_detail', order_id=order.id)

@login_required
def order_detail(request, order_id):
    order = get_object_or_404(Order, pk=order_id, user=request.user)
    total_price = sum(item.product.price * item.quantity for item in order.orderitem_set.all())
    return render(request, 'orders/order_detail.html', {'order': order, 'total_price': total_price})

@login_required
def checkout(request, order_id):
    order = get_object_or_404(Order, pk=order_id, user=request.user)
    if request.method == 'POST':
        address = request.POST.get('address')
        phone = request.POST.get('phone')
        order.address = address
        order.phone = phone
        order.status = 'processing'
        order.save()
        return redirect('order_list')
    return render(request, 'orders/checkout.html', {'order': order})

@login_required
def order_list(request):
    orders = Order.objects.filter(user=request.user).exclude(status='new')
    for order in orders:
        order.total_price = sum(item.product.price * item.quantity for item in order.orderitem_set.all())
    return render(request, 'orders/order_list.html', {'orders': orders})

@login_required
def repeat_order(request, order_id):
    """
    Создаёт новый заказ на основе существующего заказа.
    """
    old_order = get_object_or_404(Order, pk=order_id, user=request.user)
    new_order = Order.objects.create(user=request.user, status='new')
    for item in old_order.orderitem_set.all():
        OrderItem.objects.create(order=new_order, product=item.product, quantity=item.quantity)
    return redirect('order_detail', order_id=new_order.id)

@login_required
def update_cart_item(request, item_id, action):
    item = get_object_or_404(OrderItem, pk=item_id, order__user=request.user, order__status='new')
    if action == "plus":
        item.quantity += 1
        item.save()
    elif action == "minus":
        if item.quantity > 1:
            item.quantity -= 1
            item.save()
        else:
            item.delete()
    elif action == "remove":
        item.delete()
    return redirect('order_detail', order_id=item.order_id)