from django.contrib import admin, messages
from django.contrib.admin.models import LogEntry
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from events.models import Booking, BookingStatus, Event
from events.tasks import expire_pending_bookings


@admin.register(LogEntry)
class LogEntryAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'action_flag', 'change_message', 'object_id', 'content_type', 'action_time']
    search_fields = ['user__username', 'user__email', 'user__id']
    list_filter = ['action_flag', 'action_time', 'content_type']
    ordering = ['-id']

    def has_delete_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


class BookingInlineAdmin(admin.TabularInline):
    model = Booking
    raw_id_fields = ['user']
    readonly_fields = [
        'status',
        'expires_at',
        'confirmed_at',
        'cancelled_at',
        'expired_at',
        'created_at',
        'updated_at',
    ]
    extra = 0
    show_change_link = True

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'title',
        'capacity',
        'active_bookings_count',
        'confirmed_bookings_count',
        'remaining_capacity',
        'event_date',
        'created_at',
        'updated_at',
    ]
    search_fields = ['id', 'title', 'description']
    list_filter = ['event_date', 'created_at', 'updated_at']
    readonly_fields = [
        'active_bookings_count',
        'confirmed_bookings_count',
        'remaining_capacity',
        'created_at',
        'updated_at',
    ]
    date_hierarchy = 'event_date'
    ordering = ['-event_date']
    inlines = [BookingInlineAdmin]

    def active_bookings_count(self, obj):
        return obj.active_bookings_count

    active_bookings_count.short_description = _('Active bookings')

    def confirmed_bookings_count(self, obj):
        return obj.confirmed_bookings_count

    confirmed_bookings_count.short_description = _('Confirmed bookings')

    def remaining_capacity(self, obj):
        return obj.remaining_capacity

    remaining_capacity.short_description = _('Remaining capacity')


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'user',
        'event',
        'status',
        'expires_at',
        'confirmed_at',
        'cancelled_at',
        'expired_at',
        'created_at',
        'updated_at',
    ]
    search_fields = [
        'id',
        'user__id',
        'user__username',
        'user__email',
        'event__id',
        'event__title',
    ]
    list_filter = [
        'status',
        'event',
        'expires_at',
        'confirmed_at',
        'cancelled_at',
        'expired_at',
        'created_at',
        'updated_at',
    ]
    raw_id_fields = ['user', 'event']
    readonly_fields = [
        'created_at',
        'updated_at',
    ]
    date_hierarchy = 'created_at'
    ordering = ['-id']
    list_editable = ['status']
    actions = [
        'expire_selected_pending_bookings',
        'run_expire_pending_bookings_task',
    ]

    @admin.action(description=_('Expire selected pending bookings'))
    def expire_selected_pending_bookings(self, request, queryset):
        now = timezone.now()

        expired_count = queryset.filter(
            status=BookingStatus.PENDING,
            expires_at__lte=now,
        ).update(
            status=BookingStatus.EXPIRED,
            expired_at=now,
            updated_at=now,
        )

        self.message_user(
            request,
            _('%(count)s pending booking(s) expired successfully.') % {
                'count': expired_count,
            },
            level=messages.SUCCESS,
        )

    @admin.action(description=_('Run expire pending bookings celery task'))
    def run_expire_pending_bookings_task(self, request, queryset):
        expire_pending_bookings.delay()

        self.message_user(
            request,
            _('Expire pending bookings task has been queued successfully.'),
            level=messages.SUCCESS,
        )