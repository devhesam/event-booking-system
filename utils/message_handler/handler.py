from utils.message_handler import messages


def get_message(message_code, is_dict=True, **kwargs):
    message = messages.MESSAGE_CODES.get(message_code)

    if not message:
        message_code = messages.ERROR_UNKNOWN
        message = messages.MESSAGE_CODES.get(message_code)

    if kwargs:
        message = message.format(**kwargs)

    return dict(detail=message, code=message_code) if is_dict else message
