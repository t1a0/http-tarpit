import asyncio
import logging
import time
import datetime
from aiohttp import web
from aiohttp.client_exceptions import ClientConnectionResetError 

from . import config

from .reporting.abuseipdb_reporter import report_ip_to_abuseipdb

from .utils.geoip_lookup import get_geoip_data

from .database import log_event_to_db, check_ip_reported_recently

log = logging.getLogger(__name__) 

def _clean_headers(headers):
    return {k: v for k, v in headers.items()}

async def _handle_abuseipdb_report(ip_addr: str, target_port: int, event_log_data: dict):
    if config.ABUSEIPDB_ENABLED and \
       ip_addr != "127.0.0.1" and \
       not ip_addr.startswith("192.168.") and \
       not ip_addr.startswith("10."):
        if not await asyncio.to_thread(check_ip_reported_recently, ip_addr): 
            report_comment = f"TargetPort:{target_port},Path: {event_log_data['http_path']}, Method: {event_log_data['http_method']}, UA: {event_log_data['user_agent'][:100]}"
            log.debug(f"Scheduling AbuseIPDB report task for {ip_addr}")
            asyncio.create_task(report_ip_to_abuseipdb(ip_addr, report_comment))
            event_log_data['reported_to_abuseipdb'] = 1
            event_log_data['abuseipdb_report_timestamp'] = datetime.datetime.now(datetime.timezone.utc).isoformat()

        else:
            log.debug(f"IP {ip_addr} was reported recently, skipping new report.")
    else:
        log.debug(f"AbuseIPDB report for {ip_addr} skipped.")
        event_log_data['reported_to_abuseipdb'] = 0
        event_log_data['abuseipdb_report_timestamp'] = None
        
async def handle_request(request):
    start_time = time.monotonic()
    request_timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat() 
    peername = request.transport.get_extra_info('peername')
    proxy_ip = "Unknown_Proxy"
    proxy_port = 0
    if peername:
        proxy_ip = peername[0]
        proxy_port = peername[1]
    
    real_ip_from_xfwd = request.headers.get('X-Forwarded-For', '').split(',')[0].strip()
    real_ip_from_xreal = request.headers.get('X-Real-IP', '').strip()
    
    actual_client_ip = real_ip_from_xfwd or real_ip_from_xreal or proxy_ip
    
    log.debug(f"Proxy IP: {proxy_ip}:{proxy_port}, Client IP: {actual_client_ip}")    
    ip_addr = actual_client_ip
    target_port_str = request.headers.get('X-Tarpit-Target-Port', '0') 
    target_port = 0
    
    try:
        target_port = int(target_port_str)
    except ValueError:
        log.warning(f"Could not parse X-Tarpit-Target-Port header: {target_port_str}")
        
    event_log_data = {
        'timestamp': request_timestamp,
        'client_ip': ip_addr,
        'client_port': proxy_port,
        'target_port': target_port,
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

    if ip_addr != "Unknown Proxy" and not ip_addr.startswith("127."):
        geoip_info = await asyncio.to_thread(get_geoip_data, ip_addr) 
        if geoip_info:
            event_log_data['geoip_data'] = geoip_info
            log.debug(f"GeoIP data for {ip_addr}: {geoip_info}")
        else:
            log.debug(f"No GeoIP data found for {ip_addr}")

    log.info(f"Connection received on target port {target_port} (logging to JSON)", extra={'extra_data': event_log_data})
    
    await _handle_abuseipdb_report(ip_addr, target_port, event_log_data)


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
                log.warning(error_msg, extra={'extra_data': {'client_ip': ip_addr}})
                break 
            except Exception as e_write:
                error_msg = f"Error writing to {ip_addr}:{port}: {e_write}"
                event_log_data['error_message'] = error_msg
                log.error(error_msg, exc_info=True, extra={'extra_data': {'client_ip': ip_addr}})
                break 
        if error_msg is None or error_msg == "Connection reset by peer during write":
            try:
                await response.write_eof()
            except ClientConnectionResetError:
                log.info(f"Client {ip_addr} closed connection before write_eof.")
                if not error_msg: 
                    error_msg = "Client closed connection prematurely before eof"
                    event_log_data['error_message'] = error_msg
            except Exception as e_eof:
                log.error(f"Error during write_eof for {ip_addr}: {e_eof}", exc_info=True)
                if not error_msg:
                    error_msg = f"Error during write_eof: {e_eof}"
                    event_log_data['error_message'] = error_msg

        return response

    except Exception as e_prepare:
         error_msg = f"Error during request preparation: {e_prepare}"
         event_log_data['response_status'] = 500
         event_log_data['error_message'] = error_msg
         log.error(f"Error during request preparation for {ip_addr}: {e_prepare}", exc_info=True, extra={'extra_data': event_log_data})
         end_time = time.monotonic()
         duration = end_time - start_time
         event_log_data['duration_s'] = round(duration, 3)
         try:
             await asyncio.to_thread(log_event_to_db, event_log_data.copy())
         except Exception as db_err:
             log.exception(f"Failed to log event to database after prepare error for IP {ip_addr}: {db_err}")
         return web.Response(status=500, text="Internal Server Error")

    finally:
        end_time = time.monotonic()
        duration = end_time - start_time
        event_log_data['duration_s'] = round(duration, 3)
        event_log_data['bytes_sent'] = bytes_sent_total 
        if event_log_data['response_status'] is None:
             event_log_data['response_status'] = 500 
        final_log_level = logging.WARNING if error_msg else logging.INFO
        log.log(final_log_level, f"Connection finished for {ip_addr}:{proxy_port} on target port {target_port} (JSON log)", extra={'extra_data': event_log_data})

        try:
            await asyncio.to_thread(log_event_to_db, event_log_data.copy())
        except Exception as db_err:
            log.exception(f"Failed to log event to database for IP {ip_addr}: {db_err}")