from django.shortcuts import render, get_object_or_404
from .models import Product
from reviews.models import Review


def product_list(request):
    products = Product.objects.all()
    return render(request, 'products/product_list.html', {'products': products})


def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk)
    reviews = Review.objects.filter(product=product).order_by(
        '-created_at')  # Сортировка отзывов по дате (новые сверху)

    return render(request, 'products/product_detail.html', {'product': product, 'reviews': reviews})