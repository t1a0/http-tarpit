import asyncio
import logging
import sys

# Импортируем функцию запуска сервера из нашего пакета
# Poetry поймет, где искать src/http_tarpit
from http_tarpit.tarpit import start_server

def setup_logging():
    """Настраивает базовое логирование в консоль."""
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    # Используем StreamHandler для вывода в stderr/stdout
    logging.basicConfig(level=logging.INFO, format=log_format, stream=sys.stdout)
    # Можно сделать логгирование более подробным для нашего модуля
    logging.getLogger("http_tarpit.tarpit").setLevel(logging.DEBUG) # Показываем debug-сообщения от нашего тарпита

if __name__ == "__main__":
    setup_logging()
    log = logging.getLogger(__name__) # Логгер для main.py

    try:
        # Запускаем асинхронный сервер
        asyncio.run(start_server())
    except KeyboardInterrupt:
        log.info("Server stopped by user (KeyboardInterrupt).")
    except Exception as e:
        log.exception(f"An unexpected critical error occurred in main: {e}")
        sys.exit(1)