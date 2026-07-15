from celery import shared_task
from django.db import transaction
from django.db.utils import OperationalError
from django.utils import timezone

from events.models import Booking, BookingStatus


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_jitter=True,
             retry_kwargs={"max_retries": 3})
def expire_pending_bookings(self):
    now = timezone.now()

    expired_count = Booking.objects.filter(status=BookingStatus.PENDING, expires_at__lte=now).update(
        status=BookingStatus.EXPIRED, expired_at=now, updated_at=now)

    return expired_count


@shared_task(
    bind=True,
    autoretry_for=(OperationalError,),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={"max_retries": 3},
    acks_late=True,
)
def confirm_booking_task(self, user_id, booking_id):
    now = timezone.now()

    with transaction.atomic():
        booking = (
            Booking.objects.select_for_update()
            .filter(id=booking_id, user_id=user_id)
            .first()
        )

        if booking is None:
            return "booking_not_found"

        if booking.status == BookingStatus.CONFIRMED:
            return "already_confirmed"

        if booking.status != BookingStatus.PENDING:
            return f"ignored_{booking.status}"

        if booking.expires_at <= now:
            booking.status = BookingStatus.EXPIRED
            booking.expired_at = now
            booking.save(update_fields=["status", "expired_at", "updated_at"])

            return "expired"

        booking.status = BookingStatus.CONFIRMED
        booking.confirmed_at = now
        booking.save(update_fields=["status", "confirmed_at", "updated_at"])

        return "confirmed"


@shared_task(
    bind=True,
    autoretry_for=(OperationalError,),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={"max_retries": 3},
    acks_late=True,
)
def cancel_booking_task(self, user_id, booking_id):
    now = timezone.now()

    with transaction.atomic():
        booking = (
            Booking.objects.select_for_update()
            .filter(id=booking_id, user_id=user_id)
            .first()
        )

        if booking is None:
            return "booking_not_found"

        if booking.status == BookingStatus.CANCELLED:
            return "already_cancelled"

        if booking.status not in [
            BookingStatus.PENDING,
            BookingStatus.CONFIRMED,
        ]:
            return f"ignored_{booking.status}"

        booking.status = BookingStatus.CANCELLED
        booking.cancelled_at = now
        booking.save(update_fields=["status", "cancelled_at", "updated_at"])

        return "cancelled"