import logging
import os
import time
from http import HTTPStatus
from logging.handlers import RotatingFileHandler

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

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
handler = RotatingFileHandler(
    'my_logger.log',
    maxBytes=50000000,
    backupCount=5,
    encoding='UTF-8'
)
logger.addHandler(handler)
handler.setFormatter(formatter)

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

# Прокомментируй пожалуйста такой вариант. Минусы и плюсы
# def check_tokens():
#     """Проверяет наличие необходимых переменных окружения."""
#     tokens = [PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]
#     return all(tokens)


def check_tokens():
    """Проверяет наличие необходимых переменных окружения."""
    tokens = {
        'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
        'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
        'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID
    }
    for token in tokens.values():
        if token is None:
            return False
    return True


def send_message(bot, message):
    """Отправляет сообщение в чат телеграмма."""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logger.debug('Сообщение успешно отправленно')
    except telegram.error.TelegramError as error:
        logger.error(f'Ошибка при отправке сообщения {error}')


def get_api_answer(timestamp):
    """Делает запрос к API."""
    try:
        payload = {'from_date': timestamp}
        homework_statuses = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params=payload
        )
        if homework_statuses.status_code != HTTPStatus.OK:
            url = homework_statuses.url
            headers = homework_statuses.headers
            raise ex.ConectionError(
                f'API не отвечает. URL:{url}'
                f'HEADERS:{headers}'
            )
        return homework_statuses.json()
    except requests.RequestException as error:
        logger.error('Api не отвечает')
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
    """Извлекает из информации о конкретной.
    домашней работе статус этой работы.
    """
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')

    if not homework_name:
        logger.warning('Отсутствует имя домашней работы')
        raise TypeError('В ответе API отсутствует имя домашней работы')

    if not homework_status:
        logger.error('Отсутствует стату домашней работы')
        raise KeyError('D ответе API отсутствует статус домашней рабоыт')

    if homework_status not in HOMEWORK_VERDICTS:
        message = 'Нет статуса домашней работы'
        logger.error(message)
        raise ex.StatusError(message)

    verdict = HOMEWORK_VERDICTS.get(homework_status)
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logger.critical('Отсутствует переменная окружения')
        raise ex.TokenError('Отсутствует переменная окружения')

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    sent_message = set()

    while True:
        try:
            response = get_api_answer(timestamp)
            check_response(response)
            if response['homeworks']:
                message = parse_status(response['homeworks'][0])
                if message not in sent_message:
                    send_message(bot, message)
                    sent_message.add(message)
            else:
                message = 'Информация о домашке отсутствует'
                logger.debug(message)
            timestamp = response['current_date']
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            if message not in sent_message:
                send_message(bot, message)
                sent_message.add(message)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
