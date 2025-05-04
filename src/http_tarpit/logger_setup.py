import logging
import json
import datetime
import sys
import traceback # Для форматирования исключений

# Импортируем конфигурацию
from . import config # Используем относительный импорт внутри пакета

class JsonFormatter(logging.Formatter):
    """Кастомный форматер для вывода логов в JSON."""
    def format(self, record):
        log_record = {
            'timestamp': datetime.datetime.fromtimestamp(record.created, tz=datetime.timezone.utc).isoformat(),
            'level': record.levelname,
            'name': record.name, # Имя логгера (модуля)
            'message': record.getMessage(),
        }
        # Добавляем кастомные поля из extra, если они есть и это словарь
        if hasattr(record, 'extra_data') and isinstance(record.extra_data, dict):
            log_record.update(record.extra_data)

        # Добавляем информацию об исключении, если есть
        if record.exc_info:
            log_record['exception_info'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                # traceback.format_exc() дает полную трассировку стека в виде строки
                'traceback': traceback.format_exception(*record.exc_info)
            }
        elif record.exc_text:
             log_record['exception_text'] = record.exc_text

        try:
            # default=str пытаемся преобразовать несериализуемые объекты в строку
            return json.dumps(log_record, ensure_ascii=False, default=str)
        except TypeError as e:
            error_log = {
                'timestamp': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                'level': 'ERROR', 'name': 'JsonFormatter',
                'message': 'Failed to serialize log record to JSON',
                'original_message': record.getMessage(), 'serialization_error': str(e),
            }
            return json.dumps(error_log)

def setup_logging():
    """Настраивает JSON логирование в файл и базовое в консоль."""
    json_formatter = JsonFormatter()
    # Используем 'a' для режима добавления в файл
    file_handler = logging.FileHandler(config.LOG_FILE, mode='a', encoding='utf-8')
    file_handler.setFormatter(json_formatter)
    file_handler.setLevel(config.LOG_LEVEL) # Уровень для файла

    console_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(config.CONSOLE_LOG_LEVEL) # Уровень для консоли

    root_logger = logging.getLogger() # Получаем корневой логгер
    root_logger.setLevel(min(config.LOG_LEVEL, config.CONSOLE_LOG_LEVEL)) # Общий уровень - минимальный из хендлеров

    # Очищаем старые обработчики, если они были добавлены ранее (на всякий случай)
    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    # Подавляем слишком подробные логи от aiohttp
    logging.getLogger('aiohttp.access').setLevel(logging.WARNING)
    logging.getLogger('aiohttp.web').setLevel(logging.WARNING)
    logging.getLogger('aiohttp.server').setLevel(logging.INFO)

    log = logging.getLogger(__name__) # Логгер для этого модуля
    log.info(f"Logging setup complete. File: {config.LOG_FILE} (Level: {logging.getLevelName(config.LOG_LEVEL)}), Console Level: {logging.getLevelName(config.CONSOLE_LOG_LEVEL)}")