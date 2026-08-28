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
-- -----------------------------------------
-- SEED: 100 BOLA target users (IDs 5-104)
-- No accounts, no balances, no login needed - BOLA demo targets only.
-- -----------------------------------------
INSERT IGNORE INTO users (name, surname, email, phone, username, password) VALUES
('Emma', 'Martin', 'emma.martin@arcadiafinance.com', '+33 6 10 00 00 01', 'emma.martin', 'bola_target'),
('Hugo', 'Simon', 'hugo.simon@arcadiafinance.com', '+33 6 10 00 00 02', 'hugo.simon', 'bola_target'),
('Lea', 'Michel', 'lea.michel@arcadiafinance.com', '+33 6 10 00 00 03', 'lea.michel', 'bola_target'),
('Nathan', 'Leroy', 'nathan.leroy@arcadiafinance.com', '+33 6 10 00 00 04', 'nathan.leroy', 'bola_target'),
('Manon', 'Laurent', 'manon.laurent@arcadiafinance.com', '+33 6 10 00 00 05', 'manon.laurent', 'bola_target'),
('Theo', 'Girard', 'theo.girard@arcadiafinance.com', '+33 6 10 00 00 06', 'theo.girard', 'bola_target'),
('Camille', 'Bonnet', 'camille.bonnet@arcadiafinance.com', '+33 6 10 00 00 07', 'camille.bonnet', 'bola_target'),
('Romain', 'Francois', 'romain.francois@arcadiafinance.com', '+33 6 10 00 00 08', 'romain.francois', 'bola_target'),
('Chloe', 'Martinez', 'chloe.martinez@arcadiafinance.com', '+33 6 10 00 00 09', 'chloe.martinez', 'bola_target'),
('Maxime', 'Garcia', 'maxime.garcia@arcadiafinance.com', '+33 6 10 00 00 10', 'maxime.garcia', 'bola_target'),
('Juliette', 'David', 'juliette.david@arcadiafinance.com', '+33 6 10 00 00 11', 'juliette.david', 'bola_target'),
('Antoine', 'Bertrand', 'antoine.bertrand@arcadiafinance.com', '+33 6 10 00 00 12', 'antoine.bertrand', 'bola_target'),
('Pauline', 'Roux', 'pauline.roux@arcadiafinance.com', '+33 6 10 00 00 13', 'pauline.roux', 'bola_target'),
('Clement', 'Vincent', 'clement.vincent@arcadiafinance.com', '+33 6 10 00 00 14', 'clement.vincent', 'bola_target'),
('Marine', 'Fournier', 'marine.fournier@arcadiafinance.com', '+33 6 10 00 00 15', 'marine.fournier', 'bola_target'),
('Florian', 'Morel', 'florian.morel@arcadiafinance.com', '+33 6 10 00 00 16', 'florian.morel', 'bola_target'),
('Laura', 'Muller', 'laura.muller@arcadiafinance.com', '+33 6 10 00 00 17', 'laura.muller', 'bola_target'),
('Kevin', 'Petit', 'kevin.petit@arcadiafinance.com', '+33 6 10 00 00 18', 'kevin.petit', 'bola_target'),
('Emilie', 'Lemaire', 'emilie.lemaire@arcadiafinance.com', '+33 6 10 00 00 19', 'emilie.lemaire', 'bola_target'),
('Quentin', 'Dumont', 'quentin.dumont@arcadiafinance.com', '+33 6 10 00 00 20', 'quentin.dumont', 'bola_target'),
('Mathilde', 'Fontaine', 'mathilde.fontaine@arcadiafinance.com', '+33 6 10 00 00 21', 'mathilde.fontaine', 'bola_target'),
('Baptiste', 'Rousseau', 'baptiste.rousseau@arcadiafinance.com', '+33 6 10 00 00 22', 'baptiste.rousseau', 'bola_target'),
('Elisa', 'Blanc', 'elisa.blanc@arcadiafinance.com', '+33 6 10 00 00 23', 'elisa.blanc', 'bola_target'),
('Nicolas', 'Guerin', 'nicolas.guerin@arcadiafinance.com', '+33 6 10 00 00 24', 'nicolas.guerin', 'bola_target'),
('Charlotte', 'Gauthier', 'charlotte.gauthier@arcadiafinance.com', '+33 6 10 00 00 25', 'charlotte.gauthier', 'bola_target');

