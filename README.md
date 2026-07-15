# Event Booking System


This project provides a backend service for creating events and booking tickets with limited capacity.  
The main focus of the implementation is correctness under concurrent booking requests, idempotent booking behavior, reservation expiration, transaction handling, clean architecture, and maintainable API design.

---

## Features

- Create events with limited capacity
- Book tickets for an event
- Prevent overselling under concurrent requests
- Prevent duplicate active bookings per user/event
- Confirm pending bookings
- Cancel active bookings
- Automatically expire pending bookings after 10 minutes
- Return event detail with capacity information
- Centralized success/error message codes
- Custom exception handler
- Pytest-based test suite
- Celery periodic task for reservation expiration
- Optional async confirm/cancel flow controlled by feature flags
- Django Admin support for Event and Booking management
- Postman collection included

---

## Tech Stack

- Python
- Django
- Django REST Framework
- MySQL
- Celery
- Redis
- django-constance
- pytest
- pytest-django

---

## Domain Overview

### Event

Each event has:

- `title`
- `description`
- `capacity`
- `event_date`

Capacity must be a positive number.

### Booking

Each booking has one of the following statuses:

- `PENDING`
- `CONFIRMED`
- `CANCELLED`
- `EXPIRED`

A booking is considered active when its status is:

```text
PENDING or CONFIRMED
```

Only active bookings consume event capacity.

---

## API Endpoints

### Create Event

```http
POST /api/events/
```

Creates a new event.

Request example:

```json
{
  "title": "Backend Challenge Event",
  "description": "Test event booking system",
  "capacity": 100,
  "event_date": "2026-08-01T12:00:00Z"
}
```

Success response example:

```json
{
  "detail": "Event created successfully.",
  "code": 2000,
  "data": {
    "id": 1,
    "title": "Backend Challenge Event",
    "description": "Test event booking system",
    "capacity": 100,
    "event_date": "2026-08-01T12:00:00Z",
    "active_bookings_count": 0,
    "confirmed_bookings_count": 0,
    "remaining_capacity": 100,
    "created_at": "2026-07-15T10:00:00Z",
    "updated_at": "2026-07-15T10:00:00Z"
  }
}
```

---

### Get Event Detail

```http
GET /api/events/{event_id}/
```

Returns event information with capacity-related fields.

Response includes:

- total capacity
- active bookings count
- confirmed bookings count
- remaining capacity

Example response:

```json
{
  "detail": "Event detail retrieved successfully.",
  "code": 2001,
  "data": {
    "id": 1,
    "title": "Backend Challenge Event",
    "description": "Test event booking system",
    "capacity": 100,
    "event_date": "2026-08-01T12:00:00Z",
    "active_bookings_count": 5,
    "confirmed_bookings_count": 2,
    "remaining_capacity": 95,
    "created_at": "2026-07-15T10:00:00Z",
    "updated_at": "2026-07-15T10:00:00Z"
  }
}
```

---

### Book Ticket

```http
POST /api/events/{event_id}/book/
```

Books a ticket for the authenticated user.

Rules:

- The event capacity must not be exceeded.
- Each user can have only one active booking per event.
- The API is idempotent for repeated booking requests from the same user.
- A new booking is created with `PENDING` status.
- The user has 10 minutes to confirm the booking.

If the same user retries the booking request while an active booking already exists, the existing booking is returned instead of creating a duplicate booking.

---

### Confirm Booking

```http
POST /api/bookings/{booking_id}/confirm/
```

Confirms a pending booking.

Rules:

- Only `PENDING` bookings can be confirmed.
- If the booking is already expired based on `expires_at`, it is marked as `EXPIRED` and confirmation is rejected.
- On success, status changes to `CONFIRMED`.

---

### Cancel Booking

```http
POST /api/bookings/{booking_id}/cancel/
```

Cancels an active booking.

Rules:

- Only `PENDING` or `CONFIRMED` bookings can be cancelled.
- On success, status changes to `CANCELLED`.
- Cancelled bookings no longer consume event capacity.

---

## Response Format

The project uses centralized message codes.

Success response example:

