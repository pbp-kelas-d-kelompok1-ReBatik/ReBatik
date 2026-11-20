"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.views.static import serve

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('main.urls')),
    path('batik_story/', include('batik_story.urls')),
    path('marketplace/', include('marketplace.urls')),
    path('rewards/', include('rewards.urls')),
    path('upcycling/', include('upcycling.urls')),
    path('donasi/', include('donasi.urls')),
    path('batik_custom/', include('batik_custom.urls')),
    path('impact-tracker/', include('impact_tracker.urls')),
    path('profile/', include('profiles.urls')),
    path('landing/', include('landing.urls')),
    path("api/v1/upcycling/", include("upcycling.api_urls")),

    # Web service Django REST Framework untuk aplikasi Flutter
    path('api/v1/auth/', include('main.api_urls')),
    path('api/v1/rewards/', include('rewards.api_urls')),
    path('api/v1/batik-story/', include('batik_story.api_urls')),
    path('api/v1/batik-custom/', include('batik_custom.api_urls')),
    path('api/v1/marketplace/', include('marketplace.api_urls')),
    path('api-auth/', include('rest_framework.urls')),
    # Serve uploaded media files on PWS
    re_path(
        r'^media/(?P<path>.*)$',
        serve,
        {'document_root': settings.MEDIA_ROOT},
    ),
]



