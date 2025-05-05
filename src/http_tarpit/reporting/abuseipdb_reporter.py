import logging
import asyncio
from aiohttp import ClientSession, ClientError, ClientResponseError

from .. import config

log = logging.getLogger(__name__)

ABUSEIPDB_API_URL = 'https://api.abuseipdb.com/api/v2/report'

REPORTED_IPS_CACHE = set()
CACHE_MAX_SIZE = 10000

async def report_ip_to_abuseipdb(ip_address: str, comment_details: str):
    """Асинхронная отправка репорта в AbuseIPDB"""
    if not config.ABUSEIPDB_ENABLED:
        log.debug("AbuseIPDB reporting is disabled in config.")
        return
    if not config.ABUSEIPDB_API_KEY:
        log.error("AbusIPDB reporting is enablud, but API is missing!")
        return
    
    if ip_address in REPORTED_IPS_CACHE:
        log.debug(f"IP {ip_address} already reported recently. Skipping.")
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
    
    log.info(f"Attempting to report IP {ip_address} to AbuseIPDB. Categories: {params['categories']}")
    
    try:
        async with ClientSession(headers=headers) as session:
            async with session.post(ABUSEIPDB_API_URL, data=params) as response:
                response_json = await response.json()
                
                response.raise_for_status()
                response_json = await response.json()

                abuse_data = response_json.get('data', {})
                score = abuse_data.get('abuseConfidenceScore') 

                if score is not None:
                    log.info(f"Successfully reported IP {ip_address} to AbuseIPDB. New confidence score: {score}")
                    if len(REPORTED_IPS_CACHE) >= CACHE_MAX_SIZE:
                        REPORTED_IPS_CACHE.clear()
                        log.warning("Reported IP cache reached max size and was cleared.")
                    REPORTED_IPS_CACHE.add(ip_address)
                else: 
                    log.warning(f"Reported IP {ip_address}, but response format was unexpected or score missing: {response_json}")
    except ClientResponseError as e:
        response_body = getattr(e, 'response_body', None) 
        if not response_body and hasattr(e, 'history') and e.history:
            try:
                response_body = await e.history[-1].text()
            except Exception:
                response_body = "(Failed to retrieve error response body)"
        log.error(
            f"Failed to report IP {ip_address}: HTTP Error {e.status} - {e.message}. "
            f"URL: {e.request_info.real_url}. " 
            f"Response hint: {response_body or '(No body details)'}" 
        )
    except ClientError as e:
        log.error(f"Failed to report IP {ip_address}: Client/Network Error - {e}")
    except Exception as e:
        log.exception(f"An unexpected error occurred while reporting IP {ip_address}")