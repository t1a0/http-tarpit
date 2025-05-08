import logging
import asyncio
from aiohttp import ClientSession, ClientError, ClientResponseError

from .. import config

log = logging.getLogger(__name__)

ABUSEIPDB_API_URL = 'https://api.abuseipdb.com/api/v2/report'


async def report_ip_to_abuseipdb(ip_address: str,  target_port: int, comment_details: str):
    """Асинхронная отправка репорта в AbuseIPDB"""
    if not config.ABUSEIPDB_ENABLED:
        log.debug("AbuseIPDB reporting is disabled in config.")
        return
    if not config.ABUSEIPDB_API_KEY:
        log.error("AbusIPDB reporting is enablud, but API is missing!")
        return
    
    headers = {
        'Accept': 'application/json',
        'Key': config.ABUSEIPDB_API_KEY
    }
    
    params = {
        'ip': ip_address,
        'categories': config.ABUSEIPDB_CATEGORIES,
        'comment': f"{config.ABUSEIPDB_COMMENT_PREFIX}{comment_details}"
    }
    
    log.info(f"Attempting to report IP {ip_address} (from target port {target_port}) to AbuseIPDB. Categories: {params['categories']}")    
    
    try:
        async with ClientSession(headers=headers) as session:
            async with session.post(ABUSEIPDB_API_URL, data=params) as response:
                response_json = await response.json()
                
                response.raise_for_status()
                response_json = await response.json()

                abuse_data = response_json.get('data', {})
                score = abuse_data.get('abuseConfidenceScore') 

                if score is not None:
                    log.info(f"Successfully reported IP {ip_address} (from target port {target_port}) to AbuseIPDB. New confidence score: {score}")
                else: 
                    log.warning(f"Reported IP {ip_address} (from target port {target_port}), but response format was unexpected or score missing: {response_json}")    
        
    except ClientResponseError as e:
        response_body = None
        try:
            if hasattr(e, 'history') and e.history:
                 last_response = e.history[-1][1] 
                 if last_response: response_body = await last_response.text()
        except Exception as read_err:
            log.debug(f"Could not read response body from error history: {read_err}")
            response_body = "(Failed to retrieve error response body)"
        log.error(
            f"Failed to report IP {ip_address} (from target port {target_port}): HTTP Error {e.status} - {e.message}. "
            f"URL: {e.request_info.real_url}. "
            f"Response hint: {response_body or '(No body details)'}"
        )
    except ClientError as e:
        log.error(f"Failed to report IP {ip_address} (from target port {target_port}): Client/Network Error - {e}")
    except Exception as e:
        log.exception(f"An unexpected error occurred while reporting IP {ip_address} (from target port {target_port})")