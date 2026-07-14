from rest_framework import exceptions, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from events.models import Event
from events.serializers import (BookingSerializer, EventCreateSerializer, EventDetailSerializer)
from events.services import BookingService
from utils.message_handler import messages
from utils.message_handler.handler import get_message


class EventCreateAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = EventCreateSerializer(data=request.data)

        if not serializer.is_valid():
            response = get_message(messages.ERROR_VALIDATION)
            response["errors"] = serializer.errors

            return Response(
                response,
                status=status.HTTP_400_BAD_REQUEST,
            )

        event = serializer.save()
        response_serializer = EventDetailSerializer(event)

        response = get_message(messages.SUCCESS_EVENT_CREATED)
        response["data"] = response_serializer.data

        return Response(
            response,
            status=status.HTTP_201_CREATED,
        )


class EventDetailAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, event_id):
        try:
            event = Event.objects.get(id=event_id)
        except Event.DoesNotExist:
            raise exceptions.NotFound(
                get_message(messages.ERROR_EVENT_NOT_FOUND)
            )

        serializer = EventDetailSerializer(event)

        response = get_message(messages.SUCCESS_EVENT_DETAIL_RETRIEVED)
        response["data"] = serializer.data

        return Response(
            response,
            status=status.HTTP_200_OK,
        )


class BookTicketAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, event_id):
        booking, created = BookingService.book_ticket(
            user=request.user,
            event_id=event_id,
        )

        serializer = BookingSerializer(booking)

        if created:
            response = get_message(messages.SUCCESS_BOOKING_CREATED)
            response["data"] = serializer.data

            return Response(
                response,
                status=status.HTTP_201_CREATED,
            )

        response = get_message(messages.SUCCESS_BOOKING_ALREADY_EXISTS)
        response["data"] = serializer.data

        return Response(
            response,
            status=status.HTTP_200_OK,
        )


class ConfirmBookingAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, booking_id):
        booking = BookingService.confirm_booking(
            user=request.user,
            booking_id=booking_id,
        )

        serializer = BookingSerializer(booking)

        response = get_message(messages.SUCCESS_BOOKING_CONFIRMED)
        response["data"] = serializer.data

        return Response(
            response,
            status=status.HTTP_200_OK,
        )


class CancelBookingAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, booking_id):
        booking = BookingService.cancel_booking(
            user=request.user,
            booking_id=booking_id,
        )

        serializer = BookingSerializer(booking)

        response = get_message(messages.SUCCESS_BOOKING_CANCELLED)
        response["data"] = serializer.data

        return Response(
            response,
            status=status.HTTP_200_OK,
        )
