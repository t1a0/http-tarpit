import asyncio
import logging
import sys
import os

try:
    from src.http_tarpit.logger_setup import setup_logging
    setup_logging()
except ImportError as e:
    print(f"Critical Error: Failed to import or run logger setup: {e}", file=sys.stderr)
    print("Please ensure 'src/http_tarpit/logger_setup.py' exists and is correct.", file=sys.stderr)
    sys.exit(1)
except Exception as e_log:
    print(f"Critical Error during logging setup: {e_log}", file=sys.stderr)
    sys.exit(1)



log = logging.getLogger(__name__)

try:
    from src.http_tarpit import config
    from src.http_tarpit.database import init_db 
    from src.http_tarpit.tarpit_server import run_server

    init_db()

except ImportError as e:
    log.exception(f"Failed to import application modules or init DB: {e}")
    sys.exit(1)
except Exception as e_init: 
    log.exception(f"Failed during application initialization: {e_init}")
    sys.exit(1)
    
try:
    from src.http_tarpit import config 
    from src.http_tarpit.tarpit_server import run_server
except ImportError as e:
    log.exception(f"Failed to import application modules: {e}")
    sys.exit(1)



if __name__ == "__main__":
    log.info("Application starting...")
    log.info(f"Configuration: HOST={config.HOST}, PORT={config.PORT}, LOG_FILE={config.LOG_FILE}")

    try:
        asyncio.run(run_server())
    except KeyboardInterrupt:
        log.info("Server stopped by user (KeyboardInterrupt).")
    except Exception as e:
        log.exception(f"A critical error occurred: {e}")
        sys.exit(1) 
    finally:
        log.info("Application shutting down.")