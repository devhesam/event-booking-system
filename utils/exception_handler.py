from rest_framework import status
from rest_framework.views import exception_handler

from utils.message_handler import messages
from utils.message_handler.handler import get_message


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        if response.status_code == status.HTTP_400_BAD_REQUEST and isinstance(response.data, dict):
            detail = response.data.get('detail', False)

            if not detail:
                errors = response.data

                response.data = get_message(messages.ERROR_VALIDATION)
                response.data['errors'] = errors

                return response

        if isinstance(response.data, dict):
            detail = response.data.get('detail', False)
            code = response.data.get('code', False)

            if detail and code:
                try:
                    response.data['code'] = int(code)
                except (TypeError, ValueError):
                    response.data['code'] = response.status_code

            elif detail and not code:
                response.data['code'] = response.status_code

    return response