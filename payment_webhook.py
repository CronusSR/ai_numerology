"""
Модуль для обработки вебхуков платежей Telegram.
Предоставляет функции для проверки и обработки платежей.
"""

import logging
import json
import hmac
import hashlib
from aiohttp import web
from datetime import datetime, timedelta
import database
from bot import bot, generate_and_send_pdf

# Настройка логгирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Секретный токен для проверки платежей (должен быть в переменных окружения в реальном приложении)
PAYMENT_TOKEN_SECRET = "YOUR_PAYMENT_SECRET_TOKEN"  # Замените на реальный токен в production


async def verify_telegram_payment(request):
    """
    Проверяет подлинность вебхука от Telegram Payments API.
    
    Args:
        request: aiohttp Request объект
        
    Returns:
        bool: True если вебхук подлинный, False в противном случае
    """
    try:
        data = await request.json()
        
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


async def handle_successful_payment(payment_data):
    """
    Обрабатывает успешный платеж.
    
    Args:
        payment_data: Данные платежа от Telegram
        
    Returns:
        bool: True если обработка прошла успешно, False в противном случае
    """
    try:
        # Извлечение необходимых данных
        telegram_payment_charge_id = payment_data.get('telegram_payment_charge_id')
        provider_payment_charge_id = payment_data.get('provider_payment_charge_id')
        
        # Проверяем, есть ли Invoice payload
        if 'invoice_payload' not in payment_data:
            logger.error("No invoice_payload in payment data")
            return False
            
        # Разбор payload
        payload = json.loads(payment_data['invoice_payload'])
        user_id = payload.get('user_id')
        product_type = payload.get('product_type')
        order_id = payload.get('order_id')
        
        if not all([user_id, product_type, order_id]):
            logger.error(f"Missing required fields in payload: {payload}")
            return False
            
        # Обновление статуса заказа в БД
        await database.update_order_status(
            order_id=order_id,
            status='paid',
            telegram_payment_charge_id=telegram_payment_charge_id,
            provider_payment_charge_id=provider_payment_charge_id
        )
        
        # Обработка различных типов продуктов
        if product_type == 'full_report':
            # Генерация и отправка PDF отчета
            await generate_and_send_pdf(user_id)
            
        elif product_type == 'compatibility':
            # Генерация и отправка отчета о совместимости
            await generate_and_send_pdf(user_id, report_type='compatibility')
            
        elif product_type == 'subscription_month':
            # Активация подписки
            trial_end = datetime.now()
            next_charge = trial_end + timedelta(days=30)
            
            await database.create_subscription(
                user_id=user_id,
                status='active',
                trial_end=trial_end,
                next_charge=next_charge,
                provider_id=provider_payment_charge_id
            )
            
            # Отправляем сообщение о успешной активации подписки
            user_data = await database.get_user(user_id)
            tg_id = user_data.get('tg_id')
            if tg_id:
                await bot.send_message(
                    tg_id,
                    "🌟 Ваша подписка успешно активирована! Теперь вы будете получать еженедельные "
                    "нумерологические прогнозы. Следующее списание через 30 дней."
                )
        
        return True
        
    except Exception as e:
        logger.error(f"Error processing successful payment: {e}")
        return False


async def handle_payment_webhook(request):
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
        data = await request.json()
        logger.info(f"Received payment webhook: {data}")
        
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
    app = web.Application()
    app.router.add_post('/payment', handle_payment_webhook)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    
    logger.info(f"Starting payment webhook server on {host}:{port}")
    await site.start()
    
    return runner