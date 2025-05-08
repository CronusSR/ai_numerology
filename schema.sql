-- Удаляем таблицы, если они существуют
DROP TABLE IF EXISTS subscriptions;
DROP TABLE IF EXISTS reports;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS users;

-- Создаем таблицу пользователей
CREATE TABLE users (
    id bigserial PRIMARY KEY,
    tg_id bigint UNIQUE,
    fio text,
    birthdate date,
    lang text DEFAULT 'ru',
    push_enabled bool DEFAULT true,
    state text,
    created_at timestamptz DEFAULT now()
);

-- Создаем таблицу заказов
CREATE TABLE orders (
    id bigserial PRIMARY KEY,
    user_id bigint REFERENCES users(id),
    product text, -- 'full_report' | 'compatibility' | 'subscription_month'
    price numeric,
    currency text,
    status text, -- 'pending' | 'paid' | 'failed'
    paid_at timestamptz,
    telegram_payment_charge_id text,
    provider_payment_charge_id text,
    payload jsonb,
    created_at timestamptz DEFAULT now()
);

-- Создаем таблицу отчетов
CREATE TABLE reports (
    id bigserial PRIMARY KEY,
    user_id bigint REFERENCES users(id),
    report_type text, -- 'mini' | 'full' | 'compatibility'
    core_json jsonb,
    pdf_url text,
    created_at timestamptz DEFAULT now()
);

-- Создаем таблицу подписок
CREATE TABLE subscriptions (
    id bigserial PRIMARY KEY,
    user_id bigint REFERENCES users(id),
    status text, -- 'trial' | 'active' | 'canceled'
    trial_end date,
    next_charge date,
    provider_id text,
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now()
);

-- Индексы для ускорения поиска
CREATE INDEX idx_users_tg_id ON users(tg_id);
CREATE INDEX idx_orders_user_id ON orders(user_id);
CREATE INDEX idx_reports_user_id ON reports(user_id);
CREATE INDEX idx_subscriptions_user_id ON subscriptions(user_id);
CREATE INDEX idx_subscriptions_status ON subscriptions(status);