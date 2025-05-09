# bot.py - основной файл бота
import logging
import os
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from aiogram import Bot, Dispatcher, Router, types
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.types import (
    Message, InlineKeyboardButton, InlineKeyboardMarkup, PreCheckoutQuery,
    LabeledPrice, FSInputFile
)
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

from database import Database
from numerology_core import calculate_numerology, calculate_compatibility
from interpret import send_to_n8n_for_interpretation
from pdf_generator import generate_pdf

# Настройка логгирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Загрузка переменных окружения
BOT_TOKEN = os.getenv("BOT_TOKEN")
PAYMENT_TOKEN = os.getenv("PAYMENT_PROVIDER_TOKEN")
WEBHOOK_HOST = os.getenv("WEBHOOK_HOST")
WEBHOOK_PATH = os.getenv("WEBHOOK_PATH", "/webhook")
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"
PDF_STORAGE_PATH = os.getenv("PDF_STORAGE_PATH", "./pdfs")
TEST_MODE = os.getenv("TEST_MODE", "false").lower() == "true"

# Создаем директорию для хранения PDF, если она не существует
os.makedirs(PDF_STORAGE_PATH, exist_ok=True)

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = os.getenv("REDIS_PORT", "6379")
storage = RedisStorage.from_url(f'redis://{REDIS_HOST}:{REDIS_PORT}/0')
dp = Dispatcher(storage=storage)
router = Router()
dp.include_router(router)

# Подключение к базе данных
db = Database()

# Определение состояний для FSM
class UserStates(StatesGroup):
    waiting_for_birthdate = State()
    waiting_for_name = State()
    waiting_for_partner_birthdate = State()
    waiting_for_partner_name = State()

# Обработчик команды /start
@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    user_id = message.from_user.id
    
    # Проверка наличия пользователя в БД и создание, если отсутствует
    user = await db.get_user_by_tg_id(user_id)
    if not user:
        await db.create_user(user_id)
    
    # Приветственное сообщение
    await message.answer(
        "Привет! Я ИИ-Нумеролог. Могу рассчитать ваш нумерологический портрет и дать индивидуальные рекомендации.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Сделать расчёт", callback_data="start_calculation")]
        ])
    )
    
    # Сброс состояния FSM
    await state.clear()

# Обработчик кнопки "Сделать расчёт"
@router.callback_query(lambda c: c.data == "start_calculation")
async def process_calculation_button(callback_query: types.CallbackQuery, state: FSMContext):
    # Подтверждение запроса
    await callback_query.answer()
    
    # Запрос даты рождения
    await callback_query.message.answer(
        "Пожалуйста, введите вашу дату рождения в формате ДД.ММ.ГГГГ (например, 01.01.1990)"
    )
    
    # Установка состояния ожидания даты рождения
    await state.set_state(UserStates.waiting_for_birthdate)

# Обработчик ввода даты рождения
@router.message(UserStates.waiting_for_birthdate)
async def process_birthdate(message: Message, state: FSMContext):
    # Сохранение даты рождения в контексте FSM
    try:
        birthdate = datetime.strptime(message.text, "%d.%m.%Y").date()
        await state.update_data(birthdate=birthdate.strftime("%Y-%m-%d"))
        
        # Запрос ФИО
        await message.answer("Спасибо! Теперь введите ваше полное ФИО")
        
        # Установка состояния ожидания ФИО
        await state.set_state(UserStates.waiting_for_name)
    except ValueError:
        await message.answer(
            "Неверный формат даты. Пожалуйста, введите дату в формате ДД.ММ.ГГГГ (например, 01.01.1990)"
        )

