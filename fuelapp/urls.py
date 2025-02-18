"""fuelapp URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.11/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls import include
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, re_path
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from rest_framework import permissions

# from base.urls import base_urls
from appointment.urls import appointment_urls
from clinic.urls import clinic_urls
from payment.urls import payment_urls
from user.urls import user_urls
from base.urls import base_urls
from notification.urls import notification_urls
from report.urls import report_urls

schema_view = get_schema_view(
    openapi.Info(
        title="Fuel API",
        default_version='v1',
        description="API used on Fuel application",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="abdul.nazurudeen@gmail.com"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
)

urlpatterns = [
    re_path(r'^swagger(?P<format>\.json|\.yaml)$',
            schema_view.without_ui(cache_timeout=0), name='schema-json'),
    re_path(r'^swagger/$', schema_view.with_ui('swagger',
                                               cache_timeout=0),
            name='schema-swagger-ui'),
    re_path(r'^redoc/$', schema_view.with_ui('redoc',
                                             cache_timeout=0),
            name='schema-redoc'),
    path('admin/', admin.site.urls),
    path('admin/base/', include(base_urls)),

    path('api/', include(user_urls + clinic_urls + appointment_urls +
                         payment_urls + notification_urls + report_urls)),
    # path('api/auth/', include('knox.urls'))
    path('', include(base_urls)),
]

urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
