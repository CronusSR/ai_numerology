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