from django.urls import path

from . import views

urlpatterns = [
    path("events/", views.get_events, name="get_events"),
    path("events/create/", views.create_event, name="create_event"),
    path("events/<str:uid>/", views.update_event, name="update_event"),
    path("events/<str:uid>/delete/", views.delete_event, name="delete_event"),
    path("events/<str:uid>/exception/", views.create_exception, name="create_exception"),
    path("events/<str:uid>/occurrence/", views.delete_occurrence, name="delete_occurrence"),
]