INSERT IGNORE INTO users (name, surname, email, phone, username, password) VALUES
('Adrien', 'Robin', 'adrien.robin@arcadiafinance.com', '+33 6 10 00 00 26', 'adrien.robin', 'bola_target'),
('Anais', 'Clement', 'anais.clement@arcadiafinance.com', '+33 6 10 00 00 27', 'anais.clement', 'bola_target'),
('Alexis', 'Mercier', 'alexis.mercier@arcadiafinance.com', '+33 6 10 00 00 28', 'alexis.mercier', 'bola_target'),
('Lucie', 'Chevalier', 'lucie.chevalier@arcadiafinance.com', '+33 6 10 00 00 29', 'lucie.chevalier', 'bola_target'),
('Thomas', 'Colin', 'thomas.colin@arcadiafinance.com', '+33 6 10 00 00 30', 'thomas.colin', 'bola_target'),
('Virginie', 'Charpentier', 'virginie.charpentier@arcadiafinance.com', '+33 6 10 00 00 31', 'virginie.charpentier', 'bola_target'),
('Sebastien', 'Gaillard', 'sebastien.gaillard@arcadiafinance.com', '+33 6 10 00 00 32', 'sebastien.gaillard', 'bola_target'),
('Justine', 'Renaud', 'justine.renaud@arcadiafinance.com', '+33 6 10 00 00 33', 'justine.renaud', 'bola_target'),
('Damien', 'Dupuis', 'damien.dupuis@arcadiafinance.com', '+33 6 10 00 00 34', 'damien.dupuis', 'bola_target'),
('Aurelie', 'Joly', 'aurelie.joly@arcadiafinance.com', '+33 6 10 00 00 35', 'aurelie.joly', 'bola_target'),
('Julien', 'Perrin', 'julien.perrin@arcadiafinance.com', '+33 6 10 00 00 36', 'julien.perrin', 'bola_target'),
('Melanie', 'Leclercq', 'melanie.leclercq@arcadiafinance.com', '+33 6 10 00 00 37', 'melanie.leclercq', 'bola_target'),
('Pierre', 'Noel', 'pierre.noel@arcadiafinance.com', '+33 6 10 00 00 38', 'pierre.noel', 'bola_target'),
('Sandrine', 'Masson', 'sandrine.masson@arcadiafinance.com', '+33 6 10 00 00 39', 'sandrine.masson', 'bola_target'),
('Guillaume', 'Marchand', 'guillaume.marchand@arcadiafinance.com', '+33 6 10 00 00 40', 'guillaume.marchand', 'bola_target'),
('Stephanie', 'Lucas', 'stephanie.lucas@arcadiafinance.com', '+33 6 10 00 00 41', 'stephanie.lucas', 'bola_target'),
('Xavier', 'Mathieu', 'xavier.mathieu@arcadiafinance.com', '+33 6 10 00 00 42', 'xavier.mathieu', 'bola_target'),
('Nathalie', 'Henry', 'nathalie.henry@arcadiafinance.com', '+33 6 10 00 00 43', 'nathalie.henry', 'bola_target'),
('Olivier', 'Renault', 'olivier.renault@arcadiafinance.com', '+33 6 10 00 00 44', 'olivier.renault', 'bola_target'),
('Isabelle', 'Richard', 'isabelle.richard@arcadiafinance.com', '+33 6 10 00 00 45', 'isabelle.richard', 'bola_target'),
('Laurent', 'Durand', 'laurent.durand@arcadiafinance.com', '+33 6 10 00 00 46', 'laurent.durand', 'bola_target'),
('Veronique', 'Thomas', 'veronique.thomas@arcadiafinance.com', '+33 6 10 00 00 47', 'veronique.thomas', 'bola_target'),
('Christophe', 'Baudoin', 'christophe.baudoin@arcadiafinance.com', '+33 6 10 00 00 48', 'christophe.baudoin', 'bola_target'),
('Catherine', 'Prevot', 'catherine.prevot@arcadiafinance.com', '+33 6 10 00 00 49', 'catherine.prevot', 'bola_target'),
('Philippe', 'Laporte', 'philippe.laporte@arcadiafinance.com', '+33 6 10 00 00 50', 'philippe.laporte', 'bola_target');