# Обработчик ввода ФИО
@router.message(UserStates.waiting_for_name)
async def process_name(message: Message, state: FSMContext):
    # Сохранение ФИО в контексте FSM
    await state.update_data(fio=message.text)
    
    # Получение данных из контекста
    user_data = await state.get_data()
    birthdate = user_data.get("birthdate")
    fio = user_data.get("fio")
    
    # Обновление данных пользователя в БД
    await db.update_user(message.from_user.id, fio, birthdate)
    
    # Выполнение нумерологических расчетов
    numerology_results = calculate_numerology(birthdate, fio)
    
    # Сохранение результатов в БД
    report_id = await db.save_report(message.from_user.id, "mini", numerology_results)
    
    # Отправка результатов на интерпретацию через n8n
    interpretation = await send_to_n8n_for_interpretation(numerology_results, "mini")
    
    # Формирование и отправка мини-отчета
    mini_report_text = interpretation.get('mini_report', 'Извините, не удалось получить интерпретацию.')
    
    buttons = [
        [InlineKeyboardButton(text="Полный PDF - 149 ₽", callback_data=f"buy_full_report:{report_id}")]
    ]
    
    # В тестовом режиме добавляем кнопку "Получить бесплатно (тестовый режим)"
    if TEST_MODE:
        buttons.append([
            InlineKeyboardButton(
                text="Получить бесплатно (тестовый режим)", 
                callback_data=f"test_full_report:{report_id}"
            )
        ])
    
    await message.answer(
        f"Ваш мини-отчет:\n\n{mini_report_text}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )
    
    # Сброс состояния FSM
    await state.clear()

# Обработчик кнопки "Получить бесплатно (тестовый режим)"
@router.callback_query(lambda c: c.data and c.data.startswith("test_full_report:"))
async def process_test_full_report(callback_query: types.CallbackQuery):
    if not TEST_MODE:
        await callback_query.answer("Тестовый режим отключен")
        return
        
    # Подтверждение запроса
    await callback_query.answer()
    
    # Получение ID отчета из callback_data
    report_id = int(callback_query.data.split(":")[1])
    
    # Получение отчета
    report = await db.get_report(report_id)
    
    if not report:
        await callback_query.message.answer("Отчет не найден. Пожалуйста, создайте новый расчет.")
        return
        
    # Получение данных пользователя
    user_id = report["user_id"]
    user = await db.get_user_by_id(user_id)
    
    if not user:
        await callback_query.message.answer("Произошла ошибка: пользователь не найден.")
        return
        
    # Отправка запроса на интерпретацию для полного отчета
    interpretation = await send_to_n8n_for_interpretation(report["core_json"], "full")
    
    # Временно помечаем пользователя о генерации отчета
    await callback_query.message.answer("⏳ Генерация полного отчета... Пожалуйста, подождите.")
    
    # Генерация PDF
    pdf_path = generate_pdf(user, report["core_json"], interpretation.get("full_report", {}))
    
    if not pdf_path:
        await callback_query.message.answer("Произошла ошибка при генерации PDF. Пожалуйста, попробуйте позже.")
        return
        
    # Обновление URL PDF в БД
    await db.update_report_pdf(report_id, pdf_path)
    
    # Отправка PDF пользователю
    await callback_query.message.answer("✅ Ваш полный отчет готов (тестовый режим).")
    
    # Скачивание PDF и отправка пользователю
    pdf_file = FSInputFile(pdf_path, filename="numerology_report.pdf")
    await bot.send_document(callback_query.message.chat.id, pdf_file)
    
    # Предложение подписки
    subscription_buttons = [
        [InlineKeyboardButton(text="Оформить подписку", callback_data="subscribe")]
    ]
    
    # В тестовом режиме добавляем кнопку для бесплатной тестовой подписки
    if TEST_MODE:
        subscription_buttons.append([
            InlineKeyboardButton(
                text="Активировать бесплатно (тестовый режим)", 
                callback_data="test_subscribe"
            )
        ])
    
    await callback_query.message.answer(
        "🌟 Хотите получать еженедельные нумерологические прогнозы?\n"
        "Оформите подписку всего за 299 ₽ в месяц!",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=subscription_buttons)
    )

# Обработчик кнопки "Активировать бесплатно (тестовый режим)" для подписки
@router.callback_query(lambda c: c.data == "test_subscribe")
async def process_test_subscription(callback_query: types.CallbackQuery):
    if not TEST_MODE:
        await callback_query.answer("Тестовый режим отключен")
        return
        
    # Подтверждение запроса
    await callback_query.answer()
    
    # Получение пользователя
    user_id = callback_query.from_user.id
    user = await db.get_user_by_tg_id(user_id)
    
    if not user:
        await callback_query.message.answer("Произошла ошибка: пользователь не найден.")
        return
    
    # Получение текущей подписки
    subscription = await db.get_user_subscription(user_id)
    
    if subscription and subscription["status"] in ["active", "trial"]:
        # Если подписка уже активна
        await callback_query.message.answer(
            "У вас уже есть активная подписка. "
            "Еженедельно вы будете получать персональный нумерологический прогноз."
        )
    else:
        # Создаем тестовую подписку
        subscription_id = await db.create_subscription(user_id, "trial")
        
        if subscription_id:
            await callback_query.message.answer(
                "✅ Тестовая подписка активирована!\n\n"
                "Вы будете получать еженедельные нумерологические прогнозы в течение 7 дней.\n"
                "По окончании тестового периода подписка автоматически отключится.\n\n"
                "Управление подпиской доступно через команду /subscribe."
            )
        else:
            await callback_query.message.answer(
                "Произошла ошибка при активации подписки. Пожалуйста, попробуйте позже."
            )

