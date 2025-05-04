import asyncio
import logging
import time
from aiohttp import web

# --- Конфигурация (пока здесь, потом вынесем) ---
HOST = '0.0.0.0'        # Слушать на всех интерфейсах
PORT = 8080             # Используем > 1024, чтобы не нужен был sudo
RESPONSE_DELAY_SECONDS = 2.0  # Задержка между отправкой байтов
RESPONSE_CHUNK = b'.'         # Что отправляем (1 байт)
MAX_RESPONSE_BYTES = 50      # Макс. кол-во байт для отправки перед закрытием
# ---

# Получаем логгер для этого модуля
log = logging.getLogger(__name__) # Используем имя модуля для логгера

async def handle_request(request):
    """
    Обработчик входящих HTTP запросов. Отвечает очень медленно.
    """
    start_time = time.monotonic()
    peername = request.transport.get_extra_info('peername')
    ip_addr = "Unknown"
    port = 0
    if peername:
        ip_addr = peername[0]
        port = peername[1]

    log.info(f"Connection received from: {ip_addr}:{port} - {request.method} {request.path}")

    response_status = 200
    bytes_sent_total = 0

    try:
        # Используем StreamResponse для контроля над потоком данных
        response = web.StreamResponse(
            status=response_status,
            reason='OK',
            headers={'Content-Type': 'text/plain', 'Connection': 'keep-alive'}
        )
        # Сразу отправляем заголовки клиенту
        await response.prepare(request)
        log.debug(f"Sent headers to {ip_addr}:{port}")

        # Медленно отправляем тело ответа по кусочкам
        while bytes_sent_total < MAX_RESPONSE_BYTES:
            try:
                await response.write(RESPONSE_CHUNK)
                # Важно: гарантирует, что данные отправлены в сеть перед паузой
                await response.drain()
                bytes_sent_total += len(RESPONSE_CHUNK)
                log.debug(f"Sent {len(RESPONSE_CHUNK)} byte(s) to {ip_addr}:{port} (total: {bytes_sent_total})")
                # Ждем перед отправкой следующего кусочка
                await asyncio.sleep(RESPONSE_DELAY_SECONDS)
            except ConnectionResetError:
                log.warning(f"Connection reset by peer {ip_addr}:{port} during write.")
                # Прерываем цикл, если клиент отключился
                break
            except Exception as e_write:
                log.error(f"Error writing to {ip_addr}:{port}: {e_write}")
                break # Прерываем при других ошибках записи

        # Завершаем HTTP ответ (отправляем финальный чанк, если нужно по протоколу)
        await response.write_eof()

        end_time = time.monotonic()
        duration = end_time - start_time
        log.info(f"Connection finished for {ip_addr}:{port}. Bytes sent: {bytes_sent_total}. Duration: {duration:.2f}s")
        return response

    except Exception as e_prepare:
        # Ловим ошибки, которые могли произойти до или во время response.prepare()
        end_time = time.monotonic()
        duration = end_time - start_time
        log.error(f"Error handling request from {ip_addr}:{port} (prepare phase?): {e_prepare}. Duration: {duration:.2f}s", exc_info=True)
        # Если не удалось даже начать StreamResponse, вернем обычный ответ об ошибке
        # (хотя в этом случае клиент все равно может не получить его)
        return web.Response(status=500, text="Internal Server Error")


async def start_server():
    """
    Настраивает и запускает aiohttp сервер.
    """
    app = web.Application()
    # Направляем все запросы на наш медленный обработчик
    app.router.add_route('*', '/{tail:.*}', handle_request)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, HOST, PORT)
    log.info(f"Starting HTTP Tarpit server on http://{HOST}:{PORT}")
    log.info(f"Response delay: {RESPONSE_DELAY_SECONDS}s, Chunk: {RESPONSE_CHUNK!r}, Max bytes: {MAX_RESPONSE_BYTES}")
    await site.start()
    log.info("Server started successfully.")

    # Держим сервер работающим (можно сделать более элегантное ожидание)
    while True:
        await asyncio.sleep(3600)