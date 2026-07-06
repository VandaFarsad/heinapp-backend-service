from django.urls import path

from . import views

urlpatterns = [
    path("slots/available-slots/", views.available_slots, name="workshop-available-slots"),
    path("slots/book-slot/", views.book_slot, name="workshop-book-slot"),
    path("slots/cancel-slot/", views.cancel_slot, name="workshop-cancel-slot"),
]
