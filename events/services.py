from datetime import timedelta

from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework import exceptions

from events.models import Booking, BookingStatus, Event
from utils.message_handler.handler import get_message
from utils.message_handler import messages


ACTIVE_BOOKING_STATUSES = [
    BookingStatus.PENDING,
    BookingStatus.CONFIRMED,
]


class BookingService:
    BOOKING_EXPIRATION_MINUTES = 10

    @classmethod
    def book_ticket(cls, *, user, event_id):
        now = timezone.now()

        with transaction.atomic():
            try:
                event = Event.objects.select_for_update().get(id=event_id)
            except Event.DoesNotExist:
                raise exceptions.NotFound(
                    get_message(messages.ERROR_EVENT_NOT_FOUND)
                )

            cls._expire_due_pending_bookings_for_event(event=event, now=now)

            existing_booking = Booking.objects.filter(
                user=user,
                event=event,
                status__in=ACTIVE_BOOKING_STATUSES,
            ).first()

            if existing_booking:
                return existing_booking, False

            active_bookings_count = Booking.objects.filter(
                event=event,
                status__in=ACTIVE_BOOKING_STATUSES,
            ).count()

            if active_bookings_count >= event.capacity:
                raise exceptions.ParseError(
                    get_message(messages.ERROR_EVENT_SOLD_OUT)
                )

            try:
                booking = Booking.objects.create(
                    user=user,
                    event=event,
                    status=BookingStatus.PENDING,
                    expires_at=now + timedelta(minutes=cls.BOOKING_EXPIRATION_MINUTES),
                )
            except IntegrityError:
                booking = Booking.objects.filter(
                    user=user,
                    event=event,
                    status__in=ACTIVE_BOOKING_STATUSES,
                ).first()

                if booking:
                    return booking, False

                raise exceptions.ParseError(
                    get_message(messages.ERROR_DUPLICATE_ACTIVE_BOOKING)
                )

            return booking, True

    @classmethod
    def confirm_booking(cls, *, user, booking_id):
        now = timezone.now()
        booking_is_expired = False

        with transaction.atomic():
            booking = (
                Booking.objects.select_for_update()
                .select_related("event")
                .filter(id=booking_id, user=user)
                .first()
            )

            if booking is None:
                raise exceptions.NotFound(
                    get_message(messages.ERROR_BOOKING_NOT_FOUND)
                )

            if booking.status != BookingStatus.PENDING:
                raise exceptions.ParseError(
                    get_message(messages.ERROR_INVALID_BOOKING_STATE)
                )

            if booking.expires_at <= now:
                booking.status = BookingStatus.EXPIRED
                booking.expired_at = now
                booking.save(update_fields=["status", "expired_at", "updated_at"])

                booking_is_expired = True
            else:
                booking.status = BookingStatus.CONFIRMED
                booking.confirmed_at = now
                booking.save(update_fields=["status", "confirmed_at", "updated_at"])

                return booking

        if booking_is_expired:
            raise exceptions.ParseError(
                get_message(messages.ERROR_BOOKING_EXPIRED)
            )

    @classmethod
    def cancel_booking(cls, *, user, booking_id):
        now = timezone.now()

        with transaction.atomic():
            booking = (
                Booking.objects.select_for_update()
                .select_related("event")
                .filter(id=booking_id, user=user)
                .first()
            )

            if booking is None:
                raise exceptions.NotFound(
                    get_message(messages.ERROR_BOOKING_NOT_FOUND)
                )

            if booking.status not in ACTIVE_BOOKING_STATUSES:
                raise exceptions.ParseError(
                    get_message(messages.ERROR_INVALID_BOOKING_STATE)
                )

            booking.status = BookingStatus.CANCELLED
            booking.cancelled_at = now
            booking.save(update_fields=["status", "cancelled_at", "updated_at"])

            return booking

    @staticmethod
    def _expire_due_pending_bookings_for_event(*, event, now):
        Booking.objects.filter(
            event=event,
            status=BookingStatus.PENDING,
            expires_at__lte=now,
        ).update(
            status=BookingStatus.EXPIRED,
            expired_at=now,
            updated_at=now,
        )