import asyncio
import logging
from aiohttp import web

from .request_handler import handle_request
from . import config

log = logging.getLogger(__name__) 

async def run_server():
    """
    Настраивает и запускает aiohttp сервер тарпита.
    """
    app = web.Application()
    app.router.add_route('*', '/{tail:.*}', handle_request)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, config.HOST, config.PORT)

    log.info(f"Attempting to start HTTP Tarpit server on http://{config.HOST}:{config.PORT}")
    log.info(f"Tarpit settings: Delay={config.RESPONSE_DELAY_SECONDS}s, Chunk={config.RESPONSE_CHUNK!r}, MaxBytes={config.MAX_RESPONSE_BYTES}")

    try:
        await site.start()
        log.info("Server started successfully. Waiting for connections...")
        while True:
            await asyncio.sleep(3600) # Просыпаемся раз в час для проверки
    except Exception as e:
        log.exception("Failed to start or run the server")
        await runner.cleanup()
        raise 
    finally:
        log.info("Server run loop finished or encountered an error.")
        await runner.cleanup()