# Обработчик кнопки "Оформить подписку" (платная версия)
@router.callback_query(lambda c: c.data == "subscribe")
async def process_subscription(callback_query: types.CallbackQuery):
    # Подтверждение запроса
    await callback_query.answer()
    
    # Проверка на тестовый режим
    if TEST_MODE or not PAYMENT_TOKEN:
        await callback_query.message.answer(
            "⚠️ Платежная система не настроена или бот работает в тестовом режиме.\n"
            "Для тестирования используйте кнопку \"Активировать бесплатно (тестовый режим)\"."
        )
        return
    
    # Получение пользователя
    user_id = callback_query.from_user.id
    
    # Создание заказа в БД
    order_id = await db.create_order(
        user_id,
        product="subscription_month",
        price=299.0,
        currency="RUB",
        payload={"type": "subscription", "duration": "month"}
    )
    
    if not order_id:
        await callback_query.message.answer("Произошла ошибка при создании заказа.")
        return
    
    # Создание платежного инвойса
    await bot.send_invoice(
        chat_id=callback_query.message.chat.id,
        title="Подписка на ИИ-Нумеролог",
        description="Еженедельные персональные нумерологические прогнозы на 1 месяц",
        payload=f"subscription:{order_id}",
        provider_token=PAYMENT_TOKEN,
        currency="RUB",
        prices=[LabeledPrice(label="Подписка на 1 месяц", amount=29900)],  # в копейках
        max_tip_amount=10000,
        suggested_tip_amounts=[5000, 10000],
        start_parameter="subscription",
        provider_data=None,
        photo_url="https://example.com/subscription.jpg",
        photo_size=512,
        photo_width=512,
        photo_height=512,
        need_name=False,
        need_phone_number=False,
        need_email=False,
        need_shipping_address=False,
        send_phone_number_to_provider=False,
        send_email_to_provider=False,
        is_flexible=False,
        disable_notification=False,
        protect_content=False,
        reply_to_message_id=None,
        allow_sending_without_reply=True,
        reply_markup=None,
        request_timeout=15
    )

# Обработчик предварительной проверки платежа
@router.pre_checkout_query()
async def process_pre_checkout_query(pre_checkout_query: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

# Обработчик успешного платежа
@router.message(lambda message: message.successful_payment)
async def process_successful_payment(message: Message):
    payment = message.successful_payment
    payload = payment.invoice_payload
    
    # Разбор payload
    if ":" not in payload:
        logger.error(f"Invalid payload format: {payload}")
        await message.answer("Произошла ошибка при обработке платежа.")
        return
    
    payload_type, order_id_str = payload.split(":", 1)
    
    try:
        order_id = int(order_id_str)
    except ValueError:
        logger.error(f"Invalid order ID in payload: {order_id_str}")
        await message.answer("Произошла ошибка при обработке платежа.")
        return
    
    # Получение заказа
    order = await db.get_order(order_id)
    if not order:
        logger.error(f"Order not found: {order_id}")
        await message.answer("Произошла ошибка: заказ не найден.")
        return
    
    # Обновление статуса заказа
    await db.update_order_status(order_id, "paid")
    
    # Обработка различных типов продуктов
    if order["product"] == "full_report":
        # Обработка покупки полного отчета
        await process_full_report_payment(message, order)
    elif order["product"] == "compatibility":
        # Обработка покупки отчета о совместимости
        await process_compatibility_payment(message, order)
    elif order["product"] == "subscription_month":
        # Обработка покупки подписки
        await process_subscription_payment(message, order)
    else:
        await message.answer(f"Оплата за {order['product']} успешно получена.")

async def process_full_report_payment(message: Message, order: Dict[str, Any]):
    """Обрабатывает успешную оплату полного отчета"""
    user_id = order["user_id"]
    payload = order.get("payload", {})
    report_id = payload.get("report_id")
    
    if not report_id:
        await message.answer("Произошла ошибка: не указан ID отчета.")
        return
    
    # Получение отчета
    report = await db.get_report(report_id)
    if not report:
        await message.answer("Произошла ошибка: отчет не найден.")
        return
    
    # Получение данных пользователя
    user = await db.get_user_by_id(user_id)
    if not user:
        await message.answer("Произошла ошибка: пользователь не найден.")
        return
    
    # Отправка уведомления пользователю
    await message.answer("✅ Оплата успешно получена! Генерирую ваш полный отчет...")
    
    # Отправка запроса на интерпретацию для полного отчета
    interpretation = await send_to_n8n_for_interpretation(report["core_json"], "full")
    
    # Генерация PDF
    pdf_path = generate_pdf(user, report["core_json"], interpretation.get("full_report", {}))
    
    if not pdf_path:
        await message.answer("Произошла ошибка при генерации PDF. Пожалуйста, обратитесь в поддержку.")
        return
    
    # Обновление URL PDF в БД
    await db.update_report_pdf(report_id, pdf_path)
    
    # Отправка PDF пользователю
    pdf_file = FSInputFile(pdf_path, filename="numerology_report.pdf")
    await bot.send_document(message.chat.id, pdf_file)
    
    # Предложение подписки
    await message.answer(
        "🌟 Хотите получать еженедельные нумерологические прогнозы?\n"
        "Оформите подписку всего за 299 ₽ в месяц!",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Оформить подписку", callback_data="subscribe")]
        ])
    )

