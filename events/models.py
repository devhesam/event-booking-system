from datetime import timedelta

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone


class Event(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    capacity = models.PositiveIntegerField()
    event_date = models.DateTimeField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=Q(capacity__gt=0),
                name="event_capacity_must_be_positive",
            )
        ]
        indexes = [
            models.Index(fields=["event_date"]),
        ]

    def __str__(self):
        return self.title

    @property
    def active_bookings_count(self):
        return self.bookings.filter(
            status__in=[
                BookingStatus.PENDING,
                BookingStatus.CONFIRMED,
            ]
        ).count()

    @property
    def confirmed_bookings_count(self):
        return self.bookings.filter(
            status=BookingStatus.CONFIRMED,
        ).count()

    @property
    def remaining_capacity(self):
        return max(self.capacity - self.active_bookings_count, 0)


class BookingStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    CONFIRMED = "CONFIRMED", "Confirmed"
    CANCELLED = "CANCELLED", "Cancelled"
    EXPIRED = "EXPIRED", "Expired"


def default_booking_expiration():
    return timezone.now() + timedelta(minutes=10)


class Booking(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="bookings")
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="bookings")

    status = models.CharField(max_length=20, choices=BookingStatus.choices, default=BookingStatus.PENDING)
    expires_at = models.DateTimeField(default=default_booking_expiration)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    expired_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "event"],
                condition=Q(
                    status__in=[
                        BookingStatus.PENDING,
                        BookingStatus.CONFIRMED,
                    ]
                ),
                name="unique_active_booking_per_user_event",
            )
        ]
        indexes = [
            models.Index(fields=["event", "status"]),
            models.Index(fields=["user", "event", "status"]),
            models.Index(fields=["status", "expires_at"]),
        ]

    def __str__(self):
        return f"{self.user_id} - {self.event_id} - {self.status}"

    @property
    def is_active(self):
        return self.status in [
            BookingStatus.PENDING,
            BookingStatus.CONFIRMED,
        ]

    @property
    def is_expired(self):
        return self.status == BookingStatus.PENDING and self.expires_at <= timezone.now()
