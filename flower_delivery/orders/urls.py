from django.urls import path
from . import views

urlpatterns = [
    path('add_to_cart/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('detail/<int:order_id>/', views.order_detail, name='order_detail'),
    path('update_cart_item/<int:item_id>/<str:action>/', views.update_cart_item, name='update_cart_item'),
    path('checkout/<int:order_id>/', views.checkout, name='checkout'),
    path('list/', views.order_list, name='order_list'),
    path('repeat/<int:order_id>/', views.repeat_order, name='repeat_order'),  # Повторить заказ
]