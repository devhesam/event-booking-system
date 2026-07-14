from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):
    # Call REST framework's default exception handler first,
    # to get the standard error response.
    response = exception_handler(exc, context)

    # Now add the HTTP status code to the response.
    if response is not None:
        if isinstance(response.data, dict):
            detail = response.data.get('detail', False)
            code = response.data.get('code', False)
            if detail and (code and code.isdigit()):
                response.data['code'] = int(code)
            elif detail and not code:
                response.data['code'] = response.status_code

    return response