```json
{
  "detail": "Booking created successfully.",
  "code": 2002,
  "data": {
    "id": 1,
    "event": 1,
    "event_title": "Backend Challenge Event",
    "status": "PENDING",
    "expires_at": "2026-07-15T10:10:00Z",
    "confirmed_at": null,
    "cancelled_at": null,
    "expired_at": null,
    "created_at": "2026-07-15T10:00:00Z",
    "updated_at": "2026-07-15T10:00:00Z"
  }
}
```

Error response example:

```json
{
  "detail": "Event is sold out.",
  "code": 4101
}
```

Validation error example:

```json
{
  "detail": "Validation error.",
  "code": 4001,
  "errors": {
    "capacity": [
      "Capacity must be a positive number."
    ]
  }
}
```

---

## Project Structure

```text
event-booking-system/
  config/
    settings.py
    urls.py
    celery.py

  events/
    admin.py
    models.py
    serializers.py
    services.py
    tasks.py
    urls.py
    views.py
    tests/

  utils/
    exception_handler.py
    message_handler/
      handler.py
      messages.py

  examples/
    postman.json

  Makefile
  pytest.ini
  requirements.txt
  README.md
```

---

## Architecture

The project separates responsibilities into clear layers:

### Models

`events/models.py`

Responsible for database schema, booking statuses, constraints, indexes, and computed capacity properties.

### Serializers

`events/serializers.py`

Responsible for request validation and response serialization.

### Services

`events/services.py`

Contains the main business logic for:

- booking tickets
- confirming bookings
- cancelling bookings
- preparing async confirm/cancel flows
- handling transaction boundaries
- applying row-level locks

### Views

`events/views.py`

Responsible for request/response handling only.  
Business logic is delegated to the service layer.

### Tasks

`events/tasks.py`

Contains Celery tasks for:

- expiring pending bookings
- async confirm flow
- async cancel flow

---

## Concurrency Strategy

The most important requirement is preventing overselling under concurrent booking requests.

The implementation uses:

- `transaction.atomic()`
- `select_for_update()`
- pessimistic locking on the `Event` row

When a user tries to book a ticket, the service locks the target event row.

Inside the same transaction:

1. Expired pending bookings for the same event are released.
2. Existing active booking for the same user/event is checked.
3. Active bookings are counted.
4. A new `PENDING` booking is created only if capacity is still available.

Because all booking attempts for the same event must acquire the same event row lock, concurrent booking requests for that event are serialized.

This guarantees that:

```text
active bookings count <= event capacity
```

---

## Why Lock the Event Row?

The capacity belongs to the event, not to a single booking.

Therefore, the critical section is:

```text
capacity check + booking creation
```

Locking the event row ensures that multiple users cannot simultaneously read the same available capacity and create more bookings than allowed.

---

## Idempotency Strategy

This project uses business-level idempotency.

The requirement says each user can have only one active booking for each event.  
Therefore, the following combination acts as a natural idempotency key:

```text
user + event + active booking status
```

Active statuses are:

```text
PENDING
CONFIRMED
```

Before creating a new booking, the service checks whether the user already has an active booking for the event.

If an active booking already exists, the existing booking is returned and no new booking is created.

This handles retry scenarios such as:

- The first request succeeds but the client does not receive the response.
- The client retries the same booking request.
- The server returns the already existing active booking instead of creating a duplicate.

A separate `idempotency_key` field was not added because the business rule itself provides idempotency for this challenge.

For payment-related or more complex production flows, an explicit `Idempotency-Key` header could be added.

---

## Expiration Strategy

Each booking is created in `PENDING` status with:

```text
expires_at = created_at + 10 minutes
```

A Celery periodic task runs every minute and expires all pending bookings whose expiration time has passed.

The task updates only bookings that are still:

```text
status = PENDING
expires_at <= now
```

This makes the task retry-safe.

If the task runs multiple times, already expired bookings are not updated again.

---

## Reliability of Expiration

The expiration system does not rely only on a single countdown task per booking.

Instead, the source of truth is stored in the database through the `expires_at` field.

This means:

