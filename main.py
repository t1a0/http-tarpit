import asyncio
import logging
import sys
import os

# 1. Настройка логирования - ДО всего остального импорта из нашего пакета
try:
    from src.http_tarpit.logger_setup import setup_logging
    setup_logging()
except ImportError as e:
    print(f"Critical Error: Failed to import or run logger setup: {e}", file=sys.stderr)
    print("Please ensure 'src/http_tarpit/logger_setup.py' exists and is correct.", file=sys.stderr)
    sys.exit(1)
except Exception as e_log:
    print(f"Critical Error during logging setup: {e_log}", file=sys.stderr)
    sys.exit(1)


# Получаем логгер для этого файла уже ПОСЛЕ настройки
log = logging.getLogger(__name__)

# 2. Теперь импортируем остальные части приложения
try:
    from src.http_tarpit import config # Импортируем для доступа к конфигу, если нужно
    from src.http_tarpit.tarpit_server import run_server
except ImportError as e:
    log.exception(f"Failed to import application modules: {e}")
    sys.exit(1)


# 3. Основной блок запуска
if __name__ == "__main__":
    log.info("Application starting...")
    log.info(f"Configuration: HOST={config.HOST}, PORT={config.PORT}, LOG_FILE={config.LOG_FILE}")

    try:
        # Запускаем асинхронный сервер
        asyncio.run(run_server())
    except KeyboardInterrupt:
        log.info("Server stopped by user (KeyboardInterrupt).")
    except Exception as e:
        # Логируем любые другие критические ошибки во время работы run_server
        log.exception(f"A critical error occurred: {e}")
        sys.exit(1) # Выходим с кодом ошибки
    finally:
        log.info("Application shutting down.")