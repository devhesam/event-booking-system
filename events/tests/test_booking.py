from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.db import close_old_connections
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from events.models import Booking, BookingStatus, Event
from events.services import BookingService
from events.tasks import expire_pending_bookings


User = get_user_model()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user(db):
    return User.objects.create_user(
        username="testuser",
        password="testpass123",
    )


@pytest.fixture
def authenticated_client(api_client, user):
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def event(db):
    return Event.objects.create(
        title="Backend Challenge Event",
        description="Test event",
        capacity=2,
        event_date=timezone.now() + timedelta(days=1),
    )


@pytest.mark.django_db
def test_create_event_successfully(authenticated_client):
    url = reverse("event-create")

    payload = {
        "title": "New Event",
        "description": "New event description",
        "capacity": 10,
        "event_date": (timezone.now() + timedelta(days=2)).isoformat(),
    }

    response = authenticated_client.post(url, payload, format="json")

    assert response.status_code == status.HTTP_201_CREATED
    assert Event.objects.count() == 1
    assert "data" in response.data
    assert response.data["data"]["capacity"] == 10


@pytest.mark.django_db
def test_create_event_with_invalid_capacity_fails(authenticated_client):
    url = reverse("event-create")

    payload = {
        "title": "Invalid Event",
        "description": "Invalid capacity",
        "capacity": 0,
        "event_date": (timezone.now() + timedelta(days=2)).isoformat(),
    }

    response = authenticated_client.post(url, payload, format="json")

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["code"] == 4001
    assert "errors" in response.data


@pytest.mark.django_db
def test_get_event_detail_returns_capacity_information(authenticated_client, user, event):
    Booking.objects.create(
        user=user,
        event=event,
        status=BookingStatus.PENDING,
        expires_at=timezone.now() + timedelta(minutes=10),
    )

    url = reverse("event-detail", kwargs={"event_id": event.id})

    response = authenticated_client.get(url)

    assert response.status_code == status.HTTP_200_OK
    assert response.data["data"]["capacity"] == 2
    assert response.data["data"]["active_bookings_count"] == 1
    assert response.data["data"]["confirmed_bookings_count"] == 0
    assert response.data["data"]["remaining_capacity"] == 1


@pytest.mark.django_db
def test_user_cannot_create_duplicate_active_booking(authenticated_client, user, event):
    url = reverse("book-ticket", kwargs={"event_id": event.id})

    first_response = authenticated_client.post(url)
    second_response = authenticated_client.post(url)

    assert first_response.status_code == status.HTTP_201_CREATED
    assert second_response.status_code == status.HTTP_200_OK

    active_bookings_count = Booking.objects.filter(
        user=user,
        event=event,
        status__in=[BookingStatus.PENDING, BookingStatus.CONFIRMED],
    ).count()

    assert active_bookings_count == 1
    assert first_response.data["data"]["id"] == second_response.data["data"]["id"]


@pytest.mark.django_db
def test_event_capacity_cannot_be_exceeded(api_client, user, event):
    second_user = User.objects.create_user(
        username="seconduser",
        password="testpass123",
    )
    third_user = User.objects.create_user(
        username="thirduser",
        password="testpass123",
    )

    BookingService.book_ticket(user=user, event_id=event.id)
    BookingService.book_ticket(user=second_user, event_id=event.id)

    api_client.force_authenticate(user=third_user)

    url = reverse("book-ticket", kwargs={"event_id": event.id})
    response = api_client.post(url)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["code"] == 4101

    active_bookings_count = Booking.objects.filter(
        event=event,
        status__in=[BookingStatus.PENDING, BookingStatus.CONFIRMED],
    ).count()

    assert active_bookings_count == 2
    assert active_bookings_count == event.capacity


@pytest.mark.django_db
def test_confirm_pending_booking_successfully(authenticated_client, user, event):
    booking, _ = BookingService.book_ticket(
        user=user,
        event_id=event.id,
    )

    url = reverse("confirm-booking", kwargs={"booking_id": booking.id})
    response = authenticated_client.post(url)

    booking.refresh_from_db()

    assert response.status_code == status.HTTP_200_OK
    assert booking.status == BookingStatus.CONFIRMED
    assert booking.confirmed_at is not None
    assert response.data["data"]["status"] == BookingStatus.CONFIRMED


