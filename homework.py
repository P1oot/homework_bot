"""Бот проверяет изменение статуса домашней работы."""
import logging
import os
import sys
import requests
import time
import telegram
from dotenv import load_dotenv
from logging import StreamHandler
from http import HTTPStatus
import exceptions

load_dotenv()
PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

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


def send_message(bot, message):
    """Отправка сообщения в Telegram."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info(f'Успешная отправка сообщения: {message}')
    except Exception as error:
        logger.error(f'Сбой при отправке сообщения: {error}')


def get_api_answer(current_timestamp):
    """Запрос к API-сервису."""
    timestamp = current_timestamp
    params = {'from_date': timestamp}
    homework_statuses = requests.get(
        ENDPOINT,
        headers=HEADERS,
        params=params
    )
    if homework_statuses.status_code == HTTPStatus.INTERNAL_SERVER_ERROR:
        logger.error('Эндпоинт недоступен')
        raise exceptions.APIAnswerException('Эндпоинт недоступен')
    elif homework_statuses.status_code != HTTPStatus.OK:
        logger.error('Ошибка доступа к эндпоинту')
        raise exceptions.APIAnswerException('Ошибка доступа к эндпоинту')
    else:
        return homework_statuses.json()


def check_response(response):
    """Проверка корректности ответа API-сервиса."""
    try:
        homeworks = response['homeworks']
    except KeyError as error:
        logger.error(f'Отсутствие ожидаемого ключа: {error}')
        raise KeyError(f'Отсутствие ожидаемого ключа: {error}')
    if not isinstance(homeworks, list):
        logger.error('API передает ответ "homeworks" не в виде списка')
        raise exceptions.CheckResponseException(
            'API передает ответ "homeworks" не в виде списка'
        )
    return homeworks


def parse_status(homework):
    """Извлечение информации о домашней работе."""
    try:
        homework_name = homework['homework_name']
        homework_status = homework['status']
    except KeyError as error:
        logger.error(f'Отсутсвие ожидаемого ключа: {error}')
        raise KeyError(f'Отсутсвие ожидаемого ключа: {error}')
    try:
        verdict = HOMEWORK_STATUSES[homework_status]
    except KeyError as error:
        logger.error(f'Незадокументированный статус домашней работы: {error}')
        raise KeyError(
            f'Незадокументированный статус домашней работы: {error}'
        )
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверка доступности токенов."""
    tokens = [PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]
    for token in tokens:
        if token is None:
            logger.critical(f'Переменная окружения отсутствует: {token}')
            return False
    return True


def main():
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
            time.sleep(RETRY_TIME)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            if old_message != message:
                send_message(bot, message)
            old_message = message
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
