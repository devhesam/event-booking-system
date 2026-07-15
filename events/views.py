from constance import config
from rest_framework import exceptions, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from events.models import Event
from events.serializers import (BookingSerializer, EventCreateSerializer, EventDetailSerializer)
from events.services import BookingService
from events.tasks import cancel_booking_task, confirm_booking_task
from utils.message_handler import messages
from utils.message_handler.handler import get_message


class EventCreateAPIView(APIView):
    # permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = EventCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

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
        if config.CONFIRM_BOOKING_ASYNC:
            booking = BookingService.prepare_confirm_booking_async(
                user=request.user,
                booking_id=booking_id,
            )

            confirm_booking_task.delay(
                user_id=request.user.id,
                booking_id=booking.id,
            )

            serializer = BookingSerializer(booking)

            response = get_message(messages.SUCCESS_BOOKING_CONFIRM_QUEUED)
            response["data"] = serializer.data

            return Response(
                response,
                status=status.HTTP_202_ACCEPTED,
            )

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
        if config.CANCEL_BOOKING_ASYNC:
            booking = BookingService.prepare_cancel_booking_async(
                user=request.user,
                booking_id=booking_id,
            )

            cancel_booking_task.delay(
                user_id=request.user.id,
                booking_id=booking.id,
            )

            serializer = BookingSerializer(booking)

            response = get_message(messages.SUCCESS_BOOKING_CANCEL_QUEUED)
            response["data"] = serializer.data

            return Response(
                response,
                status=status.HTTP_202_ACCEPTED,
            )

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
