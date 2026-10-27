from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('mwvane/', admin.site.urls),
    # path("", include("AI.urls")),  # AI დაუმთავრებელი ფუნქცია, ამიტომ დროებით გამორთულია
    path("", include("products.urls")),
    path('users/', include('User.urls')),
    path("cart/", include("cart.urls")),
    path('accounts/', include('allauth.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
