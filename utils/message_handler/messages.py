from django.utils.translation import gettext_lazy as _

""" Success message codes: Range [2000 - 2999] """

SUCCESS_EVENT_CREATED = 2000
SUCCESS_EVENT_DETAIL_RETRIEVED = 2001
SUCCESS_BOOKING_CREATED = 2002
SUCCESS_BOOKING_ALREADY_EXISTS = 2003
SUCCESS_BOOKING_CONFIRMED = 2004
SUCCESS_BOOKING_CANCELLED = 2005
SUCCESS_BOOKING_EXPIRED = 2006
SUCCESS_BOOKING_CONFIRM_QUEUED = 2007
SUCCESS_BOOKING_CANCEL_QUEUED = 2008

SUCCESS_MESSAGE_CODES = {
    SUCCESS_EVENT_CREATED: _("Event created successfully."),
    SUCCESS_EVENT_DETAIL_RETRIEVED: _("Event detail retrieved successfully."),
    SUCCESS_BOOKING_CREATED: _("Booking created successfully."),
    SUCCESS_BOOKING_ALREADY_EXISTS: _("Active booking already exists for this event."),
    SUCCESS_BOOKING_CONFIRMED: _("Booking confirmed successfully."),
    SUCCESS_BOOKING_CANCELLED: _("Booking cancelled successfully."),
    SUCCESS_BOOKING_EXPIRED: _("Booking expired successfully."),
    SUCCESS_BOOKING_CONFIRM_QUEUED: _("Booking confirmation has been queued successfully."),
    SUCCESS_BOOKING_CANCEL_QUEUED: _("Booking cancellation has been queued successfully."),
}

""" Error message codes: Range [4000 - 4999] """

ERROR_UNKNOWN = 4000
ERROR_VALIDATION = 4001
ERROR_AUTHENTICATION_REQUIRED = 4002
ERROR_PERMISSION_DENIED = 4003

ERROR_EVENT_NOT_FOUND = 4100
ERROR_EVENT_SOLD_OUT = 4101
ERROR_INVALID_EVENT_CAPACITY = 4102

ERROR_BOOKING_NOT_FOUND = 4200
ERROR_DUPLICATE_ACTIVE_BOOKING = 4201
ERROR_INVALID_BOOKING_STATE = 4202
ERROR_BOOKING_EXPIRED = 4203

ERROR_MESSAGE_CODES = {
    ERROR_UNKNOWN: _("Unknown error."),
    ERROR_VALIDATION: _("Validation error."),
    ERROR_AUTHENTICATION_REQUIRED: _("Authentication credentials were not provided."),
    ERROR_PERMISSION_DENIED: _("You do not have permission to perform this action."),

    ERROR_EVENT_NOT_FOUND: _("Event not found."),
    ERROR_EVENT_SOLD_OUT: _("Event is sold out."),
    ERROR_INVALID_EVENT_CAPACITY: _("Event capacity must be a positive number."),

    ERROR_BOOKING_NOT_FOUND: _("Booking not found."),
    ERROR_DUPLICATE_ACTIVE_BOOKING: _("Active booking already exists for this event."),
    ERROR_INVALID_BOOKING_STATE: _("Invalid booking state."),
    ERROR_BOOKING_EXPIRED: _("Booking has expired."),
}

MESSAGE_CODES = {
    **SUCCESS_MESSAGE_CODES,
    **ERROR_MESSAGE_CODES,
}
