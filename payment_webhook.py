"""
Модуль для обработки вебхуков платежей Telegram.
Предоставляет функции для проверки и обработки платежей.
"""

import logging
import json
import hmac
import hashlib
import os
from aiohttp import web
from datetime import datetime, timedelta
from database import Database
from typing import Dict, Any

# Настройка логгирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Секретный токен для проверки платежей
PAYMENT_TOKEN_SECRET = os.getenv("PAYMENT_TOKEN_SECRET", "your_payment_secret_token")
TEST_MODE = os.getenv("TEST_MODE", "false").lower() == "true"

# Инициализация базы данных
db = Database()


async def verify_telegram_payment(request):
    """
    Проверяет подлинность вебхука от Telegram Payments API.
    
    Args:
        request: aiohttp Request объект
        
    Returns:
        bool: True если вебхук подлинный, False в противном случае
    """
    # В тестовом режиме всегда возвращаем True
    if TEST_MODE:
        return True
        
    try:
        # Проверка наличия заголовка X-Telegram-Bot-Api-Secret-Token
        if 'X-Telegram-Bot-Api-Secret-Token' not in request.headers:
            logger.warning("Missing X-Telegram-Bot-Api-Secret-Token header")
            return False
        
        # Проверка токена
        secret_token = request.headers['X-Telegram-Bot-Api-Secret-Token']
        if not hmac.compare_digest(secret_token, PAYMENT_TOKEN_SECRET):
            logger.warning("Invalid secret token")
            return False
            
        return True
    except Exception as e:
        logger.error(f"Error verifying payment: {e}")
        return False


async def handle_successful_payment(payment_data: Dict[str, Any]) -> bool:
    """
    Обрабатывает успешный платеж.
    
    Args:
        payment_data: Данные платежа от Telegram
        
    Returns:
        bool: True если обработка прошла успешно, False в противном случае
    """
    try:
        # Инициализация базы данных
        await db.init()
        
        # Извлечение необходимых данных
        telegram_payment_charge_id = payment_data.get('telegram_payment_charge_id')
        provider_payment_charge_id = payment_data.get('provider_payment_charge_id')
        
        # Проверяем, есть ли Invoice payload
        if 'invoice_payload' not in payment_data:
            logger.error("No invoice_payload in payment data")
            return False
        
        # Разбор payload
        payload_str = payment_data['invoice_payload']
        
        # Проверяем формат payload (должен быть 'order:123' или 'subscription:123')
        if ":" not in payload_str:
            logger.error(f"Invalid payload format: {payload_str}")
            return False
            
        payload_type, order_id_str = payload_str.split(":", 1)
        
        try:
            order_id = int(order_id_str)
        except ValueError:
            logger.error(f"Invalid order ID in payload: {order_id_str}")
            return False
        
        # Получение заказа из БД
        order = await db.get_order(order_id)
        if not order:
            logger.error(f"Order not found: {order_id}")
            return False
            
        # Обновление статуса заказа в БД
        await db.update_order_status(order_id, 'paid')
        
        # Обработка различных типов продуктов
        if order['product'] == 'full_report':
            # Генерация и отправка PDF отчета
            await process_full_report_payment(order)
            
        elif order['product'] == 'compatibility':
            # Генерация и отправка отчета о совместимости
            await process_compatibility_payment(order)
            
        elif order['product'] == 'subscription_month':
            # Активация подписки
            await process_subscription_payment(order)
        
        return True
        
    except Exception as e:
        logger.error(f"Error processing successful payment: {e}")
        return False


async def process_full_report_payment(order: Dict[str, Any]):
    """
    Обрабатывает оплату полного отчета.
    
    Args:
        order: Данные заказа
    """
    # Здесь должен быть код для генерации и отправки PDF-отчета
    # В рамках этого файла мы только логируем событие
    logger.info(f"Processing full report payment for order: {order['id']}")
    
    # В реальном коде здесь должен быть вызов функций из bot.py для отправки отчета


async def process_compatibility_payment(order: Dict[str, Any]):
    """
    Обрабатывает оплату отчета о совместимости.
    
    Args:
        order: Данные заказа
    """
    logger.info(f"Processing compatibility report payment for order: {order['id']}")
    
    # В реальном коде здесь должен быть вызов функций из bot.py для отправки отчета


async def process_subscription_payment(order: Dict[str, Any]):
    """
    Обрабатывает оплату подписки.
    
    Args:
        order: Данные заказа
    """
    logger.info(f"Processing subscription payment for order: {order['id']}")
    
    # Активация подписки в БД
    now = datetime.now().date()
    next_charge = now + timedelta(days=30)
    
    # Получение пользователя
    user_id = order['user_id']
    
    # Создание записи о подписке
    await db.create_subscription(user_id, "active")
    
    # В реальном коде здесь должен быть вызов функций из bot.py для отправки уведомления


async def handle_payment_webhook(request: web.Request) -> web.Response:
    """
    Обрабатывает вебхуки от Telegram Payments API.
    
    Args:
        request: aiohttp Request объект
        
    Returns:
        aiohttp.web.Response
    """
    # Проверка подлинности вебхука
    if not await verify_telegram_payment(request):
        return web.Response(status=401, text="Unauthorized")
        
    try:
        # Получение данных запроса
        data = await request.json()
        logger.info(f"Received payment webhook: {data}")
        
        # В тестовом режиме всегда возвращаем успешный ответ
        if TEST_MODE:
            logger.info("Test mode: Simulating successful payment processing")
            return web.Response(status=200, text="Payment webhook processed in test mode")
        
        # Проверка на успешный платеж
        if 'update_id' in data and 'message' in data:
            message = data['message']
            if 'successful_payment' in message:
                payment_data = message['successful_payment']
                
                if await handle_successful_payment(payment_data):
                    return web.Response(status=200, text="Payment processed successfully")
                else:
                    return web.Response(status=500, text="Error processing payment")
        
        # Обрабатываем другие типы уведомлений
        return web.Response(status=200, text="Notification received")
        
    except Exception as e:
        logger.error(f"Error in payment webhook handler: {e}")
        return web.Response(status=500, text=f"Error: {str(e)}")


async def setup_payment_webhook_server(host='0.0.0.0', port=8080):
    """
    Настраивает и запускает веб-сервер для обработки вебхуков платежей.
    
    Args:
        host: Хост для веб-сервера
        port: Порт для веб-сервера
    """
    # Инициализация базы данных
    await db.init()
    
    app = web.Application()
    app.router.add_post('/payment', handle_payment_webhook)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    
    logger.info(f"Starting payment webhook server on {host}:{port}")
    await site.start()
    
    return runner