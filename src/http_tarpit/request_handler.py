import asyncio
import logging
import time
import datetime
from aiohttp import web

from . import config

from .reporting.abuseipdb_reporter import report_ip_to_abuseipdb

from .utils.geoip_lookup import get_geoip_data

from .database import log_event_to_db, check_ip_reported_recently, mark_ip_as_reported

log = logging.getLogger(__name__) 

def _clean_headers(headers):
    """Преобразует MultiDict в обычный dict для JSON лога"""
    return {k: v for k, v in headers.items()}

async def _handle_abuseipdb_report(ip_addr: str, event_log_data: dict):
    if config.ABUSEIPDB_ENABLED and \
       ip_addr != "127.0.0.1" and \
       not ip_addr.startswith("192.168.") and \
       not ip_addr.startswith("10."):
        if not await asyncio.to_thread(check_ip_reported_recently, ip_addr): 
            report_comment = f"Path: {event_log_data['http_path']}, Method: {event_log_data['http_method']}, UA: {event_log_data['user_agent'][:100]}"
            log.debug(f"Scheduling AbuseIPDB report task for {ip_addr}")
            asyncio.create_task(report_ip_to_abuseipdb(ip_addr, report_comment))
            event_log_data['reported_to_abuseipdb'] = 0 
            event_log_data['abuseipdb_report_timestamp'] = None

        else:
            log.debug(f"IP {ip_addr} was reported recently, skipping new report.")
    else:
        
        event_log_data['reported_to_abuseipdb'] = 0
        event_log_data['abuseipdb_report_timestamp'] = None
        
async def handle_request(request):
    start_time = time.monotonic()
    request_timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat() 
    peername = request.transport.get_extra_info('peername')
    ip_addr = "Unknown"
    port = 0
    if peername:
        ip_addr = peername[0]
        port = peername[1]
        
    event_log_data = {
        'timestamp': request_timestamp,
        'client_ip': ip_addr,
        'client_port': port,
        'http_method': request.method,
        'http_path': request.path,
        'http_query': str(request.query_string),
        'http_version': f"{request.version.major}.{request.version.minor}",
        'user_agent': request.headers.get('User-Agent', 'N/A'),
        'headers': _clean_headers(request.headers),
        'request_body_preview': None,
        'response_status': None,
        'bytes_sent': 0,
        'duration_s': None,
        'error_message': None,
        'geoip_data': None,
        'reported_to_abuseipdb': 0, 
        'abuseipdb_report_timestamp': None
    }

    if ip_addr != "Unknown":
        geoip_info = await asyncio.to_thread(get_geoip_data, ip_addr) 
        if geoip_info:
            event_log_data['geoip_data'] = geoip_info
            log.debug(f"GeoIP data for {ip_addr}: {geoip_info}")
        else:
            log.debug(f"No GeoIP data found for {ip_addr}")

    log.info(f"Connection received (logging to JSON)", extra={'extra_data': event_log_data})
    
    await _handle_abuseipdb_report(ip_addr, event_log_data)


    response_status = 200
    bytes_sent_total = 0
    error_msg = None

    try:
        response = web.StreamResponse(
            status=response_status,
            reason='OK',
            headers={'Content-Type': 'text/plain', 'Connection': 'keep-alive'}
        )
        event_log_data['response_status'] = response_status
        await response.prepare(request)
        log.debug(f"Sent headers to {ip_addr}", extra={'extra_data': {'client_ip': ip_addr}})

        while bytes_sent_total < config.MAX_RESPONSE_BYTES:
            try:
                await response.write(config.RESPONSE_CHUNK)
                await response.drain()
                bytes_sent_total += len(config.RESPONSE_CHUNK)
                log.debug(f"Sent chunk (total: {bytes_sent_total})", extra={'extra_data': {'client_ip': ip_addr}})
                await asyncio.sleep(config.RESPONSE_DELAY_SECONDS)
            except ConnectionResetError:
                error_msg = "Connection reset by peer during write"
                event_log_data['error_message'] = error_msg
                break
            except Exception as e_write:
                error_msg = f"Error writing to {ip_addr}:{port}: {e_write}"
                event_log_data['error_message'] = error_msg
                log.error(f"Error writing to {ip_addr}:{port}: {e_write}", exc_info=True) 
                break

        await response.write_eof()
        return response

    except Exception as e_prepare:
         error_msg = f"Error during request preparation: {e_prepare}"
         event_log_data['response_status'] = 500
         event_log_data['error_message'] = error_msg
         log.error(f"Error during request preparation for {ip_addr}: {e_prepare}", exc_info=True)
         return web.Response(status=500, text="Internal Server Error")

    finally:
        end_time = time.monotonic()
        duration = end_time - start_time
        event_log_data['duration_s'] = round(duration, 3)
        event_log_data['bytes_sent'] = bytes_sent_total

        final_log_level = logging.WARNING if error_msg else logging.INFO
        log.log(final_log_level, f"Connection finished for {ip_addr}:{port} (JSON log)", extra={'extra_data': event_log_data})

        try:
            await asyncio.to_thread(log_event_to_db, event_log_data.copy()) 
        except Exception as db_err:
            log.exception(f"Failed to log event to database for IP {ip_addr}: {db_err}")