# EventHub - Event Ticketing Platform API

EventHub is a backend RESTful API built with **Django** and **Django REST Framework (DRF)** for an event ticketing platform. It provides endpoints to browse events, reserve seats with real-time availability checks, and cancel reservations with automatic seat restoration.

---

## Table of Contents
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [How to Run the Project](#how-to-run-the-project)
  - [Local Setup](#1-local-setup)
  - [Docker Setup](#2-docker-setup)
- [API Endpoints Overview](#api-endpoints-overview)
- [Detailed API Specifications & Examples](#detailed-api-specifications--examples)
  - [1. Create an Event](#1-create-an-event)
  - [2. Successful Reservation (201 Created)](#2-successful-reservation-201-created)
  - [3. Overbooking Failure (400 Bad Request)](#3-overbooking-failure-400-bad-request)
  - [4. Successful Cancellation & Seat Restoration](#4-successful-cancellation--seat-restoration)
  - [5. Filter Events & Reservations](#5-filter-events--reservations)
- [Design Decisions](#design-decisions)
- [Running Automated Tests](#running-automated-tests)

---

## Features
- **Event Management**: Create, list, retrieve, update, and filter events by `status` and `venue`.
- **Computed Fields**: Dynamic `reservations_count` computed via `SerializerMethodField` to track confirmed bookings.
- **Seat Availability Validation**: Validates that reservations do not exceed available seats and that `available_seats` cannot exceed `total_seats`.
- **Automatic Seat Management**:
  - Reserving seats automatically deducts from `event.available_seats`.
  - Cancelling a reservation automatically restores seats to `event.available_seats`.
- **Status Guards**: Prevents reserving seats for completed or cancelled events, and blocks double cancellations.
- **Request Logging Middleware**: Logs HTTP method, URL path, response status code, and execution duration for every incoming request.

---

## Tech Stack
- **Framework**: Django 6.x
- **API Toolkit**: Django REST Framework (DRF) 3.18+
- **Database**: SQLite
- **Containerization**: Docker & Docker Compose

---

## Project Structure

```text
eventhub/
├── manage.py
├── requirements.txt
├── DockerFile
├── docker-compose.yml
├── README.md
├── eventhub/
│   ├── __init__.py
│   ├── asgi.py
│   ├── settings.py       # Installed apps, middleware & logging config
│   ├── urls.py           # Root URL routing (/api/ & /)
│   └── wsgi.py
└── events/
    ├── __init__.py
    ├── admin.py          # Django admin configuration
    ├── apps.py
    ├── middleware.py     # RequestLoggingMiddleware
    ├── models.py         # Event and Reservation models
    ├── serializers.py    # EventSerializer and ReservationSerializer
    ├── tests.py          # Comprehensive test suite (9 test cases)
    ├── urls.py           # DefaultRouter configuration for ViewSets
    └── views.py          # EventViewSet and ReservationViewSet
```

---

## How to Run the Project

### 1. Local Setup

#### Prerequisites
- Python 3.10+ (tested on Python 3.14)
- `pip`

#### Steps

1. **Clone or Navigate to the Repository**:
   ```bash
   cd eventhub
   ```

2. **(Optional) Create and Activate a Virtual Environment**:
   ```bash
   # Windows (PowerShell)
   python -m venv venv
   .\venv\Scripts\Activate.ps1

   # Linux / macOS
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Run Database Migrations**:
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

5. **(Optional) Create a Superuser for Django Admin**:
   ```bash
   python manage.py createsuperuser
   ```

6. **Start the Development Server**:
   ```bash
   python manage.py runserver
   ```
   The API will be available at `http://127.0.0.1:8000/`.

---

### 2. Docker Setup

You can build and start the application container using Docker Compose:

```bash
# Build and run the container
docker compose up --build

# Run migrations inside the container
docker compose exec event-hub-web python manage.py migrate
```

---

## API Endpoints Overview

| Method | Endpoint | Description | Query Parameters |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/events/` | List all events | `?status=<status>&venue=<venue>` |
| `POST` | `/api/events/` | Create a new event | None |
| `GET` | `/api/events/{id}/` | Retrieve single event details | None |
| `PUT` | `/api/events/{id}/` | Update all fields of an event | None |
| `PATCH` | `/api/events/{id}/` | Partially update an event | None |
| `DELETE` | `/api/events/{id}/` | Delete an event | None |
| `GET` | `/api/reservations/` | List reservations | `?event_id=<id>` |
| `POST` | `/api/reservations/` | Reserve seats for an event | None |
| `GET` | `/api/reservations/{id}/` | Retrieve reservation details | None |
| `POST` | `/api/reservations/{id}/cancel/` | Cancel reservation & restore seats | None |

---

## Detailed API Specifications & Examples

### 1. Create an Event

**Request**:
- **Method**: `POST`
- **URL**: `/api/events/`
- **Headers**: `Content-Type: application/json`
- **Body**:
  ```json
  {
    "title": "PyCon India 2025",
    "venue": "NIMHANS Convention Centre, Bangalore",
    "date": "2025-09-20",
    "total_seats": 500,
    "available_seats": 500,
    "status": "upcoming"
  }
  ```

**Response (`201 Created`)**:
```json
{
  "id": 1,
  "title": "PyCon India 2025",
  "venue": "NIMHANS Convention Centre, Bangalore",
  "date": "2025-09-20",
  "total_seats": 500,
  "available_seats": 500,
  "status": "upcoming",
  "created_at": "2026-10-22T08:10:00.000000Z",
  "reservations_count": 0
}
```

---

### 2. Successful Reservation (201 Created)

When an attendee books seats for an event with sufficient capacity:
1. Seat availability is verified.
2. `seats_reserved` are deducted from the event's `available_seats`.
3. A new `Reservation` record is created with `status: "confirmed"`.

**Request**:
- **Method**: `POST`
- **URL**: `/api/reservations/`
- **Headers**: `Content-Type: application/json`
- **Body**:
  ```json
  {
    "event": 1,
    "attendee_name": "Priya Sharma",
    "attendee_email": "priya@example.com",
    "seats_reserved": 2
  }
  ```

**Response (`201 Created`)**:
```json
{
  "id": 1,
  "event": 1,
  "attendee_name": "Priya Sharma",
  "attendee_email": "priya@example.com",
  "seats_reserved": 2,
  "status": "confirmed",
  "created_at": "2026-10-22T08:11:00.000000Z"
}
```

---

### 3. Overbooking Failure (400 Bad Request)

If an attendee attempts to reserve more seats than currently available in `event.available_seats`, the request is rejected with a validation error, and no database changes occur.

**Request**:
- **Method**: `POST`
- **URL**: `/api/reservations/`
- **Headers**: `Content-Type: application/json`
- **Body**:
  ```json
  {
    "event": 1,
    "attendee_name": "Rahul Verma",
    "attendee_email": "rahul@example.com",
    "seats_reserved": 501
  }
  ```

**Response (`400 Bad Request`)**:
```json
{
  "non_field_errors": [
    "Only 498 seat(s) available."
  ]
}
```

#### Additional Validation Safeguards:
- **Reserving seats on inactive events**: If an event status is `completed` or `cancelled`:
  ```json
  {
    "non_field_errors": [
      "Cannot reserve seats for a completed event."
    ]
  }
  ```
- **Invalid seat count**: If `seats_reserved` is `< 1`:
  ```json
  {
    "seats_reserved": [
      "Must reserve at least 1 seat."
    ]
  }
  ```

---

### 4. Successful Cancellation & Seat Restoration

To cancel a confirmed reservation, issue a `POST` request to `/api/reservations/{id}/cancel/`. No request body is required.

**Request**:
- **Method**: `POST`
- **URL**: `/api/reservations/1/cancel/`
- **Headers**: `Content-Type: application/json`
- **Body**: *(empty)*

**Response (`200 OK`)**:
```json
{
  "id": 1,
  "event": 1,
  "attendee_name": "Priya Sharma",
  "attendee_email": "priya@example.com",
  "seats_reserved": 2,
  "status": "cancelled",
  "created_at": "2026-10-22T08:11:00.000000Z"
}
```

#### Already Cancelled (Idempotency Guard - `400 Bad Request`):
If a user attempts to cancel a reservation that has already been cancelled:
```json
{
  "error": "Already cancelled."
}
```

---

### 5. Filter Events & Reservations

- **Filter Events by Status**:
  ```http
  GET /api/events/?status=upcoming
  ```
- **Filter Events by Venue (Case-Insensitive Match)**:
  ```http
  GET /api/events/?venue=bangalore
  ```
- **Filter Reservations by Event ID**:
  ```http
  GET /api/reservations/?event_id=1
  ```

---

## Design Decisions

### Coupled Seat Deduction Inside `ReservationSerializer.create()`
- **Decision**: The decrement of `event.available_seats` and the creation of the `Reservation` record are co-located directly inside the serializer's `create()` method:
  ```python
  def create(self, validated_data):
      event = validated_data['event']
      event.available_seats -= validated_data['seats_reserved']
      event.save()
      return Reservation.objects.create(**validated_data)
  ```
- **Why this was chosen**:
  1. **Encapsulation & Single Responsibility**: The business rule that a reservation deducts available seats is tied directly to the lifecycle of creating a reservation. Co-locating this logic inside `create()` ensures that no reservation can be created via the API without executing the seat deduction logic.
  2. **Consistency Across Views**: Whether the reservation is created via `ModelViewSet`, an API view, or automated test cases, the validation and deduction logic remain unified in one place.
  3. **Concurrency Path Forward**: In a high-traffic production environment with simultaneous booking requests, this design cleanly supports wrapping the deduction in Django's `transaction.atomic()` and querying with `Event.objects.select_for_update()` to prevent race conditions without needing changes to views or URL routes.

### Custom `@action` for Explicit Cancellation Lifecycle
- **Decision**: Implemented reservation cancellation as a custom detail POST action (`/api/reservations/{id}/cancel/`) rather than relying on a generic `DELETE` or `PATCH` request.
- **Why this was chosen**:
  1. **Auditability & Soft Deletion**: Ticketing platforms require reservation history for auditing, refunds, and attendance records. Using a dedicated cancel action preserves the record with `status='cancelled'` while restoring available seats.
  2. **Double-Cancellation Prevention**: The action explicitly checks `if reservation.status == 'cancelled'` and returns an HTTP 400 error (`Already cancelled.`), protecting against accidental double-restoration of seats.

---

## Running Automated Tests

A comprehensive test suite is located in `events/tests.py` covering:
- Event creation and `available_seats <= total_seats` validation
- Listing and filtering events by `status` and `venue`
- Successful reservation seat deduction and `reservations_count` updates
- Overbooking attempts returning `400 Bad Request`
- Attempting to reserve seats for `completed` events
- Reserving non-positive seat counts
- Successful reservation cancellation and seat restoration
- Idempotency check on already cancelled reservations
- Filtering reservations by `event_id`

To execute the test suite:

```bash
python manage.py test
```

Expected output:
```text
Ran 9 tests in 0.315s

OK
```