async def process_compatibility_payment(message: Message, order: Dict[str, Any]):
    """Обрабатывает успешную оплату отчета о совместимости"""
    user_id = order["user_id"]
    payload = order.get("payload", {})
    report_id = payload.get("report_id")
    
    if not report_id:
        await message.answer("Произошла ошибка: не указан ID отчета.")
        return
    
    # Получение отчета
    report = await db.get_report(report_id)
    if not report:
        await message.answer("Произошла ошибка: отчет не найден.")
        return
    
    # Получение данных пользователя
    user = await db.get_user_by_id(user_id)
    if not user:
        await message.answer("Произошла ошибка: пользователь не найден.")
        return
    
    # Отправка уведомления пользователю
    await message.answer("✅ Оплата успешно получена! Генерирую отчет о совместимости...")
    
    # Отправка запроса на интерпретацию для отчета о совместимости
    interpretation = await send_to_n8n_for_interpretation(report["core_json"], "compatibility")
    
    # Генерация PDF
    pdf_path = generate_pdf(user, report["core_json"], interpretation.get("compatibility_report", {}), "compatibility")
    
    if not pdf_path:
        await message.answer("Произошла ошибка при генерации PDF. Пожалуйста, обратитесь в поддержку.")
        return
    
    # Обновление URL PDF в БД
    await db.update_report_pdf(report_id, pdf_path)
    
    # Отправка PDF пользователю
    pdf_file = FSInputFile(pdf_path, filename="compatibility_report.pdf")
    await bot.send_document(message.chat.id, pdf_file)
    
    # Предложение подписки
    await message.answer(
        "🌟 Хотите получать еженедельные нумерологические прогнозы?\n"
        "Оформите подписку всего за 299 ₽ в месяц!",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Оформить подписку", callback_data="subscribe")]
        ])
    )

async def process_subscription_payment(message: Message, order: Dict[str, Any]):
    """Обрабатывает успешную оплату подписки"""
    user_id = order["user_id"]
    
    # Получение данных пользователя
    user = await db.get_user_by_id(user_id)
    if not user:
        await message.answer("Произошла ошибка: пользователь не найден.")
        return
    
    # Создание или обновление записи о подписке
    subscription = await db.get_user_subscription(user_id)
    
    if subscription and subscription["status"] in ["active", "trial"]:
        # Если подписка уже активна, продлеваем срок
        await db.update_subscription_status(subscription["id"], "active")
        
        await message.answer(
            "✅ Ваша подписка успешно продлена на 1 месяц!\n\n"
            "Вы будете получать еженедельные нумерологические прогнозы.\n"
            "Управление подпиской доступно через команду /subscribe."
        )
    else:
        # Создаем новую подписку
        subscription_id = await db.create_subscription(user_id, "active")
        
        if subscription_id:
            await message.answer(
                "✅ Подписка успешно оформлена!\n\n"
                "Вы будете получать еженедельные нумерологические прогнозы в течение 1 месяца.\n"
                "Управление подпиской доступно через команду /subscribe."
            )
        else:
            await message.answer(
                "Произошла ошибка при активации подписки. Пожалуйста, обратитесь в поддержку."
            )

# Обработчик команды /report
@router.message(Command("report"))
async def cmd_report(message: Message):
    user_id = message.from_user.id
    
    # Проверка наличия пользователя в БД
    user = await db.get_user_by_tg_id(user_id)
    if not user:
        await message.answer("Для начала работы с ботом отправьте команду /start")
        return
    
    # Получение последнего отчета пользователя
    report = await db.get_latest_user_report(user_id, "full")
    
    if not report or not report.get("pdf_url"):
        # Проверяем наличие отчета о совместимости
        report = await db.get_latest_user_report(user_id, "compatibility")
        
        if not report or not report.get("pdf_url"):
            await message.answer(
                "У вас еще нет купленных отчетов. Воспользуйтесь командой /start для создания расчета."
            )
            return
    
    # Отправка PDF пользователю
    pdf_path = report.get("pdf_url")
    report_type = "отчет о совместимости" if report.get("report_type") == "compatibility" else "полный нумерологический отчет"
    
    await message.answer(f"Отправляю ваш последний {report_type}...")
    
    pdf_file = FSInputFile(pdf_path, filename=f"{report_type}.pdf")
    await bot.send_document(message.chat.id, pdf_file)