INSERT IGNORE INTO users (name, surname, email, phone, username, password) VALUES
('Marie', 'Lambert', 'marie.lambert@arcadiafinance.com', '+33 6 10 00 00 51', 'marie.lambert', 'bola_target'),
('Pascal', 'Giraud', 'pascal.giraud@arcadiafinance.com', '+33 6 10 00 00 52', 'pascal.giraud', 'bola_target'),
('Brigitte', 'Lefevre', 'brigitte.lefevre@arcadiafinance.com', '+33 6 10 00 00 53', 'brigitte.lefevre', 'bola_target'),
('Michel', 'Aubert', 'michel.aubert@arcadiafinance.com', '+33 6 10 00 00 54', 'michel.aubert', 'bola_target'),
('Sylvie', 'Leclerc', 'sylvie.leclerc@arcadiafinance.com', '+33 6 10 00 00 55', 'sylvie.leclerc', 'bola_target'),
('Bernard', 'Picard', 'bernard.picard@arcadiafinance.com', '+33 6 10 00 00 56', 'bernard.picard', 'bola_target'),
('Monique', 'Arnaud', 'monique.arnaud@arcadiafinance.com', '+33 6 10 00 00 57', 'monique.arnaud', 'bola_target'),
('Francois', 'Baron', 'francois.baron@arcadiafinance.com', '+33 6 10 00 00 58', 'francois.baron', 'bola_target'),
('Colette', 'Vidal', 'colette.vidal@arcadiafinance.com', '+33 6 10 00 00 59', 'colette.vidal', 'bola_target'),
('Jacques', 'Caron', 'jacques.caron@arcadiafinance.com', '+33 6 10 00 00 60', 'jacques.caron', 'bola_target'),
('Helene', 'Dufour', 'helene.dufour@arcadiafinance.com', '+33 6 10 00 00 61', 'helene.dufour', 'bola_target'),
('Daniel', 'Faure', 'daniel.faure@arcadiafinance.com', '+33 6 10 00 00 62', 'daniel.faure', 'bola_target'),
('Martine', 'Lacroix', 'martine.lacroix@arcadiafinance.com', '+33 6 10 00 00 63', 'martine.lacroix', 'bola_target'),
('Andre', 'Riviere', 'andre.riviere@arcadiafinance.com', '+33 6 10 00 00 64', 'andre.riviere', 'bola_target'),
('Daniele', 'Meunier', 'daniele.meunier@arcadiafinance.com', '+33 6 10 00 00 65', 'daniele.meunier', 'bola_target'),
('Claude', 'Perrot', 'claude.perrot@arcadiafinance.com', '+33 6 10 00 00 66', 'claude.perrot', 'bola_target'),
('Denise', 'Renard', 'denise.renard@arcadiafinance.com', '+33 6 10 00 00 67', 'denise.renard', 'bola_target'),
('Roger', 'Perret', 'roger.perret@arcadiafinance.com', '+33 6 10 00 00 68', 'roger.perret', 'bola_target'),
('Odette', 'Schmitt', 'odette.schmitt@arcadiafinance.com', '+33 6 10 00 00 69', 'odette.schmitt', 'bola_target'),
('Raymond', 'Gautier', 'raymond.gautier@arcadiafinance.com', '+33 6 10 00 00 70', 'raymond.gautier', 'bola_target'),
('Ginette', 'Leroux', 'ginette.leroux@arcadiafinance.com', '+33 6 10 00 00 71', 'ginette.leroux', 'bola_target'),
('Marcel', 'Besson', 'marcel.besson@arcadiafinance.com', '+33 6 10 00 00 72', 'marcel.besson', 'bola_target'),
('Yvette', 'Collet', 'yvette.collet@arcadiafinance.com', '+33 6 10 00 00 73', 'yvette.collet', 'bola_target'),
('Georges', 'Millet', 'georges.millet@arcadiafinance.com', '+33 6 10 00 00 74', 'georges.millet', 'bola_target'),
('Lucette', 'Breton', 'lucette.breton@arcadiafinance.com', '+33 6 10 00 00 75', 'lucette.breton', 'bola_target');