- If a Celery worker restarts, expiration data is not lost.
- If the periodic task is delayed, expired bookings will be handled on the next run.
- If the task is retried, it will not corrupt booking state.
- If the user tries to confirm an expired booking before Celery runs, the service checks `expires_at` and rejects confirmation.

Expiration is also checked in two additional places:

### During Confirmation

If a booking is still `PENDING` but its `expires_at` has passed, it is marked as `EXPIRED` and confirmation is rejected.

### During Booking

Before counting active bookings for an event, expired pending bookings for that event are released.  
This prevents expired bookings from blocking capacity if Celery is delayed.

---

## Why Not Use Outbox Pattern?

The outbox pattern is useful when a database transaction must reliably trigger an external side effect, such as:

- sending a message to Kafka
- sending an email or SMS
- notifying another service
- syncing with an external system

For this challenge, expiration can be derived directly from the `Booking` table:

```text
PENDING bookings with expires_at in the past should become EXPIRED
```

Therefore, a separate outbox table is not required for the current scope.

If expiration needed to publish external events or trigger notifications in production, an outbox pattern would be a good next step.

---

## Confirm and Cancel Strategy

Confirm and cancel are direct user actions.

By default, they are handled synchronously inside the API/service layer because:

- the user expects an immediate result
- booking state should be updated immediately
- cancellation should release capacity as soon as possible in the synchronous flow

Both operations use:

- `transaction.atomic()`
- `select_for_update()` on the `Booking` row

This prevents race conditions between:

- confirm and cancel
- confirm and expiration
- cancel and expiration

---

## Feature Flags

This project uses `django-constance` to control whether confirm and cancel booking flows are processed synchronously or asynchronously.

Available flags:

```text
CONFIRM_BOOKING_ASYNC
CANCEL_BOOKING_ASYNC
```

These flags are editable from Django Admin through Constance.

### Synchronous Mode

If a flag is disabled, the API performs the operation synchronously and returns:

```text
200 OK
```

### Asynchronous Mode

If a flag is enabled, the API validates the request, queues a Celery task, and returns:

```text
202 Accepted
```

The final booking state is then updated by Celery workers.

### Feature Flag Trade-off

Asynchronous confirmation is safe for capacity because both `PENDING` and `CONFIRMED` bookings are active.

Asynchronous cancellation introduces eventual consistency for capacity release.  
This means capacity is released after the Celery worker processes the cancellation task, not immediately after the API response.

This is an intentional trade-off that can be controlled by the admin depending on current system load.

---

## Celery Tasks

The project includes these Celery tasks:

```text
expire_pending_bookings
confirm_booking_task
cancel_booking_task
```

### Run Celery Worker

```bash
celery -A config worker -l info
```

### Run Celery Beat

```bash
celery -A config beat -l info
```

The beat scheduler runs the expiration task every minute.

---

## Database Notes and Trade-offs

The original database design is PostgreSQL-oriented because PostgreSQL supports partial unique constraints, which are a clean way to enforce one active booking per user/event at the database level.

The model includes a conditional unique constraint for active bookings:

```text
user + event where status in (PENDING, CONFIRMED)
```

Due to local environment and time constraints, the project was implemented and tested with MySQL.

The main correctness guarantee for preventing overselling is handled by:

```text
transaction.atomic()
select_for_update()
Event row lock
```

In a production setup, the preferred option would be one of the following:

1. Use PostgreSQL and keep the partial unique constraint.
2. Adapt the MySQL schema with an `active_marker` field to enforce active booking uniqueness at the database level.

The current implementation keeps the design simple while still protecting the main concurrency requirement through row-level locking.

---

## Environment Variables

Create a `.env` file in the project root.

Example:

```env
SECRET_KEY=change-me
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

DB_ENGINE=django.db.backends.mysql
DB_NAME=event_booking
DB_USER=root
DB_PASS=password
DB_HOST=localhost
DB_PORT=3306

CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_TASK_ALWAYS_EAGER=False

PAGINATION_PAGE_SIZE=10
```

---

## Setup

### 1. Clone the Repository

```bash
git clone https://github.com/devhesam/event-booking-system.git
cd event-booking-system
```

### 2. Create Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies

```bash
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
```