# Обработчик команды /subscribe (управление подпиской)
@router.message(Command("subscribe"))
async def cmd_subscribe(message: Message):
    user_id = message.from_user.id
    
    # Проверка наличия пользователя в БД
    user = await db.get_user_by_tg_id(user_id)
    if not user:
        await message.answer("Для начала работы с ботом отправьте команду /start")
        return
    
    # Получение текущей подписки
    subscription = await db.get_user_subscription(user_id)
    
    if not subscription:
        # Если нет подписки, предлагаем оформить
        buttons = [
            [InlineKeyboardButton(text="Оформить подписку", callback_data="subscribe")]
        ]
        
        # В тестовом режиме добавляем кнопку для бесплатной тестовой подписки
        if TEST_MODE:
            buttons.append([
                InlineKeyboardButton(
                    text="Активировать бесплатно (тестовый режим)", 
                    callback_data="test_subscribe"
                )
            ])
        
        await message.answer(
            "У вас нет активной подписки на еженедельные прогнозы.\n\n"
            "Стоимость подписки - 299 ₽ в месяц.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
        )
    else:
        # Если подписка есть, показываем её статус
        status = subscription["status"]
        buttons = []
        
        if status == "active":
            next_charge = subscription.get("next_charge")
            next_charge_str = next_charge.strftime("%d.%m.%Y") if next_charge else "неизвестно"
            
            await message.answer(
                f"У вас активная подписка на еженедельные прогнозы.\n\n"
                f"Следующее списание: {next_charge_str}\n"
                f"Стоимость: 299 ₽ в месяц.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="Отменить подписку", callback_data="cancel_subscription")]
                ])
            )
        elif status == "trial":
            trial_end = subscription.get("trial_end")
            trial_end_str = trial_end.strftime("%d.%m.%Y") if trial_end else "неизвестно"
            
            buttons = [
                [InlineKeyboardButton(text="Оформить полную подписку", callback_data="subscribe")]
            ]
            
            await message.answer(
                f"У вас активна пробная подписка на еженедельные прогнозы.\n\n"
                f"Срок действия: до {trial_end_str}\n\n"
                f"После окончания пробного периода подписка будет отключена.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
            )
        elif status == "canceled":
            buttons = [
                [InlineKeyboardButton(text="Возобновить подписку", callback_data="subscribe")]
            ]
            
            # В тестовом режиме добавляем кнопку для бесплатной тестовой подписки
            if TEST_MODE:
                buttons.append([
                    InlineKeyboardButton(
                        text="Активировать бесплатно (тестовый режим)", 
                        callback_data="test_subscribe"
                    )
                ])
            
            await message.answer(
                "Ваша подписка на еженедельные прогнозы отменена.\n\n"
                "Вы можете возобновить её в любой момент.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
            )

# Обработчик кнопки "Отменить подписку"
@router.callback_query(lambda c: c.data == "cancel_subscription")
async def process_cancel_subscription(callback_query: types.CallbackQuery):
    # Подтверждение запроса
    await callback_query.answer()
    
    user_id = callback_query.from_user.id
    
    # Получение текущей подписки
    subscription = await db.get_user_subscription(user_id)
    
    if not subscription or subscription["status"] != "active":
        await callback_query.message.answer("У вас нет активной подписки для отмены.")
        return
    
    # Обновление статуса подписки
    result = await db.update_subscription_status(subscription["id"], "canceled")
    
    if result:
        await callback_query.message.answer(
            "✅ Ваша подписка успешно отменена.\n\n"
            "Вы больше не будете получать еженедельные прогнозы.\n"
            "Возобновить подписку можно в любой момент через команду /subscribe."
        )
    else:
        await callback_query.message.answer(
            "Произошла ошибка при отмене подписки. Пожалуйста, попробуйте позже."
        )

# Обработчик команды /compatibility
@router.message(Command("compatibility"))
async def cmd_compatibility(message: Message, state: FSMContext):
    user_id = message.from_user.id
    
    # Проверка наличия пользователя в БД
    user = await db.get_user_by_tg_id(user_id)
    if not user:
        await message.answer("Для начала работы с ботом отправьте команду /start")
        return
    
    # Проверка наличия данных пользователя
    if not user.get("birthdate") or not user.get("fio"):
        await message.answer(
            "Для расчета совместимости необходимо сначала ввести свои данные.\n"
            "Отправьте команду /start и следуйте инструкциям."
        )
        return
    
    # Запрос даты рождения партнера
    await message.answer(
        "Давайте рассчитаем вашу совместимость с другим человеком.\n\n"
        "Введите дату рождения партнера в формате ДД.ММ.ГГГГ (например, 01.01.1990)"
    )
    
    # Сохранение данных пользователя
    await state.update_data(
        user_birthdate=user.get("birthdate"),
        user_fio=user.get("fio")
    )
    
    # Установка состояния ожидания даты рождения партнера
    await state.set_state(UserStates.waiting_for_partner_birthdate)

# Обработчик ввода даты рождения партнера
@router.message(UserStates.waiting_for_partner_birthdate)
async def process_partner_birthdate(message: Message, state: FSMContext):
    try:
        partner_birthdate = datetime.strptime(message.text, "%d.%m.%Y").date()
        await state.update_data(partner_birthdate=partner_birthdate.strftime("%Y-%m-%d"))
        
        # Запрос ФИО партнера
        await message.answer("Спасибо! Теперь введите полное ФИО партнера")
        
        # Установка состояния ожидания ФИО партнера
        await state.set_state(UserStates.waiting_for_partner_name)
    except ValueError:
        await message.answer(
            "Неверный формат даты. Пожалуйста, введите дату в формате ДД.ММ.ГГГГ (например, 01.01.1990)"
        )

