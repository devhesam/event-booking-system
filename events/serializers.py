from rest_framework import serializers

from events.models import Booking, BookingStatus, Event


class EventCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = [
            "id",
            "title",
            "description",
            "capacity",
            "event_date",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
        ]

    def validate_capacity(self, value):
        if value <= 0:
            raise serializers.ValidationError("Capacity must be a positive number.")
        return value


class EventDetailSerializer(serializers.ModelSerializer):
    active_bookings_count = serializers.SerializerMethodField()
    confirmed_bookings_count = serializers.SerializerMethodField()
    remaining_capacity = serializers.SerializerMethodField()

    class Meta:
        model = Event
        fields = [
            "id",
            "title",
            "description",
            "capacity",
            "event_date",
            "active_bookings_count",
            "confirmed_bookings_count",
            "remaining_capacity",
            "created_at",
            "updated_at",
        ]

    def get_active_bookings_count(self, obj):
        return obj.bookings.filter(
            status__in=[
                BookingStatus.PENDING,
                BookingStatus.CONFIRMED,
            ]
        ).count()

    def get_confirmed_bookings_count(self, obj):
        return obj.bookings.filter(
            status=BookingStatus.CONFIRMED,
        ).count()

    def get_remaining_capacity(self, obj):
        active_bookings_count = self.get_active_bookings_count(obj)
        return max(obj.capacity - active_bookings_count, 0)


class BookingSerializer(serializers.ModelSerializer):
    event_title = serializers.CharField(source="event.title", read_only=True)

    class Meta:
        model = Booking
        fields = [
            "id",
            "event",
            "event_title",
            "status",
            "expires_at",
            "confirmed_at",
            "cancelled_at",
            "expired_at",
            "created_at",
            "updated_at",
        ]
