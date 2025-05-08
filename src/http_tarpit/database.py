import sqlite3
import logging
import json
import datetime
from pathlib import Path

from . import config

log = logging.getLogger(__name__)

DB_FILE = config.SQLITE_DB_FILE

def get_db_connection():
    try:
        conn = sqlite3.connect(str(DB_FILE))
        conn.row_factory= sqlite3.Row
        return conn
    except sqlite3.Error as e:
        log.exception(f"SQLite error connecting to database {DB_FILE}: {e}")
        return None

def init_db():
    conn = get_db_connection()
    if not conn:
        log.error("Cannot initialize database: connection failed.")
        return
    
    try:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                client_ip TEXT NOT NULL,
                client_port INTEGER,
                target_port INTEGER,
                http_method TEXT,
                http_path TEXT,
                http_query TEXT,
                user_agent TEXT,
                headers_json TEXT,
                response_status INTEGER,
                bytes_sent INTEGER,
                duration_s REAL,
                error_message TEXT,
                country_iso_code TEXT,
                country_name TEXT,
                city_name TEXT,
                latitude REAL,
                longitude REAL,
                asn_number INTEGER,
                asn_organization TEXT,
                reported_to_abuseipdb INTEGER DEFAULT 0, -- 0 = нет, 1 = да
                abuseipdb_report_timestamp TEXT
            )
        ''')
        try:
            cursor.execute('ALTER TABLE events ADD COLUMN target_port INTEGER')
            log.info("Added column 'target_port' to existing 'events' table.")
        except sqlite3.OperationalError as e:
            if 'duplicate column name' in str(e).lower():
                pass
            else:
                raise 
        conn.commit()
        log.info(f"Database {DB_FILE} Initialized successfully. Table 'events' created or already exists.")
    except sqlite3.Error as e:
        log.exception(f"Error initializing database table 'events': {e}")
    finally:
        if conn:
            conn.close()

def log_event_to_db(event_data: dict):
    conn = get_db_connection()
    if not conn:
        log.error("Cannot log event to DB: connection failed.")
        return
    geoip_data_dict = event_data.get('geoip_data')
    if geoip_data_dict is None: 
        geoip_data_dict = {}
    sql_data = {
        "timestamp": event_data.get('timestamp', datetime.datetime.now(datetime.timezone.utc).isoformat()),
        "client_ip": event_data.get('client_ip'),
        "client_port": event_data.get('client_port'),
        "target_port": event_data.get('target_port'),
        "http_method": event_data.get('http_method'),
        "http_path": event_data.get('http_path'),
        "http_query": event_data.get('http_query'),
        "user_agent": event_data.get('user_agent'),
        "headers_json": json.dumps(event_data.get('headers', {})),
        "response_status": event_data.get('response_status'),
        "bytes_sent": event_data.get('bytes_sent'),
        "duration_s": event_data.get('duration_s'),
        "error_message": event_data.get('error_message'),
        "country_iso_code": geoip_data_dict.get('country_iso_code'),
        "country_name": geoip_data_dict.get('country_name'),
        "city_name": geoip_data_dict.get('city_name'),
        "latitude": geoip_data_dict.get('latitude'),
        "longitude": geoip_data_dict.get('longitude'),
        "asn_number": geoip_data_dict.get('asn_number'),
        "asn_organization": geoip_data_dict.get('asn_organization'),
        "reported_to_abuseipdb": event_data.get('reported_to_abuseipdb', 0),
        "abuseipdb_report_timestamp": event_data.get('abuseipdb_report_timestamp')
    }

    columns = ', '.join(sql_data.keys())
    placeholders = ', '.join('?' * len(sql_data))
    sql = f'INSERT INTO events ({columns}) VALUES ({placeholders})'
    values = tuple(sql_data.values())

    try:
        cursor = conn.cursor()
        cursor.execute(sql, values)
        conn.commit()
        log.debug(f"Event logged to database for IP: {sql_data['client_ip']}")
    except sqlite3.Error as e:
        log.exception(f"Error logging event to database for IP {sql_data['client_ip']}: {e}")
    finally:
        if conn:
            conn.close()


def check_ip_reported_recently(ip_address: str, interval_hours: int = 1) -> bool:
    conn = get_db_connection()
    if not conn:
        return False 
    interval_minutes = config.ABUSEIPDB_REPORT_INTERVAL_MINUTES
    try:
        cursor = conn.cursor()
        threshold_time = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=interval_minutes)
        threshold_iso = threshold_time.isoformat()
        
        ccursor.execute('''
            SELECT 1 FROM events
            WHERE client_ip = ?
              AND reported_to_abuseipdb = 1
              AND abuseipdb_report_timestamp >= ?
            LIMIT 1
        ''', (ip_address, threshold_iso))
        result = cursor.fetchone()
        rwas_reported = bool(result)
        if was_reported:
            log.debug(f"Checked DB: IP {ip_address} found with recent report timestamp >= {threshold_iso}.")
        else:
            log.debug(f"Checked DB: IP {ip_address} not found with recent report timestamp.")
        return was_reported
    except sqlite3.Error as e:
        log.exception(f"Error checking if IP {ip_address} was reported: {e}")
        return False # При ошибке лучше разрешить репорт, чем блокировать его навсегда
    finally:
        if conn:
            conn.close()