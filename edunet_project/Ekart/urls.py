from django.urls import path

from . import views

urlpatterns = [
    path("", views.home),
    path("api/auth/login", views.login_view, name="login"),
    path("api/auth/register", views.register_view, name="register"),
    path("api/ai-suggest/", views.ai_suggest, name="ai_suggest"),
]
