from django.urls import path

from events.views import (
    BookTicketAPIView,
    CancelBookingAPIView,
    ConfirmBookingAPIView,
    EventCreateAPIView,
    EventDetailAPIView,
)

urlpatterns = [
    path("events/", EventCreateAPIView.as_view(), name="event-create"),
    path("events/<int:event_id>/", EventDetailAPIView.as_view(), name="event-detail"),
    path("events/<int:event_id>/book/", BookTicketAPIView.as_view(), name="book-ticket"),
    path("bookings/<int:booking_id>/confirm/", ConfirmBookingAPIView.as_view(), name="confirm-booking"),
    path("bookings/<int:booking_id>/cancel/", CancelBookingAPIView.as_view(), name="cancel-booking"),
]