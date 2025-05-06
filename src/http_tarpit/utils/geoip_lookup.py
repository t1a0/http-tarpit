import logging
import geoip2.database
from geoip2.errors import AddressNotFoundError

from .. import config 

log = logging.getLogger(__name__)

_city_reader = None
_asn_reader = None

def _initialize_geoip_readers():
    global _city_reader, _asn_reader

    if config.GEOIP_CITY_ENABLED:
        try:
            _city_reader = geoip2.database.Reader(str(config.GEOLITE2_CITY_DB_PATH))
            log.info(f"GeoLite2 City DB loaded from: {config.GEOLITE2_CITY_DB_PATH}")
        except FileNotFoundError:
            log.error(f"GeoLite2 City DB file not found at: {config.GEOLITE2_CITY_DB_PATH}")
            _city_reader = None
        except Exception as e:
            log.error(f"Failed to load GeoLite2 City DB from {config.GEOLITE2_CITY_DB_PATH}: {e}")
            _city_reader = None
    else:
        log.warning(f"GeoLite2 City DB not found or disabled by config. Path checked: {config.GEOLITE2_CITY_DB_PATH}")

    if config.GEOIP_ASN_ENABLED:
        try:
            _asn_reader = geoip2.database.Reader(str(config.GEOLITE2_ASN_DB_PATH))
            log.info(f"GeoLite2 ASN DB loaded from: {config.GEOLITE2_ASN_DB_PATH}")
        except FileNotFoundError:
            log.error(f"GeoLite2 ASN DB file not found at: {config.GEOLITE2_ASN_DB_PATH}")
            _asn_reader = None
        except Exception as e:
            log.error(f"Failed to load GeoLite2 ASN DB from {config.GEOLITE2_ASN_DB_PATH}: {e}")
            _asn_reader = None
    else:
        log.warning(f"GeoLite2 ASN DB not found or disabled by config. Path checked: {config.GEOLITE2_ASN_DB_PATH}")

_initialize_geoip_readers() 

def get_geoip_data(ip_address: str) -> dict:
    # Пропускаем приватные/локальные IP, так как для них нет GeoIP данных
    if not ip_address or \
       ip_address == "127.0.0.1" or \
       ip_address.startswith("192.168.") or \
       ip_address.startswith("10.") or \
       ip_address.startswith("172.16.") or \
       ip_address.startswith("172.17.") or \
       ip_address.startswith("172.18.") or \
       ip_address.startswith("172.19.") or \
       ip_address.startswith("172.2") or \
       ip_address.startswith("172.30.") or \
       ip_address.startswith("172.31."):
        log.debug(f"Skipping GeoIP lookup for private/local IP: {ip_address}")
        return {} 
    
    geoip_data = {}
    
    if _city_reader:
        try:
            city_response = _city_reader.city(ip_address)
            if city_response.country and city_response.country.iso_code:
                geoip_data['country_iso_code'] = city_response.country.iso_code
            if city_response.country and city_response.country.name:
                geoip_data['country_name'] = city_response.country.name
            if city_response.city and city_response.city.name:
                geoip_data['city_name'] = city_response.city.name
            if city_response.location and city_response.location.latitude:
                geoip_data['latitude'] = city_response.location.latitude
            if city_response.location and city_response.location.longitude:
                geoip_data['longitude'] = city_response.location.longitude
        except AddressNotFoundError:
            log.debug(f"GeoIP City: IP address {ip_address} not found in City database.")
        except Exception as e:
            log.error(f"Error looking up GeoIP City for {ip_address}: {e}")
        
    if _asn_reader:
        try:
            asn_response = _asn_reader.asn(ip_address)
            if asn_response.autonomous_system_number:
                geoip_data['asn_number'] = asn_response.autonomous_system_number
            if asn_response.autonomous_system_organization:
                geoip_data['asn_organization'] = asn_response.autonomous_system_organization
        except AddressNotFoundError:
            log.debug(f"GeoIP ASN: IP address {ip_address} not found in ASN database.")
        except Exception as e:
            log.error(f"Error looking up GeoIP ASN for {ip_address}: {e}")

    return geoip_data