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
PAYMENT_TOKEN = os.getenv("PAYMENT_TOKEN")
WEBHOOK_HOST = os.getenv("WEBHOOK_HOST")
WEBHOOK_PATH = os.getenv("WEBHOOK_PATH", "/webhook")
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
storage = RedisStorage.from_url('redis://redis:6379/0')
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
    await message.answer(
        f"Ваш мини-отчет:\n\n{interpretation['mini_report']}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Полный PDF - 149 ₽", callback_data=f"buy_full_report:{report_id}")]
        ])
    )
    
    # Сброс состояния FSM
    await state.clear()

# Обработчик кнопки "Полный PDF - 149 ₽"
@router.callback_query(lambda c: c.data and c.data.startswith("buy_full_report:"))
async def process_buy_full_report(callback_query: types.CallbackQuery):
    # Подтверждение запроса
    await callback_query.answer()
    
    # Получение ID отчета из callback_data
    report_id = int(callback_query.data.split(":")[1])
    
    # Создание заказа в БД
    order_id = await db.create_order(
        callback_query.from_user.id, 
        "full_report", 
        149.0, 
        "RUB",
        {"report_id": report_id}
    )
    
    # Создание инвойса для оплаты
    await bot.send_invoice(
        chat_id=callback_query.from_user.id,
        title="Полный нумерологический отчет",
        description="Детальный анализ вашего нумерологического портрета с рекомендациями",
        payload=f"order:{order_id}",
        provider_token=PAYMENT_TOKEN,
        currency="RUB",
        prices=[LabeledPrice(label="Отчет", amount=14900)],  # В копейках
        protect_content=True
    )

# Обработчик pre-checkout запроса
@router.pre_checkout_query()
async def process_pre_checkout_query(pre_checkout_query: PreCheckoutQuery):
    # Подтверждение возможности оплаты
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

# Обработчик успешной оплаты
@router.message(lambda message: message.successful_payment is not None)
async def process_successful_payment(message: Message):
    # Получение информации о платеже
    payment = message.successful_payment
    order_id = int(payment.invoice_payload.split(":")[1])
    
    # Обновление статуса заказа в БД
    await db.update_order_status(order_id, "paid")
    
    # Получение данных заказа
    order = await db.get_order(order_id)
    report_id = order["payload"]["report_id"]
    
    # Получение отчета
    report = await db.get_report(report_id)
    
    # Получение данных пользователя
    user = await db.get_user_by_id(order["user_id"])
    
    # Отправка запроса на интерпретацию для полного отчета
    interpretation = await send_to_n8n_for_interpretation(report["core_json"], "full")
    
    # Генерация PDF
    pdf_url = await generate_pdf(user, report["core_json"], interpretation["full_report"])
    
    # Обновление URL PDF в БД
    await db.update_report_pdf(report_id, pdf_url)
    
    # Отправка PDF пользователю
    await message.answer("Спасибо за оплату! Ваш полный отчет готов.")
    
    # Скачивание PDF и отправка пользователю
    pdf_file = FSInputFile(pdf_url, filename="numerology_report.pdf")
    await bot.send_document(message.chat.id, pdf_file)
    
    # Предложение подписки
    await message.answer(
        "Хотите получать еженедельные нумерологические прогнозы?",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Оформить подписку", callback_data="subscribe")]
        ])
    )

# Обработчик команды /report
@router.message(Command("report"))
async def cmd_report(message: Message):
    user_id = message.from_user.id
    
    # Получение последнего полного отчета пользователя
    report = await db.get_latest_user_report(user_id, "full")
    
    if report:
        # Отправка PDF пользователю
        pdf_file = FSInputFile(report["pdf_url"], filename="numerology_report.pdf")
        await bot.send_document(message.chat.id, pdf_file)
    else:
        await message.answer(
            "У вас пока нет полных отчетов. Хотите сделать расчет?",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Сделать расчёт", callback_data="start_calculation")]
            ])
        )

