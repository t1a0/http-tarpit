import logging
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent

load_dotenv(dotenv_path=BASE_DIR/'.env')

HOST = "127.0.0.1"
PORT = 8080        
LOG_DIR = BASE_DIR / "logs" 
LOG_FILE = LOG_DIR / "tarpit.log" 
LOG_LEVEL = logging.INFO 
CONSOLE_LOG_LEVEL = logging.WARNING 

# bd config
DATABASE_DIR = BASE_DIR / "data"
SQLITE_DB_FILE = DATABASE_DIR / "tarpit_events.db"

# tarpit config
RESPONSE_DELAY_SECONDS = 1.5
RESPONSE_CHUNK = b'.'
MAX_RESPONSE_BYTES = 1200

ABUSEIPDB_API_KEY = os.getenv("ABUSEIPDB_API_KEY",None)
ABUSEIPDB_ENABLED = bool(ABUSEIPDB_API_KEY)
ABUSEIPDB_CONFIDENCE_SCORE = 90
ABUSEIPDB_COMMENT_PREFIX = "HTTP Tarpit detected bot activity:"
ABUSEIPDB_CATEGORIES = "14,21,19" # 14 = Port Scan, 21 = Web App Atack, 19 = Bad Web Bot (?18 = Brute?)
ABUSEIPDB_REPORT_INTERVAL_MINUTES = 40

GEOLITE2_CITY_DB_PATH = BASE_DIR / "data" / "GeoLite2-City.mmdb"
GEOLITE2_ASN_DB_PATH = BASE_DIR / "data" / "GeoLite2-ASN.mmdb"

GEOIP_CITY_ENABLED = GEOLITE2_CITY_DB_PATH.exists()
GEOIP_ASN_ENABLED = GEOLITE2_ASN_DB_PATH.exists()

LOG_DIR.mkdir(parents=True, exist_ok=True)
DATABASE_DIR.mkdir(parents=True, exist_ok=True)