# Обработчик ввода ФИО партнера
@router.message(UserStates.waiting_for_partner_name)
async def process_partner_name(message: Message, state: FSMContext):
    # Сохранение ФИО партнера
    await state.update_data(partner_fio=message.text)
    
    # Получение всех данных
    data = await state.get_data()
    user_birthdate = data.get("user_birthdate")
    user_fio = data.get("user_fio")
    partner_birthdate = data.get("partner_birthdate")
    partner_fio = data.get("partner_fio")
    
    # Выполнение расчета совместимости
    compatibility_results = calculate_compatibility(
        user_birthdate, user_fio,
        partner_birthdate, partner_fio
    )
    
    # Сохранение результатов в БД
    report_id = await db.save_report(message.from_user.id, "compatibility_mini", compatibility_results)
    
    # Отправка результатов на интерпретацию через n8n
    interpretation = await send_to_n8n_for_interpretation(compatibility_results, "compatibility_mini")
    
    # Формирование и отправка мини-отчета о совместимости
    compatibility_score = compatibility_results.get("compatibility", {}).get("total", 0)
    score_percent = int(compatibility_score * 10)  # преобразуем оценку из 10 в проценты
    
    mini_report_text = interpretation.get(
        'compatibility_mini_report', 
        f"Ваша совместимость с {partner_fio}: {score_percent}%"
    )
    
    buttons = [
        [InlineKeyboardButton(
            text="Полный отчет о совместимости - 199 ₽", 
            callback_data=f"buy_compatibility:{report_id}"
        )]
    ]
    
    # В тестовом режиме добавляем кнопку "Получить бесплатно (тестовый режим)"
    if TEST_MODE:
        buttons.append([
            InlineKeyboardButton(
                text="Получить бесплатно (тестовый режим)", 
                callback_data=f"test_compatibility:{report_id}"
            )
        ])
    
    await message.answer(
        f"{mini_report_text}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )
    
    # Сброс состояния FSM
    await state.clear()

# Обработчик кнопки "Получить бесплатно (тестовый режим)" для отчета о совместимости
@router.callback_query(lambda c: c.data and c.data.startswith("test_compatibility:"))
async def process_test_compatibility(callback_query: types.CallbackQuery):
    if not TEST_MODE:
        await callback_query.answer("Тестовый режим отключен")
        return
        
    # Подтверждение запроса
    await callback_query.answer()
    
    # Получение ID отчета из callback_data
    report_id = int(callback_query.data.split(":")[1])
    
    # Получение отчета
    report = await db.get_report(report_id)
    
    if not report:
        await callback_query.message.answer("Отчет не найден. Пожалуйста, создайте новый расчет.")
        return
        
    # Получение данных пользователя
    user_id = report["user_id"]
    user = await db.get_user_by_id(user_id)
    
    if not user:
        await callback_query.message.answer("Произошла ошибка: пользователь не найден.")
        return
        
    # Отправка запроса на интерпретацию для полного отчета о совместимости
    interpretation = await send_to_n8n_for_interpretation(report["core_json"], "compatibility")
    
    # Временно помечаем пользователя о генерации отчета
    await callback_query.message.answer("⏳ Генерация отчета о совместимости... Пожалуйста, подождите.")
    
    # Генерация PDF
    pdf_path = generate_pdf(user, report["core_json"], interpretation.get("compatibility_report", {}), "compatibility")
    
    if not pdf_path:
        await callback_query.message.answer("Произошла ошибка при генерации PDF. Пожалуйста, попробуйте позже.")
        return
        
    # Обновление URL PDF в БД
    await db.update_report_pdf(report_id, pdf_path)
    
    # Отправка PDF пользователю
    await callback_query.message.answer("✅ Ваш отчет о совместимости готов (тестовый режим).")
    
    # Скачивание PDF и отправка пользователю
    pdf_file = FSInputFile(pdf_path, filename="compatibility_report.pdf")
    await bot.send_document(callback_query.message.chat.id, pdf_file)

# Обработчик кнопки "Полный отчет о совместимости - 199 ₽"
@router.callback_query(lambda c: c.data and c.data.startswith("buy_compatibility:"))
async def process_buy_compatibility(callback_query: types.CallbackQuery):
    # Подтверждение запроса
    await callback_query.answer()
    
    # Проверка на тестовый режим
    if TEST_MODE or not PAYMENT_TOKEN:
        await callback_query.message.answer(
            "⚠️ Платежная система не настроена или бот работает в тестовом режиме.\n"
            "Для тестирования используйте кнопку \"Получить бесплатно (тестовый режим)\"."
        )
        return
    
    # Получение ID отчета из callback_data
    report_id = int(callback_query.data.split(":")[1])
    
    # Получение отчета
    report = await db.get_report(report_id)
    
    if not report:
        await callback_query.message.answer("Отчет не найден. Пожалуйста, создайте новый расчет.")
        return
    
    # Получение данных пользователя
    user_id = report["user_id"]
    
    # Создание заказа в БД
    order_id = await db.create_order(
        user_id,
        product="compatibility",
        price=199.0,
        currency="RUB",
        payload={"type": "compatibility", "report_id": report_id}
    )
    
    if not order_id:
        await callback_query.message.answer("Произошла ошибка при создании заказа.")
        return
    
    # Создание платежного инвойса
    await bot.send_invoice(
        chat_id=callback_query.message.chat.id,
        title="Отчет о совместимости",
        description="Полный анализ нумерологической совместимости с партнером",
        payload=f"compatibility:{order_id}",
        provider_token=PAYMENT_TOKEN,
        currency="RUB",
        prices=[LabeledPrice(label="Отчет о совместимости", amount=19900)],  # в копейках
        max_tip_amount=5000,
        suggested_tip_amounts=[2000, 5000],
        start_parameter="compatibility",
        provider_data=None,
        photo_url="https://example.com/compatibility.jpg",
        photo_size=512,
        photo_width=512,
        photo_height=512,
        need_name=False,
        need_phone_number=False,
        need_email=False,
        need_shipping_address=False,
        send_phone_number_to_provider=False,
        send_email_to_provider=False,
        is_flexible=False,
        disable_notification=False,
        protect_content=False,
        reply_to_message_id=None,
        allow_sending_without_reply=True,
        reply_markup=None,
        request_timeout=15
    )

# Обработчик кнопки "Полный PDF - 149 ₽"
@router.callback_query(lambda c: c.data and c.data.startswith("buy_full_report:"))
async def process_buy_full_report(callback_query: types.CallbackQuery):
    # Подтверждение запроса
    await callback_query.answer()
    
    # Проверка на тестовый режим
    if TEST_MODE or not PAYMENT_TOKEN:
        await callback_query.message.answer(
            "⚠️ Платежная система не настроена или бот работает в тестовом режиме.\n"
            "Для тестирования используйте кнопку \"Получить бесплатно (тестовый режим)\"."
        )
        return
    
    # Получение ID отчета из callback_data
    report_id = int(callback_query.data.split(":")[1])
    
    # Получение отчета
    report = await db.get_report(report_id)
    
    if not report:
        await callback_query.message.answer("Отчет не найден. Пожалуйста, создайте новый расчет.")
        return
    
    # Получение данных пользователя
    user_id = report["user_id"]
    
    # Создание заказа в БД
    order_id = await db.create_order(
        user_id,
        product="full_report",
        price=149.0,
        currency="RUB",
        payload={"type": "full_report", "report_id": report_id}
    )
    
    if not order_id:
        await callback_query.message.answer("Произошла ошибка при создании заказа.")
        return
    
    # Создание платежного инвойса
    await bot.send_invoice(
        chat_id=callback_query.message.chat.id,
        title="Полный нумерологический отчет",
        description="Детальный анализ вашего нумерологического портрета с рекомендациями",
        payload=f"full_report:{order_id}",
        provider_token=PAYMENT_TOKEN,
        currency="RUB",
        prices=[LabeledPrice(label="Полный PDF-отчет", amount=14900)],  # в копейках
        max_tip_amount=5000,
        suggested_tip_amounts=[1000, 3000, 5000],
        start_parameter="full_report",
        provider_data=None,
        photo_url="https://example.com/full_report.jpg",
        photo_size=512,
        photo_width=512,
        photo_height=512,
        need_name=False,
        need_phone_number=False,
        need_email=False,
        need_shipping_address=False,
        send_phone_number_to_provider=False,
        send_email_to_provider=False,
        is_flexible=False,
        disable_notification=False,
        protect_content=False,
        reply_to_message_id=None,
        allow_sending_without_reply=True,
        reply_markup=None,
        request_timeout=15
    )

# Обработчик команды /help
@router.message(Command("help"))
async def cmd_help(message: Message):
    help_text = (
        "🔮 ИИ-Нумеролог - ваш персональный нумерологический консультант\n\n"
        "Доступные команды:\n"
        "/start - Начать расчет нумерологического портрета\n"
        "/report - Получить последний купленный отчет\n"
        "/compatibility - Рассчитать совместимость с партнером\n"
        "/subscribe - Управление подпиской на еженедельные прогнозы\n"
        "/settings - Настройки языка и уведомлений\n"
        "/help - Справка и информация о боте\n\n"
        
        "📊 Доступные услуги:\n"
        "🔸 Бесплатный мини-отчет - базовый анализ вашего нумерологического портрета\n"
        "🔸 Полный PDF-отчет (149 ₽) - детальный анализ с рекомендациями\n"
        "🔸 Анализ совместимости (199 ₽) - расчет нумерологической совместимости с партнером\n"
        "🔸 Подписка на еженедельные прогнозы (299 ₽/месяц) - персональные нумерологические прогнозы каждую неделю\n\n"
        
        "По всем вопросам обращайтесь к администратору: @admin_username"
    )
    
    await message.answer(help_text)

# Обработчик команды /settings
@router.message(Command("settings"))
async def cmd_settings(message: Message):
    user_id = message.from_user.id
    
    # Проверка наличия пользователя в БД
    user = await db.get_user_by_tg_id(user_id)
    if not user:
        await message.answer("Для начала работы с ботом отправьте команду /start")
        return
    
    # Получение текущих настроек
    current_lang = user.get("lang", "ru")
    push_enabled = user.get("push_enabled", True)
    
    # Формирование клавиатуры с настройками
    lang_text = "🇷🇺 Русский" if current_lang == "ru" else "🇬🇧 English"
    push_text = "Включены ✅" if push_enabled else "Отключены ❌"
    
    settings_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"Язык: {lang_text}", callback_data="toggle_lang")],
        [InlineKeyboardButton(text=f"Уведомления: {push_text}", callback_data="toggle_push")]
    ])
    
    await message.answer(
        "⚙️ Настройки\n\n"
        f"Текущий язык: {lang_text}\n"
        f"Уведомления: {push_text}",
        reply_markup=settings_keyboard
    )

