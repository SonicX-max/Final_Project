from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from products.models import Product
from .models import Review


@login_required
def add_review(request, product_id):
    product = get_object_or_404(Product, pk=product_id)

    if request.method == 'POST':
        text = request.POST.get('text', '').strip()
        rating = request.POST.get('rating')

        if not text:
            messages.error(request, "Отзыв не может быть пустым.")
            return redirect('product_detail', pk=product_id)

        try:
            rating = int(rating)
            if rating < 1 or rating > 5:
                raise ValueError
        except ValueError:
            messages.error(request, "Рейтинг должен быть числом от 1 до 5.")
            return redirect('product_detail', pk=product_id)

        Review.objects.create(user=request.user, product=product, text=text, rating=rating)
        messages.success(request, "Ваш отзыв успешно добавлен.")

    return redirect('product_detail', pk=product_id)  # Перенаправляем обратно к товару