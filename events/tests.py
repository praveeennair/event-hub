from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from .models import Event, Reservation


class EventHubAPITests(APITestCase):
    def setUp(self):
        self.event1 = Event.objects.create(
            title="PyCon India 2025",
            venue="NIMHANS Convention Centre, Bangalore",
            date="2025-09-20",
            total_seats=500,
            available_seats=500,
            status="upcoming",
        )
        self.event2 = Event.objects.create(
            title="Django Day Delhi 2025",
            venue="India Habitat Centre, Delhi",
            date="2025-11-15",
            total_seats=200,
            available_seats=200,
            status="completed",
        )

    def test_create_event_success(self):
        payload = {
            "title": "Tech Summit 2025",
            "venue": "Whitefield, Bangalore",
            "date": "2025-10-10",
            "total_seats": 100,
            "available_seats": 100,
            "status": "upcoming",
        }
        response = self.client.post("/api/events/", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["title"], "Tech Summit 2025")
        self.assertEqual(response.data["reservations_count"], 0)

    def test_create_event_invalid_seats(self):
        payload = {
            "title": "Invalid Event",
            "venue": "Online",
            "date": "2025-10-10",
            "total_seats": 50,
            "available_seats": 100,
            "status": "upcoming",
        }
        response = self.client.post("/api/events/", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("non_field_errors", response.data)
        self.assertIn("available_seats cannot exceed total_seats.", response.data["non_field_errors"])

    def test_list_and_filter_events(self):
        # List all
        response = self.client.get("/api/events/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

        # Filter by status
        response = self.client.get("/api/events/?status=upcoming")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], self.event1.id)

        # Filter by venue (icontains)
        response = self.client.get("/api/events/?venue=bangalore")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], self.event1.id)

    def test_create_reservation_success(self):
        payload = {
            "event": self.event1.id,
            "attendee_name": "Priya Sharma",
            "attendee_email": "priya@example.com",
            "seats_reserved": 2,
        }
        response = self.client.post("/api/reservations/", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["attendee_name"], "Priya Sharma")
        self.assertEqual(response.data["status"], "confirmed")

        # Verify seats were deducted
        self.event1.refresh_from_db()
        self.assertEqual(self.event1.available_seats, 498)

        # Verify reservations_count in event
        event_res = self.client.get(f"/api/events/{self.event1.id}/")
        self.assertEqual(event_res.data["reservations_count"], 1)

    def test_reservation_overbooking_failure(self):
        # Only 2 seats available
        small_event = Event.objects.create(
            title="Exclusive Workshop",
            venue="Online",
            date="2025-08-01",
            total_seats=2,
            available_seats=2,
            status="upcoming",
        )
        payload = {
            "event": small_event.id,
            "attendee_name": "Overbooker",
            "attendee_email": "overbooker@example.com",
            "seats_reserved": 5,
        }
        response = self.client.post("/api/reservations/", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("non_field_errors", response.data)
        self.assertIn("Only 2 seat(s) available.", response.data["non_field_errors"])

        # Verify available seats remains unchanged
        small_event.refresh_from_db()
        self.assertEqual(small_event.available_seats, 2)

    def test_reservation_for_completed_event_fails(self):
        payload = {
            "event": self.event2.id,
            "attendee_name": "Late Attendee",
            "attendee_email": "late@example.com",
            "seats_reserved": 1,
        }
        response = self.client.post("/api/reservations/", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("non_field_errors", response.data)
        self.assertIn("Cannot reserve seats for a completed event.", response.data["non_field_errors"])

    def test_reservation_invalid_seat_count(self):
        payload = {
            "event": self.event1.id,
            "attendee_name": "Zero Seats",
            "attendee_email": "zero@example.com",
            "seats_reserved": 0,
        }
        response = self.client.post("/api/reservations/", payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("seats_reserved", response.data)

    def test_cancel_reservation_success_and_restores_seats(self):
        # Create reservation
        reservation = Reservation.objects.create(
            event=self.event1,
            attendee_name="Rahul Verma",
            attendee_email="rahul@example.com",
            seats_reserved=3,
            status="confirmed",
        )
        self.event1.available_seats -= 3
        self.event1.save()

        # Cancel reservation
        response = self.client.post(f"/api/reservations/{reservation.id}/cancel/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "cancelled")

        # Verify seats restored
        self.event1.refresh_from_db()
        self.assertEqual(self.event1.available_seats, 500)

        # Canceling already cancelled returns 400
        response_retry = self.client.post(f"/api/reservations/{reservation.id}/cancel/")
        self.assertEqual(response_retry.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response_retry.data["error"], "Already cancelled.")

    def test_filter_reservations_by_event_id(self):
        r1 = Reservation.objects.create(
            event=self.event1,
            attendee_name="User 1",
            attendee_email="u1@example.com",
            seats_reserved=1,
            status="confirmed",
        )
        r2 = Reservation.objects.create(
            event=self.event2,
            attendee_name="User 2",
            attendee_email="u2@example.com",
            seats_reserved=1,
            status="confirmed",
        )

        response = self.client.get(f"/api/reservations/?event_id={self.event1.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], r1.id)
