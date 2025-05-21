# database_sqlite.py - замена PostgreSQL на SQLite
import os
import json
import sqlite3
import asyncio
from datetime import datetime, date, timedelta
from typing import Dict, Any, List, Optional, Union

class Database:
    def __init__(self):
        self.db_file = "numerology_bot.db"
        self.connection = None
        
        async def close(self):
            """Закрывает соединение с базой данных"""
            if self.connection:
                self.connection.close()
                self.connection = None
            return True
        return False
        
    async def init(self):
        """Инициализация соединения с базой данных"""
        # SQLite подключение (синхронное, но мы обернем его в асинхронные функции)
        self.connection = sqlite3.connect(self.db_file)
        self.connection.row_factory = sqlite3.Row
        
        # Создаем таблицы если они не существуют
        await self._create_tables_if_not_exist()
        return True
    
    async def _create_tables_if_not_exist(self):
        """Создает таблицы, если они не существуют"""
        cursor = self.connection.cursor()
        
        # Создаем таблицу users
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tg_id INTEGER UNIQUE,
                fio TEXT,
                birthdate DATE,
                lang TEXT DEFAULT 'ru',
                push_enabled INTEGER DEFAULT 1,
                state TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Создаем таблицу orders
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                product TEXT,
                price REAL,
                currency TEXT,
                status TEXT,
                paid_at TIMESTAMP,
                payload TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Создаем таблицу reports
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                report_type TEXT,
                core_json TEXT,
                pdf_url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        # Создаем таблицу subscriptions
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                status TEXT,
                trial_end DATE,
                next_charge DATE,
                provider_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
        
        self.connection.commit()
    
    async def get_user_by_tg_id(self, tg_id: int) -> Optional[Dict[str, Any]]:
        """Получает пользователя по идентификатору Telegram"""
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM users WHERE tg_id = ?", (tg_id,))
        row = cursor.fetchone()
        
        if row:
            return dict(row)
        return None
    
    async def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Получает пользователя по ID в базе данных"""
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        
        if row:
            return dict(row)
        return None
    
    async def create_user(self, tg_id: int) -> int:
        """Создает нового пользователя"""
        cursor = self.connection.cursor()
        cursor.execute("INSERT INTO users (tg_id) VALUES (?)", (tg_id,))
        self.connection.commit()
        return cursor.lastrowid
    
    async def update_user(self, tg_id: int, fio: str, birthdate: str) -> bool:
        """Обновляет данные пользователя"""
        cursor = self.connection.cursor()
        cursor.execute(
            "UPDATE users SET fio = ?, birthdate = ? WHERE tg_id = ?",
            (fio, birthdate, tg_id)
        )
        self.connection.commit()
        return cursor.rowcount > 0
    
    async def update_user_settings(self, tg_id: int, lang: str = None, push_enabled: bool = None) -> bool:
        """Обновляет настройки пользователя"""
        query_parts = []
        params = []
        
        if lang is not None:
            query_parts.append("lang = ?")
            params.append(lang)
        
        if push_enabled is not None:
            query_parts.append("push_enabled = ?")
            params.append(1 if push_enabled else 0)
        
        if not query_parts:
            return False
        
        params.append(tg_id)
        
        cursor = self.connection.cursor()
        cursor.execute(
            f"UPDATE users SET {', '.join(query_parts)} WHERE tg_id = ?",
            params
        )
        self.connection.commit()
        return cursor.rowcount > 0
    
    async def save_report(self, user_id: int, report_type: str, core_json: Dict[str, Any]) -> int:
        """Сохраняет отчет в базу данных"""
        cursor = self.connection.cursor()
        
        # Проверяем, является ли user_id телеграм ID или ID в базе
        if isinstance(user_id, int) and user_id > 0:
            cursor.execute("SELECT id FROM users WHERE tg_id = ?", (user_id,))
            row = cursor.fetchone()
            if row:
                user_id = row[0]
        
        # Сохраняем отчет
        cursor.execute(
            "INSERT INTO reports (user_id, report_type, core_json) VALUES (?, ?, ?)",
            (user_id, report_type, json.dumps(core_json))
        )
        self.connection.commit()
        return cursor.lastrowid
    
    async def update_report_pdf(self, report_id: int, pdf_url: str) -> bool:
        """Обновляет URL PDF-отчета"""
        cursor = self.connection.cursor()
        cursor.execute(
            "UPDATE reports SET pdf_url = ? WHERE id = ?",
            (pdf_url, report_id)
        )
        self.connection.commit()
        return cursor.rowcount > 0
    
    async def get_report(self, report_id: int) -> Optional[Dict[str, Any]]:
        """Получает отчет по ID"""
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM reports WHERE id = ?", (report_id,))
        row = cursor.fetchone()
        
        if row:
            report = dict(row)
            # Парсим JSON из строки
            if report["core_json"]:
                report["core_json"] = json.loads(report["core_json"])
            return report
        return None
    
    async def get_latest_user_report(self, user_id: int, report_type: str) -> Optional[Dict[str, Any]]:
        """Получает последний отчет пользователя определенного типа"""
        cursor = self.connection.cursor()
        
        # Проверяем, является ли user_id телеграм ID или ID в базе
        if isinstance(user_id, int) and user_id > 0:
            cursor.execute("SELECT id FROM users WHERE tg_id = ?", (user_id,))
            row = cursor.fetchone()
            if row:
                user_id = row[0]
        
        cursor.execute(
            """
            SELECT * FROM reports 
            WHERE user_id = ? AND report_type = ? AND pdf_url IS NOT NULL
            ORDER BY created_at DESC 
            LIMIT 1
            """,
            (user_id, report_type)
        )
        row = cursor.fetchone()
        
        if row:
            report = dict(row)
            # Парсим JSON из строки
            if report["core_json"]:
                report["core_json"] = json.loads(report["core_json"])
            return report
        return None
    
    async def create_order(self, user_id: int, product: str, price: float, 
                          currency: str, payload: Dict[str, Any]) -> int:
        """Создает новый заказ"""
        cursor = self.connection.cursor()
        
        # Проверяем, является ли user_id телеграм ID или ID в базе
        if isinstance(user_id, int) and user_id > 0:
            cursor.execute("SELECT id FROM users WHERE tg_id = ?", (user_id,))
            row = cursor.fetchone()
            if row:
                user_id = row[0]
        
        # Создаем заказ
        cursor.execute(
            """
            INSERT INTO orders (user_id, product, price, currency, status, payload) 
            VALUES (?, ?, ?, ?, 'pending', ?)
            """,
            (user_id, product, price, currency, json.dumps(payload))
        )
        self.connection.commit()
        return cursor.lastrowid
    
    async def update_order_status(self, order_id: int, status: str) -> bool:
        """Обновляет статус заказа"""
        cursor = self.connection.cursor()
        paid_at = datetime.now().isoformat() if status == 'paid' else None
        
        cursor.execute(
            "UPDATE orders SET status = ?, paid_at = ? WHERE id = ?",
            (status, paid_at, order_id)
        )
        self.connection.commit()
        return cursor.rowcount > 0
    
    async def get_order(self, order_id: int) -> Optional[Dict[str, Any]]:
        """Получает заказ по ID"""
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
        row = cursor.fetchone()
        
        if row:
            order = dict(row)
            # Парсим JSON из строки
            if order["payload"]:
                order["payload"] = json.loads(order["payload"])
            return order
        return None
    
    async def get_user_subscription(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Получает подписку пользователя"""
        cursor = self.connection.cursor()
        
        # Проверяем, является ли user_id телеграм ID или ID в базе
        if isinstance(user_id, int) and user_id > 0:
            cursor.execute("SELECT id FROM users WHERE tg_id = ?", (user_id,))
            row = cursor.fetchone()
            if row:
                user_id = row[0]
        
        cursor.execute(
            "SELECT * FROM subscriptions WHERE user_id = ? ORDER BY created_at DESC LIMIT 1",
            (user_id,)
        )
        row = cursor.fetchone()
        
        if row:
            return dict(row)
        return None
    
    async def create_subscription(self, user_id: int, status: str, provider_id: str = None) -> int:
        """Создает новую подписку"""
        cursor = self.connection.cursor()
        
        # Проверяем, является ли user_id телеграм ID или ID в базе
        if isinstance(user_id, int) and user_id > 0:
            cursor.execute("SELECT id FROM users WHERE tg_id = ?", (user_id,))
            row = cursor.fetchone()
            if row:
                user_id = row[0]
        
        # Устанавливаем даты для подписки
        now = datetime.now().date()
        trial_end = (now + timedelta(days=7)).isoformat() if status == "trial" else None
        next_charge = (now + timedelta(days=30)).isoformat() if status in ["active", "trial"] else None
        
        # Создаем подписку
        cursor.execute(
            """
            INSERT INTO subscriptions (user_id, status, trial_end, next_charge, provider_id, updated_at) 
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (user_id, status, trial_end, next_charge, provider_id, datetime.now().isoformat())
        )
        self.connection.commit()
        return cursor.lastrowid
    
    async def update_subscription_status(self, subscription_id: int, status: str) -> bool:
        """Обновляет статус подписки"""
        cursor = self.connection.cursor()
        now = datetime.now().date()
        next_charge = (now + timedelta(days=30)).isoformat() if status == "active" else None
        
        cursor.execute(
            "UPDATE subscriptions SET status = ?, next_charge = ?, updated_at = ? WHERE id = ?",
            (status, next_charge, datetime.now().isoformat(), subscription_id)
        )
        self.connection.commit()
        return cursor.rowcount > 0
    
    async def get_active_subscribers(self) -> List[Dict[str, Any]]:
        """Получает список активных подписчиков для еженедельных рассылок"""
        cursor = self.connection.cursor()
        cursor.execute(
            """
            SELECT u.* FROM users u
            JOIN subscriptions s ON u.id = s.user_id
            WHERE s.status IN ('active', 'trial') 
            AND (s.trial_end IS NULL OR date(s.trial_end) >= date('now'))
            AND u.push_enabled = 1
            """
        )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]