Or use Makefile:

```bash
make install
```

### 4. Create Database

Create a MySQL database:

```sql
CREATE DATABASE event_booking CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 5. Run Migrations

```bash
python3 manage.py migrate
```

Or:

```bash
make migrate
```

### 6. Create Superuser

```bash
python3 manage.py createsuperuser
```

### 7. Run Development Server

```bash
python3 manage.py runserver
```

Or:

```bash
make server
```

---

## Running Redis

Celery requires Redis as broker.

If Redis is installed locally:

```bash
redis-server
```

---

## Running Celery

Run worker:

```bash
make worker
```

Run beat scheduler:

```bash
make beat
```

Or run directly:

```bash
celery -A config worker -l info
celery -A config beat -l info
```

---

## Running Tests

This project uses pytest.

Run all tests:

```bash
make test
```

Or:

```bash
python3 -m pytest -v
```

Run booking tests only:

```bash
make test-bookings
```

Or:

```bash
python3 -m pytest events/tests/test_booking.py -v
```

---

## Test Coverage

The test suite covers:

- event creation
- invalid capacity validation
- event detail capacity calculation
- duplicate active booking prevention
- capacity limit enforcement
- booking confirmation
- expired booking confirmation rejection
- booking cancellation
- capacity release after cancellation
- Celery expiration task
- retry-safe expiration behavior
- concurrent booking requests

The concurrency test simulates multiple users trying to book the same event at the same time and verifies that active bookings never exceed event capacity.

---

## Postman Collection

A Postman collection is included under:

```text
examples/postman.json
```

Before running the collection, set these variables:

```text
base_url
username
password
event_id
booking_id
```

---

## Admin Panel

The admin panel includes:

- Event management
- Booking management
- Event capacity information
- Active bookings count
- Confirmed bookings count
- Remaining capacity
- Admin action to expire selected pending bookings
- Admin action to run the expiration Celery task
- Constance feature flags for async confirm/cancel flow

---

## Makefile Commands

```bash
make install
make migrate
make makemigrations
make server
make check
make test
make test-bookings
make worker
make beat
make shell
make clean-pyc
```

---

## Important Design Decisions

### 1. Pessimistic Locking Instead of Optimistic Locking

Pessimistic locking was selected because correctness is more important than maximum throughput in this limited-capacity booking flow.

The implementation is simple, explicit, and safe for preventing overselling.

### 2. Event-Level Locking

The event row is locked because capacity belongs to the event.

This ensures all booking attempts for the same event are serialized.

### 3. Derived Remaining Capacity

Remaining capacity is not stored as a separate field.

It is calculated from:

```text
event.capacity - active bookings count
```

This avoids counter inconsistency.

For very high-scale production usage, a denormalized counter could be introduced with strict transaction handling.

### 4. Business-Level Idempotency

A separate `idempotency_key` field was not added because each user is allowed to have only one active booking per event.

This rule naturally prevents duplicate bookings for retried requests.

### 5. Periodic Expiration Instead of Per-Booking Countdown Task

A periodic task is more reliable than scheduling one countdown task per booking.

If the worker restarts, expired bookings are still recoverable from the database using `expires_at`.

### 6. Feature Flag Controlled Async Flow

Confirm and cancel flows can be switched between sync and async modes at runtime using Constance.

This allows the admin to control system behavior based on current load.

---

## Possible Future Improvements

- Add Docker and docker-compose
- Add Swagger/OpenAPI documentation
- Add explicit `Idempotency-Key` support for more complex request replay scenarios
- Add PostgreSQL as the recommended production database
- Add MySQL-compatible `active_marker` field for database-level active booking uniqueness
- Add pagination for booking list APIs if listing endpoints are added
- Add monitoring for Celery task failures
- Add structured logging
- Add CI pipeline for running tests automatically
- Add Sentry integration documentation
- Add load tests for high-concurrency booking scenarios

---

## Final Notes

The main goal of this implementation is correctness under concurrent booking requests.

The service ensures that:

```text
active bookings never exceed event capacity
```

This is achieved through transaction management, event-level row locking, idempotent booking logic, and retry-safe expiration handling.