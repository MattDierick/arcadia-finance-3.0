-- ============================================================
-- Arcadia Finance – Database Init & Seed
-- ⚠️  INTENTIONALLY VULNERABLE: no password hashing, plain SQL
-- ============================================================

CREATE DATABASE IF NOT EXISTS arcadia CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE arcadia;

-- ─────────────────────────────────────────
-- USERS
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    name       VARCHAR(100) NOT NULL,
    surname    VARCHAR(100) NOT NULL,
    email      VARCHAR(255) NOT NULL UNIQUE,
    phone      VARCHAR(30),
    username   VARCHAR(80)  NOT NULL UNIQUE,
    password   VARCHAR(255) NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ─────────────────────────────────────────
-- ACCOUNTS
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS accounts (
    id             INT AUTO_INCREMENT PRIMARY KEY,
    user_id        INT NOT NULL,
    account_number VARCHAR(20) NOT NULL UNIQUE,
    type           ENUM('checking','savings','investment') DEFAULT 'checking',
    balance        DECIMAL(15,2) DEFAULT 0.00,
    currency       VARCHAR(5) DEFAULT 'EUR',
    created_at     DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- ─────────────────────────────────────────
-- TRANSFERS
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS transfers (
    id               INT AUTO_INCREMENT PRIMARY KEY,
    from_account     VARCHAR(20) NOT NULL,
    to_account       VARCHAR(20) NOT NULL,
    amount           DECIMAL(15,2) NOT NULL,
    note             VARCHAR(255),
    status           ENUM('completed','pending','failed') DEFAULT 'completed',
    created_at       DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ─────────────────────────────────────────
-- APP CONFIG (LLM settings, etc.)
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS app_config (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    config_key  VARCHAR(100) NOT NULL UNIQUE,
    config_value TEXT,
    updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- ─────────────────────────────────────────
-- SEED: 4 fake users (passwords stored in plain text – intentional vuln)
-- ─────────────────────────────────────────
INSERT IGNORE INTO users (name, surname, email, phone, username, password) VALUES
('Alice',   'Moreau',    'alice.moreau@arcadiafinance.com',    '+33 6 12 34 56 78', 'alice',   'alice123'),
('Thomas',  'Lefebvre',  'thomas.lefebvre@arcadiafinance.com', '+33 6 23 45 67 89', 'thomas',  'thomas123'),
('Sophie',  'Bernard',   'sophie.bernard@arcadiafinance.com',  '+33 7 34 56 78 90', 'sophie',  'sophie123'),
('Lucas',   'Dupont',    'lucas.dupont@arcadiafinance.com',    '+33 7 45 67 89 01', 'lucas',   'lucas123');

-- ─────────────────────────────────────────
-- VIRTUAL ACCOUNTS (used internally)
-- ─────────────────────────────────────────
-- A system user is needed to hold virtual accounts
INSERT IGNORE INTO users (id, name, surname, email, username, password) VALUES
(99, 'System', 'Arcadia', 'system@arcadiafinance.internal', 'system', 'not-a-real-password');

INSERT IGNORE INTO accounts (user_id, account_number, type, balance, currency) VALUES
(99, 'STOCK-MARKET-VIRTUAL', 'investment', 999999999.00, 'USD');

-- ─────────────────────────────────────────
-- SEED: accounts
-- ─────────────────────────────────────────
INSERT IGNORE INTO accounts (user_id, account_number, type, balance, currency) VALUES
-- Alice
(1, 'FR7601234001001', 'checking',    12450.75, 'EUR'),
(1, 'FR7601234001002', 'savings',     35200.00, 'EUR'),
(1, 'FR7601234001003', 'investment',  80000.00, 'EUR'),
-- Thomas
(2, 'FR7601234002001', 'checking',     5890.30, 'EUR'),
(2, 'FR7601234002002', 'savings',     18750.00, 'EUR'),
-- Sophie
(3, 'FR7601234003001', 'checking',     9310.45, 'EUR'),
(3, 'FR7601234003002', 'savings',     22000.00, 'EUR'),
(3, 'FR7601234003003', 'investment',  45500.00, 'EUR'),
-- Lucas
(4, 'FR7601234004001', 'checking',     3200.00, 'EUR'),
(4, 'FR7601234004002', 'savings',     11000.00, 'EUR');

-- ─────────────────────────────────────────
-- SEED: sample transfer history
-- ─────────────────────────────────────────
INSERT IGNORE INTO transfers (from_account, to_account, amount, note, status, created_at) VALUES
('FR7601234001001', 'FR7601234002001',  500.00, 'Dinner split',           'completed', '2026-07-01 10:30:00'),
('FR7601234002001', 'FR7601234003001',  200.00, 'Shared rent utilities',  'completed', '2026-07-05 14:15:00'),
('FR7601234003001', 'FR7601234004001', 1500.00, 'Project payment',        'completed', '2026-07-10 09:00:00'),
('FR7601234001001', 'FR7601234004001',  350.00, 'Birthday gift',          'completed', '2026-07-15 18:45:00'),
('FR7601234004001', 'FR7601234001001',  100.00, 'Reimbursement',          'completed', '2026-07-20 11:20:00'),
('FR7601234002001', 'FR7601234001001',  750.00, 'Invoice #2024-07',       'completed', '2026-07-22 16:00:00'),
('FR7601234001002', 'FR7601234003002', 2000.00, 'Savings transfer',       'completed', '2026-07-25 08:30:00'),
('FR7601234003001', 'FR7601234002001',  420.00, 'Trip expenses',          'completed', '2026-07-28 13:00:00');

-- ─────────────────────────────────────────
-- STOCK HOLDINGS  (one row per user+ticker)
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS stock_holdings (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    user_id    INT NOT NULL,
    ticker     VARCHAR(20) NOT NULL,
    quantity   DECIMAL(18,6) NOT NULL DEFAULT 0,
    avg_price  DECIMAL(18,4) NOT NULL DEFAULT 0,
    currency   VARCHAR(5)   DEFAULT 'USD',
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_user_ticker (user_id, ticker),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- ─────────────────────────────────────────
-- STOCK ORDERS  (immutable purchase log)
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS stock_orders (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    user_id      INT NOT NULL,
    ticker       VARCHAR(20) NOT NULL,
    quantity     DECIMAL(18,6) NOT NULL,
    price        DECIMAL(18,4) NOT NULL,
    total        DECIMAL(18,4) NOT NULL,
    currency     VARCHAR(5)   DEFAULT 'USD',
    from_account VARCHAR(20) NOT NULL,
    status       ENUM('completed','failed') DEFAULT 'completed',
    created_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- ─────────────────────────────────────────
-- SEED: app config defaults
-- ─────────────────────────────────────────
INSERT IGNORE INTO app_config (config_key, config_value) VALUES
('llm_url',   ''),
('llm_model', 'gpt-4o'),
('chatbot_system_prompt', 'You are Aria, a helpful virtual assistant for Arcadia Finance. You help clients with questions about their accounts, transfers, and banking services. Be concise, professional, and friendly.');
