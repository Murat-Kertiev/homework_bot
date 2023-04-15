import logging
import os
import sys
import time

import requests
import telegram
from dotenv import load_dotenv

import exeptions as ex

load_dotenv()

logging.basicConfig(
    level=logging.DEBUG,
    filename='main.log',
    filemode='a',
    format='%(asctime)s, %(levelname)s, %(message)s, %(name)s',
    encoding='UTF-8'
)

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


def check_tokens():
    """Проверяет наличие необходимых переменных окружения."""
    try:
        if not PRACTICUM_TOKEN:
            logging.critical(f'Отсуствует токен {PRACTICUM_TOKEN}')
            raise ex.TokenError(
                f'Отсутствует переменная окружения {PRACTICUM_TOKEN}'
            )
        if not TELEGRAM_TOKEN:
            logging.critical(f'Отсуствует токен {TELEGRAM_TOKEN}')
            raise ex.TokenError(
                f'Отсутствует переменная окружения {TELEGRAM_TOKEN}'
            )
        if not TELEGRAM_CHAT_ID:
            logging.critical(f'Отсуствует токен {TELEGRAM_CHAT_ID}')
            raise ex.TokenError(
                f'Отсутствует переменная окружения {TELEGRAM_CHAT_ID}'
            )
    except ex.TokenError:
        sys.exit()


def send_message(bot, message):
    """Отправляет сообщение в чат телеграмма."""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logging.debug('Сообщение успешно отправленно')
    except telegram.error.TelegramError as error:
        logging.error(f'Ошибка при отправке сообщения {error}')


def get_api_answer(timestamp):
    """Делает запрос к API."""
    try:
        payload = {'from_date': timestamp}
        homework_statuses = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params=payload
        )
        if homework_statuses.status_code != 200:
            raise ex.ConectionError('API не отвечает')
        return homework_statuses.json()
    except requests.RequestException as error:
        logging.error('Api не отвечает')
        raise error('Сбой в системе')


def check_response(response):
    """Проверяет ответ API на соответствие документации."""
    if not isinstance(response, dict):
        raise TypeError('Ошибка: ответ API должен быть словарем')

    if 'homeworks' not in response:
        raise KeyError('Ошибка: в ответе API отсутствует поле homeworks')

    if 'current_date' not in response:
        raise KeyError('Ошибка: в ответе API отстутствует поле current_date')

    if not isinstance(response['homeworks'], list):
        raise TypeError('Ошибка: значение homeworks не является списком')


def parse_status(homework):
    """
    Извлекает из информации о конкретной домашней работе статус этой работы.
    """
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')

    if not homework_name:
        logging.warning('Отсутствует имя домашней работы')
        raise TypeError('В ответе API отсутствует имя домашней работы')

    if not homework_status:
        logging.error('Отсутствует стату домашней работы')
        raise KeyError

    if homework_status not in HOMEWORK_VERDICTS:
        message = 'Нет статуса домашней работы'
        logging.error(message)
        raise ex.StatusError(message)
    verdict = HOMEWORK_VERDICTS.get(homework_status)
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    check_tokens()

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    while True:
        try:
            response = get_api_answer(timestamp)
            check_response(response)
            if response['homeworks']:
                message = parse_status(response['homeworks'][0])
                send_message(bot, message)
            else:
                raise ex.HomeworkError('Список домашек пуст')
            timestamp = response['current_date']
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
            send_message(bot, message)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
