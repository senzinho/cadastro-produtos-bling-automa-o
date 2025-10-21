-- ==================== CRIAR BANCO DE DADOS ====================
CREATE DATABASE IF NOT EXISTS controle_acessos 
CHARACTER SET utf8mb4 
COLLATE utf8mb4_unicode_ci;

USE controle_acessos;

-- ==================== TABELA DE USUÁRIOS ====================
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    role VARCHAR(20) DEFAULT 'user' COMMENT 'admin ou user',
    active TINYINT(1) DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_login DATETIME NULL,
    INDEX idx_email (email),
    INDEX idx_role (role),
    INDEX idx_active (active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ==================== TABELA DE MARKETPLACES ====================
CREATE TABLE IF NOT EXISTS marketplaces (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    commission DECIMAL(5,4) NOT NULL COMMENT 'Taxa de comissão (ex: 0.1200 = 12%)',
    active TINYINT(1) DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_active (active),
    INDEX idx_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ==================== TABELA DE CONFIGURAÇÕES DE KITS ====================
CREATE TABLE IF NOT EXISTS kit_configs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    kits_data TEXT NOT NULL COMMENT 'JSON com os kits: [{"name":"Kit 2","multiplier":2}]',
    active TINYINT(1) DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_active (active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ==================== TABELA DE CÁLCULOS ====================
CREATE TABLE IF NOT EXISTS calculations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    calculation_type VARCHAR(50) NOT NULL COMMENT 'price ou cost',
    marketplace_id INT NULL,
    cost DECIMAL(10,2) NULL,
    price DECIMAL(10,2) NULL,
    margin DECIMAL(10,2) NULL COMMENT 'Margem de lucro em %',
    tax_rate DECIMAL(10,4) NULL COMMENT 'Taxa de imposto (ex: 0.1000 = 10%)',
    result_data TEXT NULL COMMENT 'JSON com resultado completo do cálculo',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (marketplace_id) REFERENCES marketplaces(id) ON DELETE SET NULL,
    INDEX idx_user_id (user_id),
    INDEX idx_calculation_type (calculation_type),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ==================== TABELA DE HISTÓRICO DE LOGIN ====================
CREATE TABLE IF NOT EXISTS login_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NULL,
    ip_address VARCHAR(50) NULL,
    user_agent VARCHAR(255) NULL,
    success TINYINT(1) DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_user_id (user_id),
    INDEX idx_success (success),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ==================== INSERIR USUÁRIOS PADRÃO ====================
INSERT INTO users (name, email, password, role, active) VALUES
('Admin Sistema', 'admin@sistema.com', 'scrypt:32768:8:1$dFqB4xKzQHGP2nWq$ef4de0eb7e0ae5d1c0f9f8d1c0c8e0b5f3e8b4d2e9a6f1c8b5d3e7a9f2c6b8d4e1a7f9c3b6d8e2a5f7c9b4d6e3a8f1c5b7d9e4a6f2c8b3d5e7a9f1', 'admin', 1),
('João Silva', 'user@sistema.com', 'scrypt:32768:8:1$dFqB4xKzQHGP2nWq$ef4de0eb7e0ae5d1c0f9f8d1c0c8e0b5f3e8b4d2e9a6f1c8b5d3e7a9f2c6b8d4e1a7f9c3b6d8e2a5f7c9b4d6e3a8f1c5b7d9e4a6f2c8b3d5e7a9f1', 'user', 1),
('Maria Santos', 'maria@sistema.com', 'scrypt:32768:8:1$dFqB4xKzQHGP2nWq$ef4de0eb7e0ae5d1c0f9f8d1c0c8e0b5f3e8b4d2e9a6f1c8b5d3e7a9f2c6b8d4e1a7f9c3b6d8e2a5f7c9b4d6e3a8f1c5b7d9e4a6f2c8b3d5e7a9f1', 'user', 1),
('Pedro Oliveira', 'pedro@sistema.com', 'scrypt:32768:8:1$dFqB4xKzQHGP2nWq$ef4de0eb7e0ae5d1c0f9f8d1c0c8e0b5f3e8b4d2e9a6f1c8b5d3e7a9f2c6b8d4e1a7f9c3b6d8e2a5f7c9b4d6e3a8f1c5b7d9e4a6f2c8b3d5e7a9f1', 'admin', 0);

-- ==================== INSERIR MARKETPLACES PADRÃO ====================
INSERT INTO marketplaces (name, commission, active) VALUES
('Mercado Livre', 0.1200, 1),
('Americanas', 0.1600, 1),
('Magalu', 0.1800, 1),
('Via Varejo', 0.1700, 1),
('Droga Raia', 0.2200, 1),
('Tray', 0.0500, 1),
('Tray + 20%', 0.0500, 1),
('Digigrow', 0.1800, 1),
('Shopee', 0.2000, 1),
('Shopee x2', 0.2000, 1);

-- ==================== INSERIR CONFIGURAÇÕES DE KITS PADRÃO ====================
INSERT INTO kit_configs (name, kits_data, active) VALUES
('Kits de 2, 3 e 6', '[{"name":"Kit 2","multiplier":2},{"name":"Kit 3","multiplier":3},{"name":"Kit 6","multiplier":6}]', 1),
('Kits de 4, 12 e 24', '[{"name":"Kit 4","multiplier":4},{"name":"Kit 12","multiplier":12},{"name":"Kit 24","multiplier":24}]', 1),
('Kits de 5, 10 e 20', '[{"name":"Kit 5","multiplier":5},{"name":"Kit 10","multiplier":10},{"name":"Kit 20","multiplier":20}]', 1),
('Kits de 8, 16 e 18', '[{"name":"Kit 8","multiplier":8},{"name":"Kit 16","multiplier":16},{"name":"Kit 18","multiplier":18}]', 1);

-- ==================== VERIFICAR DADOS INSERIDOS ====================
SELECT 'Usuários cadastrados:' as Info;
SELECT id, name, email, role, active FROM users;

SELECT 'Marketplaces cadastrados:' as Info;
SELECT id, name, commission, active FROM marketplaces;

SELECT 'Configurações de Kits:' as Info;
SELECT id, name, active FROM kit_configs;