INSERT IGNORE INTO users (name, surname, email, phone, username, password) VALUES
('Albert', 'Leger', 'albert.leger@arcadiafinance.com', '+33 6 10 00 00 76', 'albert.leger', 'bola_target'),
('Simone', 'Hubert', 'simone.hubert@arcadiafinance.com', '+33 6 10 00 00 77', 'simone.hubert', 'bola_target'),
('Henri', 'Gros', 'henri.gros@arcadiafinance.com', '+33 6 10 00 00 78', 'henri.gros', 'bola_target'),
('Suzanne', 'Brun', 'suzanne.brun@arcadiafinance.com', '+33 6 10 00 00 79', 'suzanne.brun', 'bola_target'),
('Maurice', 'Menard', 'maurice.menard@arcadiafinance.com', '+33 6 10 00 00 80', 'maurice.menard', 'bola_target'),
('Renee', 'Germain', 'renee.germain@arcadiafinance.com', '+33 6 10 00 00 81', 'renee.germain', 'bola_target'),
('Louis', 'Prevost', 'louis.prevost@arcadiafinance.com', '+33 6 10 00 00 82', 'louis.prevost', 'bola_target'),
('Raymonde', 'Marechal', 'raymonde.marechal@arcadiafinance.com', '+33 6 10 00 00 83', 'raymonde.marechal', 'bola_target'),
('Fernand', 'Charrier', 'fernand.charrier@arcadiafinance.com', '+33 6 10 00 00 84', 'fernand.charrier', 'bola_target'),
('Jeannine', 'Tessier', 'jeannine.tessier@arcadiafinance.com', '+33 6 10 00 00 85', 'jeannine.tessier', 'bola_target'),
('Gaston', 'Lefevre', 'gaston.lefevre@arcadiafinance.com', '+33 6 10 00 00 86', 'gaston.lefevre', 'bola_target'),
('Yvonne', 'Courtois', 'yvonne.courtois@arcadiafinance.com', '+33 6 10 00 00 87', 'yvonne.courtois', 'bola_target'),
('Edouard', 'Delorme', 'edouard.delorme@arcadiafinance.com', '+33 6 10 00 00 88', 'edouard.delorme', 'bola_target'),
('Henriette', 'Gillet', 'henriette.gillet@arcadiafinance.com', '+33 6 10 00 00 89', 'henriette.gillet', 'bola_target'),
('Gustave', 'Lecomte', 'gustave.lecomte@arcadiafinance.com', '+33 6 10 00 00 90', 'gustave.lecomte', 'bola_target'),
('Marcelle', 'Leduc', 'marcelle.leduc@arcadiafinance.com', '+33 6 10 00 00 91', 'marcelle.leduc', 'bola_target'),
('Emile', 'Bouchard', 'emile.bouchard@arcadiafinance.com', '+33 6 10 00 00 92', 'emile.bouchard', 'bola_target'),
('Georgette', 'Chevallier', 'georgette.chevallier@arcadiafinance.com', '+33 6 10 00 00 93', 'georgette.chevallier', 'bola_target'),
('Leon', 'Pelletier', 'leon.pelletier@arcadiafinance.com', '+33 6 10 00 00 94', 'leon.pelletier', 'bola_target'),
('Gilberte', 'Lamy', 'gilberte.lamy@arcadiafinance.com', '+33 6 10 00 00 95', 'gilberte.lamy', 'bola_target'),
('Armand', 'Fleury', 'armand.fleury@arcadiafinance.com', '+33 6 10 00 00 96', 'armand.fleury', 'bola_target'),
('Marguerite', 'Chauvet', 'marguerite.chauvet@arcadiafinance.com', '+33 6 10 00 00 97', 'marguerite.chauvet', 'bola_target'),
('Lucien', 'Bouvet', 'lucien.bouvet@arcadiafinance.com', '+33 6 10 00 00 98', 'lucien.bouvet', 'bola_target'),
('Germaine', 'Lepage', 'germaine.lepage@arcadiafinance.com', '+33 6 10 00 00 99', 'germaine.lepage', 'bola_target'),
('Fernande', 'Pelletier', 'fernande.pelletier@arcadiafinance.com', '+33 6 10 00 01 00', 'fernande.pelletier', 'bola_target');

-- VIRTUAL ACCOUNTS (used internally)
-- ─────────────────────────────────────────
-- A system user is needed to hold virtual accounts
INSERT IGNORE INTO users (id, name, surname, email, phone, username, password) VALUES
(99, 'System', 'Arcadia', 'system@arcadiafinance.internal', '+33 7 45 67 89 99', 'system', 'not-a-real-password');

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
('chatbot_system_prompt', 'You are Aria, a helpful virtual assistant for Arcadia Finance. You help clients with questions about their accounts, transfers, and banking services. You have access to two tools: use get_stock_price whenever a user asks about the price or value of a stock or company; use get_account_balance whenever a user asks about their account balance or how much money they have (optionally filtered by account type: checking, savings, or investment). Always use the appropriate tool to give accurate, live answers. Be concise, professional, and friendly.'),
('calypso_enabled', 'false'),
('calypso_url',     'https://www.us1.calypsoai.app');
