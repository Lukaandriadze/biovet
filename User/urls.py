from django.urls import path
from . import views

urlpatterns = [
    path('ajax/login/', views.ajax_login, name='ajax_login'),
    path('ajax/register/', views.ajax_register, name='ajax_register'),
    path('ajax/verify-code/', views.ajax_verify_code, name='ajax_verify_code'),
    path('ajax/resend-code/', views.ajax_resend_code, name='ajax_resend_code'),
    path('logout/', views.logout_view, name='logout'),
]