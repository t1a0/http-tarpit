import asyncio
import logging
import time
from aiohttp import web

from . import config

from .reporting.abuseipdb_reporter import report_ip_to_abuseipdb

from .utils.geoip_lookup import get_geoip_data

log = logging.getLogger(__name__) 

def _clean_headers(headers):
    """Преобразует MultiDict в обычный dict для JSON лога"""
    return {k: v for k, v in headers.items()}

async def handle_request(request):
    """Обработчик входящих HTTP запросов. Отвечает медленно и логирует детали."""
    start_time = time.monotonic()
    peername = request.transport.get_extra_info('peername')
    ip_addr = "Unknown"
    port = 0
    if peername:
        ip_addr = peername[0]
        port = peername[1]

    log_extra = {
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
    }

    if ip_addr != "Unknown":
        geoip_info = get_geoip_data(ip_addr)
        if geoip_info:
            log_extra['geoip_data'] = geoip_info
            log.debug(f"GeoIP data for {ip_addr}: {geoip_info}")
        else:
            log.debug(f"No GeoIP data found for {ip_addr}")
    
    log.info(f"Connection received", extra={'extra_data': log_extra})

    if config.ABUSEIPDB_ENABLED: 
        report_comment = f"Path: {request.path}, Method: {request.method}, UA: {log_extra['user_agent'][:100]}" 
        asyncio.create_task(report_ip_to_abuseipdb(ip_addr, report_comment))
        log.debug(f"Scheduled AbuseIPDB report task for {ip_addr}")

    response_status = 200
    bytes_sent_total = 0
    error_msg = None

    try:
        response = web.StreamResponse(
            status=response_status,
            reason='OK',
            headers={'Content-Type': 'text/plain', 'Connection': 'keep-alive'}
        )
        log_extra['response_status'] = response_status
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
                log_extra['error_message'] = error_msg
                log.warning(error_msg, extra={'extra_data': {'client_ip': ip_addr}})
                break
            except Exception as e_write:
                error_msg = f"Error writing to {ip_addr}:{port}: {e_write}"
                log_extra['error_message'] = error_msg
                log.error(error_msg, exc_info=True, extra={'extra_data': {'client_ip': ip_addr}})
                break

        await response.write_eof()
        return response

    except Exception as e_prepare:
         error_msg = f"Error during request preparation: {e_prepare}"
         log_extra['response_status'] = 500 
         log_extra['error_message'] = error_msg
         log.error(error_msg, exc_info=True, extra={'extra_data': log_extra})
         return web.Response(status=500, text="Internal Server Error")

    finally:
        end_time = time.monotonic()
        duration = end_time - start_time
        log_extra['duration_s'] = round(duration, 3)
        log_extra['bytes_sent'] = bytes_sent_total
        log_level = logging.WARNING if error_msg else logging.INFO
        log.log(log_level, f"Connection finished for {ip_addr}:{port}", extra={'extra_data': log_extra})