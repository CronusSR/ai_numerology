# database.py - модуль для работы с базой данных
import os
import json
import asyncio
import asyncpg
from datetime import datetime, date, timedelta
from typing import Dict, Any, List, Optional, Union

class Database:
    def __init__(self):
        self.pool = None
        self.connection_params = {
            "user": os.getenv("POSTGRES_USER", "postgres"),
            "password": os.getenv("POSTGRES_PASSWORD", "postgres"),
            "database": os.getenv("POSTGRES_DB", "numerology_bot"),
            "host": os.getenv("POSTGRES_HOST", "postgres"),
            "port": int(os.getenv("POSTGRES_PORT", "5432"))
        }
    
    async def init(self):
        """Инициализация соединения с базой данных"""
        # Попытка подключения к базе данных с ожиданием готовности PostgreSQL
        retries = 5
        while retries > 0:
            try:
                self.pool = await asyncpg.create_pool(**self.connection_params)
                # Проверяем работоспособность соединения
                async with self.pool.acquire() as conn:
                    await conn.execute("SELECT 1")
                break
            except (asyncpg.exceptions.PostgresError, OSError) as e:
                retries -= 1
                if retries == 0:
                    raise e
                print(f"Не удалось подключиться к базе данных. Повторная попытка через 5 секунд... ({e})")
                await asyncio.sleep(5)
        
        # Проверяем наличие таблиц
        await self._create_tables_if_not_exist()
    
    async def _create_tables_if_not_exist(self):
        """Создает таблицы, если они не существуют"""
        async with self.pool.acquire() as conn:
            # Проверяем наличие таблицы users
            users_exists = await conn.fetchval(
                "SELECT EXISTS(SELECT FROM information_schema.tables WHERE table_name = 'users')"
            )
            
            if not users_exists:
                # Создаем таблицу users
                await conn.execute("""
                    CREATE TABLE users (
                        id bigserial PRIMARY KEY,
                        tg_id bigint UNIQUE,
                        fio text,
                        birthdate date,
                        lang text DEFAULT 'ru',
                        push_enabled bool DEFAULT true,
                        state text,
                        created_at timestamptz DEFAULT now()
                    )
                """)
            
            # Проверяем наличие таблицы orders
            orders_exists = await conn.fetchval(
                "SELECT EXISTS(SELECT FROM information_schema.tables WHERE table_name = 'orders')"
            )
            
            if not orders_exists:
                # Создаем таблицу orders
                await conn.execute("""
                    CREATE TABLE orders (
                        id bigserial PRIMARY KEY,
                        user_id bigint REFERENCES users(id),
                        product text,
                        price numeric,
                        currency text,
                        status text,
                        paid_at timestamptz,
                        payload jsonb,
                        created_at timestamptz DEFAULT now()
                    )
                """)
            
            # Проверяем наличие таблицы reports
            reports_exists = await conn.fetchval(
                "SELECT EXISTS(SELECT FROM information_schema.tables WHERE table_name = 'reports')"
            )
            
            if not reports_exists:
                # Создаем таблицу reports
                await conn.execute("""
                    CREATE TABLE reports (
                        id bigserial PRIMARY KEY,
                        user_id bigint REFERENCES users(id),
                        report_type text,
                        core_json jsonb,
                        pdf_url text,
                        created_at timestamptz DEFAULT now()
                    )
                """)
            
            # Проверяем наличие таблицы subscriptions
            subscriptions_exists = await conn.fetchval(
                "SELECT EXISTS(SELECT FROM information_schema.tables WHERE table_name = 'subscriptions')"
            )
            
            if not subscriptions_exists:
                # Создаем таблицу subscriptions
                await conn.execute("""
                    CREATE TABLE subscriptions (
                        id bigserial PRIMARY KEY,
                        user_id bigint REFERENCES users(id),
                        status text,
                        trial_end date,
                        next_charge date,
                        provider_id text,
                        created_at timestamptz DEFAULT now()
                    )
                """)
    
    async def get_user_by_tg_id(self, tg_id: int) -> Optional[Dict[str, Any]]:
        """Получает пользователя по идентификатору Telegram"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM users WHERE tg_id = $1",
                tg_id
            )
            
            if row:
                return dict(row)
            return None
    
    async def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Получает пользователя по ID в базе данных"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM users WHERE id = $1",
                user_id
            )
            
            if row:
                return dict(row)
            return None
    
    async def create_user(self, tg_id: int) -> int:
        """Создает нового пользователя"""
        async with self.pool.acquire() as conn:
            user_id = await conn.fetchval(
                "INSERT INTO users (tg_id) VALUES ($1) RETURNING id",
                tg_id
            )
            return user_id
    
    async def update_user(self, tg_id: int, fio: str, birthdate: str) -> bool:
        """Обновляет данные пользователя"""
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                "UPDATE users SET fio = $1, birthdate = $2 WHERE tg_id = $3",
                fio, birthdate, tg_id
            )
            return result == "UPDATE 1"
    
    async def update_user_settings(self, tg_id: int, lang: str = None, push_enabled: bool = None) -> bool:
        """Обновляет настройки пользователя"""
        query_parts = []
        params = []
        
        if lang is not None:
            query_parts.append("lang = $" + str(len(params) + 1))
            params.append(lang)
        
        if push_enabled is not None:
            query_parts.append("push_enabled = $" + str(len(params) + 1))
            params.append(push_enabled)
        
        if not query_parts:
            return False
        
        params.append(tg_id)
        
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                f"UPDATE users SET {', '.join(query_parts)} WHERE tg_id = ${len(params)}",
                *params
            )
            return result == "UPDATE 1"
    
    async def save_report(self, user_id: int, report_type: str, core_json: Dict[str, Any]) -> int:
        """Сохраняет отчет в базу данных"""
        async with self.pool.acquire() as conn:
            # Получаем ID пользователя по Telegram ID, если передан tg_id
            if isinstance(user_id, int) and user_id > 0:
                real_user_id = await conn.fetchval(
                    "SELECT id FROM users WHERE tg_id = $1",
                    user_id
                )
                if real_user_id:
                    user_id = real_user_id
            
            # Сохраняем отчет
            report_id = await conn.fetchval(
                "INSERT INTO reports (user_id, report_type, core_json) VALUES ($1, $2, $3) RETURNING id",
                user_id, report_type, json.dumps(core_json)
            )
            return report_id
    
    async def update_report_pdf(self, report_id: int, pdf_url: str) -> bool:
        """Обновляет URL PDF-отчета"""
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                "UPDATE reports SET pdf_url = $1 WHERE id = $2",
                pdf_url, report_id
            )
            return result == "UPDATE 1"
    
    async def get_report(self, report_id: int) -> Optional[Dict[str, Any]]:
        """Получает отчет по ID"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM reports WHERE id = $1",
                report_id
            )
            
            if row:
                report = dict(row)
                # Парсим JSON из строки
                if report["core_json"]:
                    report["core_json"] = json.loads(report["core_json"])
                return report
            return None
    
    async def get_latest_user_report(self, user_id: int, report_type: str) -> Optional[Dict[str, Any]]:
        """Получает последний отчет пользователя определенного типа"""
        async with self.pool.acquire() as conn:
            # Получаем ID пользователя по Telegram ID, если передан tg_id
            if isinstance(user_id, int) and user_id > 0:
                real_user_id = await conn.fetchval(
                    "SELECT id FROM users WHERE tg_id = $1",
                    user_id
                )
                if real_user_id:
                    user_id = real_user_id
            
            row = await conn.fetchrow(
                """
                SELECT * FROM reports 
                WHERE user_id = $1 AND report_type = $2 AND pdf_url IS NOT NULL
                ORDER BY created_at DESC 
                LIMIT 1
                """,
                user_id, report_type
            )
            
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
        async with self.pool.acquire() as conn:
            # Получаем ID пользователя по Telegram ID, если передан tg_id
            if isinstance(user_id, int) and user_id > 0:
                real_user_id = await conn.fetchval(
                    "SELECT id FROM users WHERE tg_id = $1",
                    user_id
                )
                if real_user_id:
                    user_id = real_user_id
            
            # Создаем заказ
            order_id = await conn.fetchval(
                """
                INSERT INTO orders (user_id, product, price, currency, status, payload) 
                VALUES ($1, $2, $3, $4, 'pending', $5) 
                RETURNING id
                """,
                user_id, product, price, currency, json.dumps(payload)
            )
            return order_id
    
    async def update_order_status(self, order_id: int, status: str) -> bool:
        """Обновляет статус заказа"""
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                """
                UPDATE orders SET 
                    status = $1, 
                    paid_at = CASE WHEN $1 = 'paid' THEN now() ELSE paid_at END
                WHERE id = $2
                """,
                status, order_id
            )
            return result == "UPDATE 1"
    
    async def get_order(self, order_id: int) -> Optional[Dict[str, Any]]:
        """Получает заказ по ID"""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM orders WHERE id = $1",
                order_id
            )
            
            if row:
                order = dict(row)
                # Парсим JSON из строки
                if order["payload"]:
                    order["payload"] = json.loads(order["payload"])
                return order
            return None
    
    async def get_user_subscription(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Получает подписку пользователя"""
        async with self.pool.acquire() as conn:
            # Получаем ID пользователя по Telegram ID, если передан tg_id
            if isinstance(user_id, int) and user_id > 0:
                real_user_id = await conn.fetchval(
                    "SELECT id FROM users WHERE tg_id = $1",
                    user_id
                )
                if real_user_id:
                    user_id = real_user_id
            
            row = await conn.fetchrow(
                "SELECT * FROM subscriptions WHERE user_id = $1 ORDER BY created_at DESC LIMIT 1",
                user_id
            )
            
            if row:
                return dict(row)
            return None
    
    async def create_subscription(self, user_id: int, status: str, provider_id: str = None) -> int:
        """Создает новую подписку"""
        async with self.pool.acquire() as conn:
            # Получаем ID пользователя по Telegram ID, если передан tg_id
            if isinstance(user_id, int) and user_id > 0:
                real_user_id = await conn.fetchval(
                    "SELECT id FROM users WHERE tg_id = $1",
                    user_id
                )
                if real_user_id:
                    user_id = real_user_id
            
            # Устанавливаем даты для подписки
            now = datetime.now().date()
            trial_end = now + timedelta(days=7) if status == "trial" else None
            next_charge = now + timedelta(days=30) if status in ["active", "trial"] else None
            
            # Создаем подписку
            subscription_id = await conn.fetchval(
                """
                INSERT INTO subscriptions (user_id, status, trial_end, next_charge, provider_id) 
                VALUES ($1, $2, $3, $4, $5) 
                RETURNING id
                """,
                user_id, status, trial_end, next_charge, provider_id
            )
            return subscription_id
    
    async def update_subscription_status(self, subscription_id: int, status: str) -> bool:
        """Обновляет статус подписки"""
        async with self.pool.acquire() as conn:
            now = datetime.now().date()
            next_charge = now + timedelta(days=30) if status == "active" else None
            
            result = await conn.execute(
                "UPDATE subscriptions SET status = $1, next_charge = $2 WHERE id = $3",
                status, next_charge, subscription_id
            )
            return result == "UPDATE 1"
    
    async def get_active_subscribers(self) -> List[Dict[str, Any]]:
        """Получает список активных подписчиков для еженедельных рассылок"""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT u.* FROM users u
                JOIN subscriptions s ON u.id = s.user_id
                WHERE s.status IN ('active', 'trial') 
                AND (s.trial_end IS NULL OR s.trial_end >= CURRENT_DATE)
                AND u.push_enabled = true
                """
            )
            
            return [dict(row) for row in rows]