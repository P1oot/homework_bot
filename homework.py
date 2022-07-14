"""Бот проверяет изменение статуса домашней работы."""
import sys
import requests
import time
import telegram
from http import HTTPStatus
import exceptions
# Костыль для прохождения тестов
from const import PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID
import const
# from sh_logger import make_logger
import logging
from logging import StreamHandler

logging.basicConfig(
    level=logging.DEBUG,
    filename='program.log',
    format='%(asctime)s, %(levelname)s, %(message)s, %(name)s'
)
logger = logging.getLogger(__name__)
handler = StreamHandler()
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
handler.setFormatter(formatter)
logger.addHandler(handler)

# logger = make_logger()
# Для прохождения тестов логорование должно создаваться в этом файле


def send_message(bot: telegram.Bot, message: str) -> None:
    """Отправка сообщения в Telegram."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info('Успешная отправка сообщения: %s', message)
    except Exception as error:
        logger.error('Сбой при отправке сообщения: %s', error)


def get_api_answer(current_timestamp: int) -> dict:
    """Запрос к API-сервису."""
    timestamp = current_timestamp
    params = {'from_date': timestamp}
    homework_response = requests.get(
        const.ENDPOINT,
        headers=const.HEADERS,
        params=params
    )
    if homework_response.status_code != HTTPStatus.OK:
        logger.error(
            'Ошибка доступа к эндпоинту: %s', homework_response.status_code
        )
        raise exceptions.APIAnswerException('Ошибка доступа к эндпоинту')
    else:
        logger.debug(
            f'Статус кода: {homework_response.status_code}\n'
            f'Ответ: {homework_response.json()}'
        )
        return homework_response.json()


def check_response(response: dict) -> list:
    """Проверка корректности ответа API-сервиса."""
    try:
        homeworks = response['homeworks']
    except KeyError as error:
        logger.error('Отсутствие ожидаемого ключа: %s', error)
        raise KeyError('Отсутствие ожидаемого ключа: %s', error)
    if not isinstance(homeworks, list):
        logger.error('API передает ответ "homeworks" не в виде списка')
        raise exceptions.CheckResponseException(
            'API передает ответ "homeworks" не в виде списка'
        )
    return homeworks


def parse_status(homework: list) -> str:
    """Извлечение информации о домашней работе."""
    try:
        homework_name = homework['homework_name']
        homework_status = homework['status']
    except KeyError as error:
        logger.error('Отсутсвие ожидаемого ключа: %s', error)
        raise KeyError('Отсутсвие ожидаемого ключа: %s', error)
    try:
        verdict = const.HOMEWORK_STATUSES[homework_status]
    except KeyError as error:
        logger.error('Незадокументированный статус домашней работы: %s', error)
        raise KeyError(
            'Незадокументированный статус домашней работы: %s', error
        )
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens() -> bool:
    """Проверка доступности токенов."""
    tokens = [
        PRACTICUM_TOKEN,
        TELEGRAM_TOKEN,
        TELEGRAM_CHAT_ID
    ]
    if not all(tokens):
        logger.critical('Одна из переменных окружения отсутствует')
        return False
    return True


def main() -> None:
    """Основная логика работы бота."""
    if check_tokens():
        logger.debug('Переменные окружения доступны')
    else:
        sys.exit('Программа принудительно остановленна')

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    old_message = ''

    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks = check_response(response)
            if homeworks:
                message = parse_status(homeworks[0])
                send_message(bot, message)
            else:
                logger.debug('Отсутствие в ответе новых статусов')
            current_timestamp = int(time.time())

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            if old_message != message:
                send_message(bot, message)
            old_message = message
        finally:
            time.sleep(const.RETRY_TIME)


if __name__ == '__main__':
    main()