# Обработчик кнопки переключения языка
@router.callback_query(lambda c: c.data == "toggle_lang")
async def toggle_lang(callback_query: types.CallbackQuery):
    # Подтверждение запроса
    await callback_query.answer()
    
    user_id = callback_query.from_user.id
    
    # Получение текущих настроек
    user = await db.get_user_by_tg_id(user_id)
    if not user:
        await callback_query.message.answer("Для начала работы с ботом отправьте команду /start")
        return
    
    current_lang = user.get("lang", "ru")
    new_lang = "en" if current_lang == "ru" else "ru"
    
    # Обновление настроек в БД
    result = await db.update_user_settings(user_id, lang=new_lang)
    
    if result:
        # Обновление сообщения с настройками
        push_enabled = user.get("push_enabled", True)
        lang_text = "🇷🇺 Русский" if new_lang == "ru" else "🇬🇧 English"
        push_text = "Включены ✅" if push_enabled else "Отключены ❌"
        
        settings_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"Язык: {lang_text}", callback_data="toggle_lang")],
            [InlineKeyboardButton(text=f"Уведомления: {push_text}", callback_data="toggle_push")]
        ])
        
        await callback_query.message.edit_text(
            "⚙️ Настройки\n\n"
            f"Текущий язык: {lang_text}\n"
            f"Уведомления: {push_text}",
            reply_markup=settings_keyboard
        )
    else:
        await callback_query.message.answer("Произошла ошибка при обновлении настроек.")

