-- Миграция 001: Создание базовых таблиц для Payment Bot
-- Дата: 2025-01-01
-- Описание: Создание таблиц пользователей, платежей, инвайт-ссылок и истории подписок

-- Включаем поддержку внешних ключей
PRAGMA foreign_keys = ON;

-- Таблица пользователей
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    last_name TEXT,
    subscription_end TIMESTAMP,
    subscription_status TEXT DEFAULT 'expired' CHECK (subscription_status IN ('active', 'expired', 'suspended', 'trial')),
    yookassa_customer_id TEXT,
    is_active BOOLEAN DEFAULT 1,
    total_payments INTEGER DEFAULT 0,
    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Таблица платежей
CREATE TABLE IF NOT EXISTS payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    payment_id TEXT UNIQUE NOT NULL,
    yookassa_payment_id TEXT UNIQUE,
    amount DECIMAL(10,2) NOT NULL,
    currency TEXT DEFAULT 'RUB',
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'succeeded', 'canceled', 'failed')),
    description TEXT,
    confirmation_url TEXT,
    metadata TEXT, -- JSON строка с дополнительными данными
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
);

-- Таблица инвайт-ссылок
CREATE TABLE IF NOT EXISTS invite_links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    invite_link TEXT NOT NULL,
    expire_date TIMESTAMP,
    member_limit INTEGER DEFAULT 1,
    is_used BOOLEAN DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
);

-- Таблица истории подписок
CREATE TABLE IF NOT EXISTS subscription_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    payment_id INTEGER,
    start_date TIMESTAMP NOT NULL,
    end_date TIMESTAMP NOT NULL,
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'expired', 'canceled')),
    amount_paid DECIMAL(10,2),
    subscription_type TEXT DEFAULT 'monthly', -- monthly, trial, bonus
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE,
    FOREIGN KEY (payment_id) REFERENCES payments (id) ON DELETE SET NULL
);

-- Таблица рефералов (для будущего использования)
CREATE TABLE IF NOT EXISTS referrals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    referrer_id INTEGER NOT NULL,
    referred_id INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    bonus_given BOOLEAN DEFAULT 0,
    FOREIGN KEY (referrer_id) REFERENCES users (user_id) ON DELETE CASCADE,
    FOREIGN KEY (referred_id) REFERENCES users (user_id) ON DELETE CASCADE,
    UNIQUE(referrer_id, referred_id)
);

-- Таблица настроек системы
CREATE TABLE IF NOT EXISTS system_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    description TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Индексы для оптимизации запросов
CREATE INDEX IF NOT EXISTS idx_users_subscription_end ON users(subscription_end);
CREATE INDEX IF NOT EXISTS idx_users_subscription_status ON users(subscription_status);
CREATE INDEX IF NOT EXISTS idx_users_last_activity ON users(last_activity);
CREATE INDEX IF NOT EXISTS idx_payments_status ON payments(status);
CREATE INDEX IF NOT EXISTS idx_payments_user_id ON payments(user_id);
CREATE INDEX IF NOT EXISTS idx_payments_created_at ON payments(created_at);
CREATE INDEX IF NOT EXISTS idx_payments_yookassa_id ON payments(yookassa_payment_id);
CREATE INDEX IF NOT EXISTS idx_invite_links_user_id ON invite_links(user_id);
CREATE INDEX IF NOT EXISTS idx_invite_links_expire_date ON invite_links(expire_date);
CREATE INDEX IF NOT EXISTS idx_subscription_history_user_id ON subscription_history(user_id);
CREATE INDEX IF NOT EXISTS idx_subscription_history_dates ON subscription_history(start_date, end_date);

-- Триггеры для автоматического обновления updated_at
CREATE TRIGGER IF NOT EXISTS update_users_updated_at 
    AFTER UPDATE ON users
    BEGIN
        UPDATE users SET updated_at = CURRENT_TIMESTAMP WHERE user_id = NEW.user_id;
    END;

CREATE TRIGGER IF NOT EXISTS update_payments_updated_at 
    AFTER UPDATE ON payments
    BEGIN
        UPDATE payments SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
    END;

-- Вставляем начальные настройки
INSERT OR IGNORE INTO system_settings (key, value, description) VALUES 
    ('db_version', '1', 'Версия схемы базы данных'),
    ('bot_started_at', datetime('now'), 'Время первого запуска бота'),
    ('maintenance_mode', '0', 'Режим обслуживания (0 - выключен, 1 - включен)'),
    ('max_payment_attempts', '3', 'Максимальное количество попыток оплаты'),
    ('invite_link_expire_hours', '24', 'Срок действия инвайт-ссылок в часах');

-- Создаем индексы для полнотекстового поиска (если понадобится)
-- CREATE VIRTUAL TABLE IF NOT EXISTS users_fts USING fts5(user_id, username, first_name, last_name);

-- Представления для удобного доступа к данным
CREATE VIEW IF NOT EXISTS active_subscriptions AS
SELECT 
    u.user_id,
    u.username,
    u.first_name,
    u.last_name,
    u.subscription_end,
    u.total_payments,
    CAST((julianday(u.subscription_end) - julianday('now')) AS INTEGER) as days_left
FROM users u 
WHERE u.subscription_status = 'active' 
  AND u.subscription_end > datetime('now')
  AND u.is_active = 1;

CREATE VIEW IF NOT EXISTS payment_stats AS
SELECT 
    COUNT(*) as total_payments,
    SUM(CASE WHEN status = 'succeeded' THEN 1 ELSE 0 END) as successful_payments,
    SUM(CASE WHEN status = 'succeeded' THEN amount ELSE 0 END) as total_revenue,
    AVG(CASE WHEN status = 'succeeded' THEN amount ELSE NULL END) as avg_payment,
    DATE(created_at) as payment_date
FROM payments 
GROUP BY DATE(created_at)
ORDER BY payment_date DESC;