# Обработчик команды /subscribe
@router.message(Command("subscribe"))
async def cmd_subscribe(message: Message):
    user_id = message.from_user.id
    
    # Получение статуса подписки пользователя
    subscription = await db.get_user_subscription(user_id)
    
    if subscription:
        status = subscription["status"]
        if status == "active":
            next_charge = subscription["next_charge"]
            await message.answer(
                f"У вас активная подписка. Следующее списание: {next_charge}",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="Отменить подписку", callback_data="cancel_subscription")]
                ])
            )
        elif status == "canceled":
            await message.answer(
                "Ваша подписка отменена. Хотите возобновить?",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="Возобновить подписку", callback_data="resume_subscription")]
                ])
            )
        elif status == "trial":
            trial_end = subscription["trial_end"]
            await message.answer(
                f"У вас пробная подписка до {trial_end}. После этого будет списание 299 ₽/месяц.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="Отменить пробный период", callback_data="cancel_subscription")]
                ])
            )
    else:
        await message.answer(
            "У вас нет активной подписки. Стоимость подписки - 299 ₽/месяц. Получайте еженедельные нумерологические прогнозы!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Оформить подписку", callback_data="subscribe")]
            ])
        )

# Обработчик кнопки "Оформить подписку"
@router.callback_query(lambda c: c.data == "subscribe")
async def process_subscribe_button(callback_query: types.CallbackQuery):
    # Подтверждение запроса
    await callback_query.answer()
    
    # Создание заказа в БД
    order_id = await db.create_order(
        callback_query.from_user.id, 
        "subscription_month", 
        299.0, 
        "RUB",
        {}
    )
    
    # Создание инвойса для оплаты
    await bot.send_invoice(
        chat_id=callback_query.from_user.id,
        title="Подписка на нумерологические прогнозы",
        description="Еженедельные нумерологические прогнозы на месяц",
        payload=f"subscription:{order_id}",
        provider_token=PAYMENT_TOKEN,
        currency="RUB",
        prices=[LabeledPrice(label="Подписка на месяц", amount=29900)],  # В копейках
        protect_content=True
    )

# Обработчик команды /compatibility
@router.message(Command("compatibility"))
async def cmd_compatibility(message: Message, state: FSMContext):
    # Запрос даты рождения партнера
    await message.answer(
        "Рассчитаем вашу совместимость с партнером. Пожалуйста, введите дату рождения партнера в формате ДД.ММ.ГГГГ"
    )
    
    # Установка состояния ожидания даты рождения партнера
    await state.set_state(UserStates.waiting_for_partner_birthdate)

# Обработчик ввода даты рождения партнера
@router.message(UserStates.waiting_for_partner_birthdate)
async def process_partner_birthdate(message: Message, state: FSMContext):
    # Сохранение даты рождения партнера в контексте FSM
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
    # Сохранение ФИО партнера в контексте FSM
    await state.update_data(partner_fio=message.text)
    
    # Получение данных из контекста
    user_data = await state.get_data()
    partner_birthdate = user_data.get("partner_birthdate")
    partner_fio = user_data.get("partner_fio")
    
    # Получение данных пользователя из БД
    user = await db.get_user_by_tg_id(message.from_user.id)
    
    # Выполнение расчета совместимости
    compatibility_results = calculate_compatibility(
        user["birthdate"], user["fio"],
        partner_birthdate, partner_fio
    )
    
    # Сохранение результатов в БД
    report_id = await db.save_report(message.from_user.id, "compatibility", compatibility_results)
    
    # Отправка результатов на интерпретацию через n8n
    interpretation = await send_to_n8n_for_interpretation(compatibility_results, "compatibility_mini")
    
    # Формирование и отправка мини-отчета о совместимости
    await message.answer(
        f"Мини-отчет о совместимости:\n\n{interpretation['compatibility_mini_report']}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Полный отчет о совместимости - 249 ₽", callback_data=f"buy_compatibility:{report_id}")]
        ])
    )
    
    # Сброс состояния FSM
    await state.clear()

