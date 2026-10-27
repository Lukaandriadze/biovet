from django.urls import path
from . import views

urlpatterns = [
    path ('', views.main_page, name='main_page'),
    path('product/', views.products_page, name='products'),
    path('product/<int:product_id>/', views.product_detail, name='product_detail'),
    path('profile/', views.profile_page, name='profile'),
    path('terms/', views.terms_page, name='terms'),
]