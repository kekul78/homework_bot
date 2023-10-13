import logging
import os
import telegram
import sys
import requests
import time

from dotenv import load_dotenv
from logging.handlers import RotatingFileHandler

from exceptions import (BotMessageError,
                        ApiAnswerError,
                        ParseStatusError,
                        BotMainError)

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logger = logging.getLogger('homework')
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
handler = RotatingFileHandler('my_logger.log',
                              maxBytes=50000000,
                              backupCount=5)
handler.setFormatter(formatter)
logger.addHandler(handler)


def check_tokens():
    """проверяет доступность переменных окружения."""
    for token in (PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID):
        if token is None:
            logger.critical(
                'Отсутствует обязательная переменная окружения: '
                f'"{token}"')
    return all((PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID))


def send_message(bot, message):
    """отправляет сообщение в Telegram чат."""
    try:
        logger.debug('Начало отправки сообщения')
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except Exception:
        logger.error(f'Отправка сообщения невозможна: {Exception}')
        raise BotMessageError(
            f'Отправка сообщения невозможна: {Exception}')
    else:
        logger.debug('Сообщение успешно отправлено')


def get_api_answer(timestamp):
    """делает запрос к единственному эндпоинту API-сервиса."""
    payload = {'from_date': timestamp}

    try:
        homework_statuses = requests.get(ENDPOINT,
                                         headers=HEADERS,
                                         params=payload)
        if homework_statuses.status_code != 200:
            logger.error(f'Недоступность эндпоинта {ENDPOINT}')
            raise ApiAnswerError(
                f'Некорректный статус код: {homework_statuses.status_code}'
            )
        return homework_statuses.json()
    except Exception as error:
        raise ApiAnswerError(f'Возникла ошибка: {error}'
                             f'С параметрами {ENDPOINT}, {HEADERS}, {payload}')


def check_response(response):
    """проверяет ответ API на соответствие документации."""
    if isinstance(response, list):
        response = response[0]
        raise TypeError('API структура данных пришла в формате списка')
    if not isinstance(response, dict):
        raise TypeError('API структура данных пришла не в формате словоря')
    homeworks = response.get('homeworks')
    if not isinstance(homeworks, list):
        raise TypeError('Домашки пришли не ввиде списка')
    return homeworks


def parse_status(homework):
    """извлекает из информации о конкретной домашней работе статус работы."""
    if not isinstance(homework, dict):
        raise ParseStatusError('Переменная "homework" не словарь')
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if homework_name is None:
        raise KeyError('Отсутствует ключ "homework_name"')
    if homework_status is None:
        logger.debug('Статус домашних работ не изменился.')

    if homework_status in HOMEWORK_VERDICTS:
        verdict = HOMEWORK_VERDICTS[homework_status]
        return f'Изменился статус проверки работы "{homework_name}". {verdict}'
    raise ParseStatusError(
        f'Неизвестный статус домашней работы {homework_status}.')


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        sys.exit(0)
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = 0
    crutch = 'Костыли это плохо, но с нимим веселее :)'
    while True:
        try:
            response = get_api_answer(timestamp)
            homework = check_response(response)
            print(homework[0])
            if crutch != homework:
                send_message(bot, parse_status(homework[0]))
                crutch = homework
            timestamp = response['current_date']
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
            logger.error(message)
            raise BotMainError(message)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