# Обработчик кнопки "Полный отчет о совместимости"
@router.callback_query(lambda c: c.data and c.data.startswith("buy_compatibility:"))
async def process_buy_compatibility(callback_query: types.CallbackQuery):
    # Подтверждение запроса
    await callback_query.answer()
    
    # Получение ID отчета из callback_data
    report_id = int(callback_query.data.split(":")[1])
    
    # Создание заказа в БД
    order_id = await db.create_order(
        callback_query.from_user.id, 
        "compatibility", 
        249.0, 
        "RUB",
        {"report_id": report_id}
    )
    
    # Создание инвойса для оплаты
    await bot.send_invoice(
        chat_id=callback_query.from_user.id,
        title="Полный отчет о совместимости",
        description="Детальный анализ совместимости с рекомендациями",
        payload=f"compatibility:{order_id}",
        provider_token=PAYMENT_TOKEN,
        currency="RUB",
        prices=[LabeledPrice(label="Отчет о совместимости", amount=24900)],  # В копейках
        protect_content=True
    )

# Обработчик команды /help
@router.message(Command("help"))
async def cmd_help(message: Message):
    help_text = """
🔮 *ИИ-Нумеролог* - ваш персональный нумерологический консультант!

*Доступные команды:*
/start - начать работу с ботом
/report - получить последний купленный отчет
/subscribe - управление подпиской
/compatibility - рассчитать совместимость
/help - справка по боту
/settings - настройки языка и уведомлений

*Тарифы:*
• Мини-отчет - бесплатно
• Полный PDF-отчет - 149 ₽
• Отчет о совместимости - 249 ₽
• Подписка на еженедельные прогнозы - 299 ₽/месяц

По вопросам и предложениям: @support_numerology
    """
    await message.answer(help_text, parse_mode=ParseMode.MARKDOWN)

# Обработчик команды /settings
@router.message(Command("settings"))
async def cmd_settings(message: Message):
    # Получение текущих настроек пользователя
    user = await db.get_user_by_tg_id(message.from_user.id)
    
    # Формирование кнопок для выбора языка
    lang_buttons = []
    for lang_code, lang_name in [("ru", "Русский"), ("en", "English")]:
        text = f"✓ {lang_name}" if user["lang"] == lang_code else lang_name
        lang_buttons.append(InlineKeyboardButton(text=text, callback_data=f"set_lang:{lang_code}"))
    
    # Формирование кнопки для переключения уведомлений
    push_status = "Выключить" if user["push_enabled"] else "Включить"
    push_action = "disable" if user["push_enabled"] else "enable"
    
    # Создание клавиатуры
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        lang_buttons,
        [InlineKeyboardButton(text=f"{push_status} уведомления", callback_data=f"push:{push_action}")]
    ])
    
    await message.answer(
        "Настройки:\n\nВыберите язык и настройки уведомлений:",
        reply_markup=keyboard
    )

# Функция для настройки вебхуков
async def on_startup(app):
    # Установка вебхука
    await bot.set_webhook(url=WEBHOOK_URL)
    
    # Дополнительная инициализация
    await db.init()
    
    logger.info("Бот запущен и вебхук установлен")

# Основная функция запуска бота
def main():
    # Создание приложения aiohttp
    app = web.Application()
    
    # Настройка обработчика вебхуков для бота
    webhook_requests_handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
    )
    webhook_requests_handler.register(app, path=WEBHOOK_PATH)
    
    # Настройка обработчика платежных вебхуков
    app.router.add_post("/payment", lambda request: handle_payment_webhook(request, db))
    
    # Настройка функции запуска
    app.on_startup.append(on_startup)
    
    # Запуск приложения
    web.run_app(app, host="0.0.0.0", port=8000)

if __name__ == "__main__":
    main()