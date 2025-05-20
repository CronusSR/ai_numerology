# Скрипт для отправки еженедельных прогнозов подписчикам
# Запускается через cron-задачу раз в неделю

import asyncio
import logging
import os
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Any

# Настройка путей для импорта модулей из основного проекта
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Импортируем необходимые модули
try:
    from database_sqlite import Database  # Сначала пробуем импортировать SQLite версию
except ImportError:
    from database import Database  # Если нет, используем оригинальную

from numerology_core import calculate_digit_sum, get_personal_year
from interpret import send_to_n8n_for_interpretation

# Настройка логгирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='weekly_forecast.log'
)
logger = logging.getLogger(__name__)

# Загрузка переменных окружения
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    logger.info("python-dotenv не установлен, используем переменные окружения системы")

# Загрузка токена бота
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    logger.error("BOT_TOKEN не найден в переменных окружения")
    sys.exit(1)

# Инициализация бота для отправки сообщений
from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

# Инициализация базы данных
db = Database()


async def get_active_subscribers() -> List[Dict[str, Any]]:
    """
    Получает список активных подписчиков из базы данных.
    
    Returns:
        List[Dict[str, Any]]: Список словарей с данными подписчиков
    """
    try:
        # Инициализация базы данных
        await db.init()
        
        # Получение активных подписок
        subscriptions = await db.get_active_subscriptions()
        
        # Получение данных пользователей для каждой подписки
        subscribers = []
        for subscription in subscriptions:
            user_id = subscription.get("user_id")
            user = await db.get_user_by_id(user_id)
            
            if user and user.get("push_enabled", True):
                subscribers.append({
                    "user_id": user_id,
                    "tg_id": user.get("tg_id"),
                    "fio": user.get("fio"),
                    "birthdate": user.get("birthdate"),
                    "subscription": subscription
                })
        
        return subscribers
    except Exception as e:
        logger.error(f"Ошибка при получении активных подписчиков: {e}")
        return []


async def generate_weekly_forecast(user_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Генерирует еженедельный прогноз для пользователя.
    
    Args:
        user_data: Словарь с данными пользователя
        
    Returns:
        Dict[str, Any]: Словарь с прогнозом
    """
    try:
        # Получение данных пользователя
        birthdate = user_data.get("birthdate")
        fio = user_data.get("fio")
        
        if not birthdate or not fio:
            logger.warning(f"Недостаточно данных для пользователя {user_data.get('tg_id')}")
            return {"error": "Недостаточно данных для генерации прогноза"}
        
        # Получение текущей даты
        now = datetime.now()
        current_week = now.isocalendar()[1]  # Номер недели в году
        
        # Расчет числа недели (от 1 до 9)
        week_number = calculate_digit_sum(current_week)
        
        # Расчет личного года
        personal_year = get_personal_year(birthdate)
        
        # Дополнительные расчеты по новой логике
        numerology_data = calculate_numerology(birthdate, fio)
        
        # Формирование данных для отправки на интерпретацию
        forecast_data = {
            "user": {
                "fio": fio,
                "birthdate": birthdate
            },
            "forecast": {
                "week_number": week_number,
                "personal_year": personal_year,
                "date_from": (now - timedelta(days=now.weekday())).strftime("%Y-%m-%d"),
                "date_to": (now + timedelta(days=6-now.weekday())).strftime("%Y-%m-%d")
            },
            "numerology": numerology_data  # Добавляем полные нумерологические данные
        }
        
        # Отправка данных на интерпретацию через n8n
        interpretation = await send_to_n8n_for_interpretation(forecast_data, "weekly")
        
        return interpretation
    except Exception as e:
        logger.error(f"Ошибка при генерации еженедельного прогноза: {e}")
        return {"error": f"Ошибка при генерации прогноза: {str(e)}"}


async def send_forecast_to_user(tg_id: int, forecast: Dict[str, Any]) -> bool:
    """
    Отправляет еженедельный прогноз пользователю.
    
    Args:
        tg_id: Telegram ID пользователя
        forecast: Словарь с прогнозом
        
    Returns:
        bool: True если отправка прошла успешно, False в противном случае
    """
    try:
        # Проверка наличия ошибки в прогнозе
        if "error" in forecast:
            logger.error(f"Ошибка в прогнозе для пользователя {tg_id}: {forecast['error']}")
            return False
        
        # Получение текста прогноза
        forecast_text = forecast.get("weekly_forecast", "")
        if not forecast_text:
            logger.warning(f"Пустой прогноз для пользователя {tg_id}")
            return False
        
        # Получение текущей даты
        now = datetime.now()
        date_from = (now - timedelta(days=now.weekday())).strftime("%d.%m.%Y")
        date_to = (now + timedelta(days=6-now.weekday())).strftime("%d.%m.%Y")
        
        # Формирование сообщения
        message = (
            f"🔮 <b>Ваш еженедельный нумерологический прогноз</b>\n"
            f"<i>на период {date_from} - {date_to}</i>\n\n"
            f"{forecast_text}\n\n"
            f"Хорошей недели! Ваш ИИ-Нумеролог."
        )
        
        # Отправка сообщения пользователю
        await bot.send_message(chat_id=tg_id, text=message)
        
        return True
    except Exception as e:
        logger.error(f"Ошибка при отправке прогноза пользователю {tg_id}: {e}")
        return False


async def process_weekly_forecasts():
    """
    Основная функция для обработки и отправки еженедельных прогнозов.
    """
    try:
        logger.info("Начало отправки еженедельных прогнозов")
        
        # Получение активных подписчиков
        subscribers = await get_active_subscribers()
        logger.info(f"Найдено {len(subscribers)} активных подписчиков")
        
        # Обработка каждого подписчика
        success_count = 0
        for subscriber in subscribers:
            tg_id = subscriber.get("tg_id")
            
            if not tg_id:
                logger.warning(f"Не найден Telegram ID для пользователя {subscriber.get('user_id')}")
                continue
            
            # Генерация прогноза
            forecast = await generate_weekly_forecast(subscriber)
            
            # Отправка прогноза
            if await send_forecast_to_user(tg_id, forecast):
                success_count += 1
                logger.info(f"Прогноз успешно отправлен пользователю {tg_id}")
            else:
                logger.warning(f"Не удалось отправить прогноз пользователю {tg_id}")
        
        logger.info(f"Отправка еженедельных прогнозов завершена. Успешно: {success_count}/{len(subscribers)}")
    except Exception as e:
        logger.error(f"Ошибка при обработке еженедельных прогнозов: {e}")
    finally:
        # Закрытие соединения с ботом
        await bot.session.close()


if __name__ == "__main__":
    # Запуск основной функции
    asyncio.run(process_weekly_forecasts())
