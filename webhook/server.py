import logging
from aiohttp import web
from aiohttp.web import Request, Response
import json

from config.settings import WEBHOOK_HOST, WEBHOOK_PORT
from webhook.handlers import yookassa_webhook_handler, health_check_handler

logger = logging.getLogger("webhook")


def create_webhook_app() -> web.Application:
    """
    Создание веб-приложения для webhook'ов
    
    Returns:
        Настроенное aiohttp приложение
    """
    app = web.Application()
    
    # Middleware для логирования
    @web.middleware
    async def logging_middleware(request: Request, handler):
        start_time = request.loop.time()
        
        try:
            response = await handler(request)
            process_time = request.loop.time() - start_time
            
            logger.info(
                f"{request.method} {request.path} - "
                f"Status: {response.status} - "
                f"Time: {process_time:.3f}s"
            )
            
            return response
            
        except Exception as e:
            process_time = request.loop.time() - start_time
            logger.error(
                f"{request.method} {request.path} - "
                f"Error: {str(e)} - "
                f"Time: {process_time:.3f}s"
            )
            raise
    
    # Middleware для CORS (если нужно)
    @web.middleware
    async def cors_middleware(request: Request, handler):
        response = await handler(request)
        
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        
        return response
    
    # Middleware для обработки ошибок
    @web.middleware
    async def error_middleware(request: Request, handler):
        try:
            return await handler(request)
        except web.HTTPException:
            raise
        except Exception as e:
            logger.error(f"Unhandled error in {request.path}: {e}")
            return web.json_response(
                {"error": "Internal server error"},
                status=500
            )
    
    # Добавляем middleware
    app.middlewares.extend([
        logging_middleware,
        cors_middleware,
        error_middleware
    ])
    
    # Регистрируем маршруты
    app.router.add_post('/webhook/yookassa', yookassa_webhook_handler)
    app.router.add_get('/health', health_check_handler)
    app.router.add_get('/status', health_check_handler)  # Альтернативный endpoint
    
    # Обработчик для root
    async def root_handler(request: Request) -> Response:
        return web.json_response({
            "service": "Payment Bot Webhook Server",
            "status": "running",
            "endpoints": [
                "/webhook/yookassa",
                "/health",
                "/status"
            ]
        })
    
    app.router.add_get('/', root_handler)
    
    # Обработчик для OPTIONS запросов
    async def options_handler(request: Request) -> Response:
        return web.Response(
            status=200,
            headers={
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type, Authorization'
            }
        )
    
    app.router.add_route('OPTIONS', '/{path:.*}', options_handler)
    
    return app


async def start_webhook_server():
    """
    Запуск webhook сервера
    """
    try:
        app = create_webhook_app()
        
        # Настройка сервера
        runner = web.AppRunner(app)
        await runner.setup()
        
        site = web.TCPSite(
            runner, 
            host='0.0.0.0',  # Слушаем на всех интерфейсах
            port=WEBHOOK_PORT
        )
        
        await site.start()
        
        logger.info(f"Webhook сервер запущен на http://0.0.0.0:{WEBHOOK_PORT}")
        logger.info(f"Внешний URL: https://{WEBHOOK_HOST}")
        logger.info("Доступные endpoints:")
        logger.info(f"  - POST https://{WEBHOOK_HOST}/webhook/yookassa")
        logger.info(f"  - GET  https://{WEBHOOK_HOST}/health")
        
        # Держим сервер запущенным
        while True:
            await asyncio.sleep(3600)  # Спим час
            
    except Exception as e:
        logger.error(f"Ошибка запуска webhook сервера: {e}")
        raise


# Для запуска сервера отдельно
if __name__ == "__main__":
    import asyncio
    from utils.logger import setup_logging
    from config.settings import LOG_LEVEL, LOG_DIR
    
    # Настройка логирования
    setup_logging(level=LOG_LEVEL, log_dir=LOG_DIR)
    
    # Запуск сервера
    asyncio.run(start_webhook_server())