# Обработчик кнопки переключения уведомлений
@router.callback_query(lambda c: c.data == "toggle_push")
async def toggle_push(callback_query: types.CallbackQuery):
    # Подтверждение запроса
    await callback_query.answer()
    
    user_id = callback_query.from_user.id
    
    # Получение текущих настроек
    user = await db.get_user_by_tg_id(user_id)
    if not user:
        await callback_query.message.answer("Для начала работы с ботом отправьте команду /start")
        return
    
    current_push = user.get("push_enabled", True)
    new_push = not current_push
    
    # Обновление настроек в БД
    result = await db.update_user_settings(user_id, push_enabled=new_push)
    
    if result:
        # Обновление сообщения с настройками
        current_lang = user.get("lang", "ru")
        lang_text = "🇷🇺 Русский" if current_lang == "ru" else "🇬🇧 English"
        push_text = "Включены ✅" if new_push else "Отключены ❌"
        
        settings_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"Язык: {lang_text}", callback_data="toggle_lang")],
            [InlineKeyboardButton(text=f"Уведомления: {push_text}", callback_data="toggle_push")]
        ])
        
        await callback_query.message.edit_text(
            "⚙️ Настройки\n\n"
            f"Текущий язык: {lang_text}\n"
            f"Уведомления: {push_text}",
            reply_markup=settings_keyboard
        )
    else:
        await callback_query.message.answer("Произошла ошибка при обновлении настроек.")

# Обработчик неизвестных команд
@router.message(Command())
async def unknown_command(message: Message):
    await message.answer(
        "Неизвестная команда. Введите /help для получения списка доступных команд."
    )

# Обработчик простых сообщений (не команд)
@router.message()
async def process_message(message: Message):
    await message.answer(
        "Для взаимодействия с ботом используйте команды или кнопки меню.\n"
        "Введите /help для получения списка доступных команд."
    )

# Функция для настройки и запуска вебхука (при необходимости)
async def on_startup(app):
    # Инициализация базы данных
    await db.init()
    
    # Установка вебхука, если настроен
    if WEBHOOK_HOST:
        await bot.set_webhook(url=WEBHOOK_URL)
        logger.info(f"Webhook set to {WEBHOOK_URL}")

# Функция для остановки приложения
async def on_shutdown(app):
    # Закрытие соединения с базой данных
    if hasattr(db, 'pool') and db.pool:
        await db.pool.close()
    
    # Удаление вебхука при выключении
    await bot.delete_webhook()

# Функция для запуска бота (polling или webhook)
async def main():
    # Инициализация базы данных
    await db.init()
    
    # Запуск бота в режиме long polling или webhook
    if WEBHOOK_HOST:
        # Настройка webhook
        app = web.Application()
        
        # Настройка endpoint для вебхука
        SimpleRequestHandler(
            dispatcher=dp,
            bot=bot,
        ).register(app, path=WEBHOOK_PATH)
        
        # Добавление обработчиков запуска и остановки
        app.on_startup.append(on_startup)
        app.on_shutdown.append(on_shutdown)
        
        # Запуск web сервера
        logger.info(f"Starting webhook on {WEBHOOK_HOST}{WEBHOOK_PATH}")
        web.run_app(app, host="0.0.0.0", port=8443)
    else:
        # Запуск в режиме long polling
        logger.info("Starting bot in long polling mode")
        await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())