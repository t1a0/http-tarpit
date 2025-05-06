import logging 
import geoip2.database
from geoip2.errors import AddressNotFoundError

from .. import config

log = logging.getLogger(__name__)

_city_reader = None
_asn_reader = None

def _initialize_geoip_readers():
    global _city_reader, _asn_reader
    
    if config.GEOLITE2_CITY_DB_PATH:
        try:
            _city_reader = geoip2.database.Reader(str(config.GEOLITE2_CITY_DB_PATH))
            log.info(f"Geolite2 City DB Loaded from: {config.GEOLITE2_CITY_DB_PATH}")
        except Exception as e:
            log.error(f"Failed to load GeoLite2 City DB from {config.GEOLITE2_CITY_DB_PATH}")
            _city_reader = None
    else:
        log.warning(f"GeoLite2 City DB not found or disabled. Path: {config.GEOLITE2_CITY_DB_PATH}")
        
    if config.GEOIP_ASN_ENABLED:
        try:
            _city_reader = geoip2.database.Reader(str(config.GEOLITE2_ASN_DB_PATH))
            log.info(f"Geolite2 ASN DB Loaded from: {config.GEOLITE2_ASN_DB_PATH}")
        except Exception as e:
            log.error(f"Failed to load GeoLite2 ASN DB from {config.GEOLITE2_ASN_DB_PATH}")
            _city_reader = None
    else:
        log.warning(f"GeoLite2 ASN DB not found or disabled. Path: {config.GEOLITE2_ASN_DB_PATH}")

_initialize_geoip_readers()

def get_geoip_data(ip_address: str) -> dict:
    if not ip_address or ip_address == "127.0.0.1" or ip_address.startswith("192.168.") or ip_address.startswith("10."):
        return {}
    
    geoip_data = {}
    
    if _city_reader:
        try:
            response = _city_reader.city(ip_address)
            if response.country.iso_code:
                geoip_data['country_iso_code'] = response.country.iso_code
            if response.country.name:
                geoip_data['country_name'] = response.country.name
            if response.city.name:
                geoip_data['city_name'] = response.city.name
            if response.location.latitude:
                geoip_data['latitude'] = response.location.latitude
            if response.location.longitude:
                geoip_data['longitude'] = response.location.longitude
        except AddressNotFoundError:
            log.debug(f"GeoIP City: IP address {ip_address} not found in database.")
        except Exception as e:
            log.error(f"Error looking up GeoIP City for {ip_address}: {e}")
        
    if _asn_reader:
        try:
            response = _asn_reader.asn(ip_address)
            if response.autonomous_system_number:
                geoip_data['asn_number'] = response.autonomous_system_number
            if response.autonomous_system_organization:
                geoip_data['asn_organization'] = response.autonomous_system_organization
        except AddressNotFoundError:
            log.debug(f"GeoIP ASN: IP address {ip_address} not found in database.")
        except Exception as e:
            log.error(f"Error looking up GeoIP ASN for {ip_address}: {e}")

    return geoip_data