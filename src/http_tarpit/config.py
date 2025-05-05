import logging
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent

load_dotenv(dotenv_path=BASE_DIR/'.env')

HOST = "127.0.0.1" # Слушаем только локально при разработке/проксировании
PORT = 8080        # Непривилегированный порт
LOG_DIR = BASE_DIR / "logs" # Папка для логов
LOG_FILE = LOG_DIR / "tarpit.log" # Имя файла лога
LOG_LEVEL = logging.DEBUG # Уровень логирования в файл 
CONSOLE_LOG_LEVEL = logging.INFO # Уровень для вывода в консоль

# tarpit config
RESPONSE_DELAY_SECONDS = 1.5
RESPONSE_CHUNK = b'.'
MAX_RESPONSE_BYTES = 50

ABUSEIPDB_API_KEY = os.getenv("ABUSEIPDB_API_KEY",None)
ABUSEIPDB_ENABLED = bool(ABUSEIPDB_API_KEY)
ABUSEIPDB_CONFIDENCE_SCORE = 90
ABUSEIPDB_COMMENT_PREFIX = "HTTP Tarpit detected bot activity:"
ABUSEIPDB_CATEGORIES = "14,21" # 14 = Port Scan, 21 = Web App Atack (?18 = Brute?)


LOG_DIR.mkdir(parents=True, exist_ok=True)