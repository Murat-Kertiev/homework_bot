class MessageError(Exception):
    """Вызывается если сообщение в телеграмм не может быть отправленно."""

    pass


class TokenError(Exception):
    """Вызывается при отсутсвии токенов в переменных окружения."""

    pass


class ConectionError(Exception):
    """Вызывается если API не отвечает."""

    pass


class HomeworkError(Exception):
    """Вызывается при отсутвии в ответе API информации о домашке."""

    pass


class StatusError(Exception):
    """Вызывается при отсутствии статуса домашней работы."""

    pass
