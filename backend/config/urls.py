"""URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information see:
https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import: from my_app import views
    2. Add a URL to urlpatterns: path('', views.home, name='home')
Class-based views
    1. Add an import: from other_app.views import Home
    2. Add a URL to urlpatterns:
       path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function:
       from django.urls import include, path
    2. Add a URL to urlpatterns: path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.routers import DefaultRouter

from core.views import (
    AnalyticsView,
    CsrfView,
    DocumentViewSet,
    HealthView,
    LoginView,
    LogoutView,
    MeView,
    TemplateViewSet,
    UserViewSet,
)

router = DefaultRouter()
router.register("documents", DocumentViewSet, basename="document")
router.register("templates", TemplateViewSet, basename="template")
router.register("users", UserViewSet, basename="user")
urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include(router.urls)),
    path("api/health/", HealthView.as_view()),
    path("api/auth/csrf/", CsrfView.as_view()),
    path("api/auth/login/", LoginView.as_view()),
    path("api/auth/logout/", LogoutView.as_view()),
    path("api/auth/me/", MeView.as_view()),
    path("api/analytics/", AnalyticsView.as_view()),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema")),
]
