# Event Booking System


This project provides a backend service for creating events and booking tickets with limited capacity.  
The main focus of the implementation is correctness under concurrent booking requests, idempotent booking behavior, reservation expiration, transaction handling, and clean architecture.

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
- Consistent response format with message codes
- Pytest-based test suite
- Celery periodic task for reservation expiration
- Django Admin support for Event and Booking management

---

## Tech Stack

- Python
- Django
- Django REST Framework
- MySQL
- Celery
- Redis
- pytest
- pytest-django

---

## Core Requirements Covered

### Event

Each event has:

- title
- description
- capacity
- event_date

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