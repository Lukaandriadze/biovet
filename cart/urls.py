from django.urls import path
from . import views

urlpatterns = [
    # Cart API (AJAX)
    path('', views.cart_detail, name='cart_detail'),
    path('add/<int:product_id>/', views.cart_add, name='cart_add'),
    path('increase/<int:item_id>/', views.cart_increase, name='cart_increase'),
    path('decrease/<int:item_id>/', views.cart_decrease, name='cart_decrease'),
    path('remove/<int:item_id>/', views.cart_remove, name='cart_remove'),
    path('clear/', views.cart_clear, name='cart_clear'),
    path('checkout/', views.checkout, name='checkout'),
    path('order-success/', views.order_success, name='order_success'),

    # 🔥 ავტო-განახლებისთვის
    path('api/order-status/', views.order_status_api, name='order_status_api'),
]