@pytest.mark.django_db
def test_cannot_confirm_expired_booking(authenticated_client, user, event):
    booking = Booking.objects.create(
        user=user,
        event=event,
        status=BookingStatus.PENDING,
        expires_at=timezone.now() - timedelta(minutes=1),
    )

    url = reverse("confirm-booking", kwargs={"booking_id": booking.id})
    response = authenticated_client.post(url)

    booking.refresh_from_db()

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.data["code"] == 4203
    assert booking.status == BookingStatus.EXPIRED
    assert booking.expired_at is not None


@pytest.mark.django_db
def test_cancel_active_booking_successfully(authenticated_client, user, event):
    booking, _ = BookingService.book_ticket(
        user=user,
        event_id=event.id,
    )

    url = reverse("cancel-booking", kwargs={"booking_id": booking.id})
    response = authenticated_client.post(url)

    booking.refresh_from_db()

    assert response.status_code == status.HTTP_200_OK
    assert booking.status == BookingStatus.CANCELLED
    assert booking.cancelled_at is not None
    assert response.data["data"]["status"] == BookingStatus.CANCELLED


@pytest.mark.django_db
def test_cancelled_booking_releases_capacity(authenticated_client, user, event):
    booking, _ = BookingService.book_ticket(
        user=user,
        event_id=event.id,
    )

    cancel_url = reverse("cancel-booking", kwargs={"booking_id": booking.id})
    authenticated_client.post(cancel_url)

    detail_url = reverse("event-detail", kwargs={"event_id": event.id})
    response = authenticated_client.get(detail_url)

    assert response.status_code == status.HTTP_200_OK
    assert response.data["data"]["active_bookings_count"] == 0
    assert response.data["data"]["remaining_capacity"] == event.capacity


@pytest.mark.django_db
def test_expire_pending_bookings_task(user, event):
    booking = Booking.objects.create(
        user=user,
        event=event,
        status=BookingStatus.PENDING,
        expires_at=timezone.now() - timedelta(minutes=1),
    )

    expired_count = expire_pending_bookings()

    booking.refresh_from_db()

    assert expired_count == 1
    assert booking.status == BookingStatus.EXPIRED
    assert booking.expired_at is not None


@pytest.mark.django_db
def test_expire_pending_bookings_task_is_retry_safe(user, event):
    booking = Booking.objects.create(
        user=user,
        event=event,
        status=BookingStatus.PENDING,
        expires_at=timezone.now() - timedelta(minutes=1),
    )

    first_result = expire_pending_bookings()
    second_result = expire_pending_bookings()

    booking.refresh_from_db()

    assert first_result == 1
    assert second_result == 0
    assert booking.status == BookingStatus.EXPIRED


@pytest.mark.django_db(transaction=True)
def test_concurrent_booking_does_not_exceed_event_capacity():
    concurrent_event = Event.objects.create(
        title="Concurrent Event",
        description="Concurrency test",
        capacity=5,
        event_date=timezone.now() + timedelta(days=1),
    )

    users = [
        User.objects.create_user(
            username=f"user_{index}",
            password="testpass123",
        )
        for index in range(20)
    ]

    def book_ticket_for_user(user_id):
        close_old_connections()

        try:
            current_user = User.objects.get(id=user_id)
            BookingService.book_ticket(
                user=current_user,
                event_id=concurrent_event.id,
            )
            return True
        except Exception:
            return False
        finally:
            close_old_connections()

    user_ids = [item.id for item in users]

    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = [
            executor.submit(book_ticket_for_user, user_id)
            for user_id in user_ids
        ]

        for future in as_completed(futures):
            future.result()

    active_bookings_count = Booking.objects.filter(
        event=concurrent_event,
        status__in=[BookingStatus.PENDING, BookingStatus.CONFIRMED],
    ).count()

    assert active_bookings_count == concurrent_event.capacity
    assert active_bookings_count <= concurrent_event.capacity