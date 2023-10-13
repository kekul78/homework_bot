class ParseStatusError(Exception):
    """неизвестный статус домашней работы."""

    pass


class ApiAnswerError(Exception):
    """оштибка доступа к эндпоинту."""

    pass


class BotMessageError(Exception):
    """ошибка отправки сообщения."""

    pass


class BotMainError(Exception):
    """ошибка работы бота."""

    pass
