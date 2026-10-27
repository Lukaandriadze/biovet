from django.urls import path
from . import views

urlpatterns = [
    path('ajax/login/', views.ajax_login, name='ajax_login'),
    path('ajax/register/', views.ajax_register, name='ajax_register'),
    path('logout/', views.logout_view, name='logout'),
]
