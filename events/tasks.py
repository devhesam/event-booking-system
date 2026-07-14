from celery import shared_task
from django.utils import timezone

from events.models import Booking, BookingStatus


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_jitter=True,
             retry_kwargs={"max_retries": 3})
def expire_pending_bookings(self):
    now = timezone.now()

    expired_count = Booking.objects.filter(status=BookingStatus.PENDING, expires_at__lte=now).update(
        status=BookingStatus.EXPIRED, expired_at=now, updated_at=now)

    return expired_count
