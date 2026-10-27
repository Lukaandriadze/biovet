from django.urls import path
from . import views


urlpatterns = [
    path("ai/",views.ai_page,name="ai-page"),

]