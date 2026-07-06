from django.contrib import admin
from django.urls import include, path

from calendar_app import urls as calendar_urls
from conf.settings import FRONTEND_URL
from contact import urls as contact_urls
from workshop import urls as workshop_urls

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/auth/", include("djoser.urls")),
    path("api/v1/auth/", include("djoser.urls.jwt")),
    path("api/v1/workshop/", include(workshop_urls)),
    path("api/v1/contact/", include(contact_urls)),
    path("api/v1/calendar/", include(calendar_urls)),
]


# Customisize admin page
admin.site.site_header = "Admin Dashboard"
admin.site.site_title = "Admin Dashboard"
admin.site.index_title = "Heinapp"
admin.site.site_url = FRONTEND_URL
