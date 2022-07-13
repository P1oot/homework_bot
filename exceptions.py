"""Кастомные исключения."""


class APIAnswerException(Exception):
    """Исключение связанное с работоспособностью API-сервиса."""

    pass


class CheckResponseException(Exception):
    """Исключение связанное с корректностью ответа API-сервиса."""

    pass
