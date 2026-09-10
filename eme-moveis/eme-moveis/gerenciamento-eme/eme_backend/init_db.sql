-- ============================================================
-- Script de criação do banco de dados emebd
-- Executar este script no MySQL para criar todas as tabelas
-- ============================================================

CREATE DATABASE IF NOT EXISTS emebd
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;
USE emebd;

-- Crie o usuário MySQL da aplicação fora deste script e configure o .env.
-- Exemplo local:
-- CREATE USER 'eme_user'@'localhost' IDENTIFIED BY 'SENHA_FORTE_AQUI';
-- GRANT ALL PRIVILEGES ON emebd.* TO 'eme_user'@'localhost';
-- FLUSH PRIVILEGES;

-- ── Usuários ────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS users (
    id          VARCHAR(36)     PRIMARY KEY,
    username    VARCHAR(100)    NOT NULL UNIQUE,
    name        VARCHAR(200)    NOT NULL,
    email       VARCHAR(200)    NOT NULL UNIQUE,
    role        ENUM('ADMIN', 'GERENTE', 'ESTOQUE') NOT NULL DEFAULT 'ESTOQUE',
    password    VARCHAR(255)    NOT NULL,
    avatar      VARCHAR(500)    NULL,
    created_at  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ── Clientes ────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS clients (
    id          VARCHAR(36)     PRIMARY KEY,
    name        VARCHAR(200)    NOT NULL,
    email       VARCHAR(200)    NOT NULL,
    phone       VARCHAR(30)     NOT NULL,
    cpf_cnpj    VARCHAR(20)     NOT NULL UNIQUE,
    address     TEXT            NOT NULL,
    created_at  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ── Projetos ────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS projects (
    id          VARCHAR(36)     PRIMARY KEY,
    title       VARCHAR(300)    NOT NULL,
    client_id   VARCHAR(36)     NOT NULL,
    description TEXT            NOT NULL,
    status      ENUM('ORCAMENTO', 'PROJETADO', 'PRODUCAO', 'MONTAGEM', 'CONCLUIDO')
                                NOT NULL DEFAULT 'ORCAMENTO',
    value       DECIMAL(12, 2)  NOT NULL DEFAULT 0,
    deadline    DATE            NOT NULL,
    steps       JSON            NULL,
    created_at  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_project_client FOREIGN KEY (client_id) REFERENCES clients(id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ── Registros Financeiros ───────────────────────────────────

CREATE TABLE IF NOT EXISTS financial_records (
    id          VARCHAR(36)     PRIMARY KEY,
    description VARCHAR(500)    NOT NULL,
    type        ENUM('ENTRADA', 'SAIDA') NOT NULL,
    category    VARCHAR(100)    NOT NULL,
    amount      DECIMAL(12, 2)  NOT NULL,
    date        DATE            NOT NULL,
    project_id  VARCHAR(36)     NULL,
    status      ENUM('PAGO', 'PENDENTE') NOT NULL DEFAULT 'PENDENTE',
    CONSTRAINT fk_financial_project FOREIGN KEY (project_id) REFERENCES projects(id)
        ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ── Categorias (Estoque e Financeiro) ───────────────────────
-- A mesma tabela serve para os dois contextos, diferenciados por
-- category_type. Os nomes só precisam ser únicos dentro do mesmo tipo
-- (ex.: pode existir "Outros" tanto em STOCK quanto em FINANCIAL).

CREATE TABLE IF NOT EXISTS categories (
    id            VARCHAR(36)     PRIMARY KEY,
    name          VARCHAR(200)    NOT NULL,
    description   TEXT            NULL,
    category_type ENUM('STOCK', 'FINANCIAL') NOT NULL DEFAULT 'STOCK',
    CONSTRAINT uq_category_name_type UNIQUE (name, category_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Categorias financeiras pré-existentes (antes eram um Enum fixo no
-- código; migradas para registros editáveis nesta tabela).
INSERT INTO categories (id, name, category_type) VALUES
    (UUID(), 'Venda de Móveis', 'FINANCIAL'),
    (UUID(), 'Massa / Madeira', 'FINANCIAL'),
    (UUID(), 'Ferragens', 'FINANCIAL'),
    (UUID(), 'Salários', 'FINANCIAL'),
    (UUID(), 'Aluguel', 'FINANCIAL'),
    (UUID(), 'Impostos', 'FINANCIAL'),
    (UUID(), 'Serviços', 'FINANCIAL'),
    (UUID(), 'Outros', 'FINANCIAL')
ON DUPLICATE KEY UPDATE name = name;


-- ── Itens de Estoque ────────────────────────────────────────

CREATE TABLE IF NOT EXISTS stock_items (
    id          VARCHAR(36)     PRIMARY KEY,
    name        VARCHAR(300)    NOT NULL,
    sku         VARCHAR(100)    NOT NULL UNIQUE,
    category_id VARCHAR(36)     NOT NULL,
    quantity    DECIMAL(12, 2)  NOT NULL DEFAULT 0,
    min_quantity DECIMAL(12, 2) NOT NULL DEFAULT 0,
    unit        VARCHAR(30)     NOT NULL,
    price       DECIMAL(12, 2)  NOT NULL DEFAULT 0,
    supplier    VARCHAR(300)    NOT NULL,
    CONSTRAINT fk_stock_category FOREIGN KEY (category_id) REFERENCES categories(id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ── Movimentações de Estoque ────────────────────────────────

CREATE TABLE IF NOT EXISTS stock_movements (
    id          VARCHAR(36)     PRIMARY KEY,
    item_id     VARCHAR(36)     NOT NULL,
    type        ENUM('ENTRADA', 'SAIDA') NOT NULL,
    quantity    DECIMAL(12, 2)  NOT NULL,
    reason      VARCHAR(500)    NOT NULL,
    created_by  VARCHAR(200)    NOT NULL,
    date        DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_movement_item FOREIGN KEY (item_id) REFERENCES stock_items(id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ============================================================
-- Após criar as tabelas, execute create_admin.py para inserir
-- o primeiro usuário administrador via script Python.
-- IMPORTANTE: Trocar a senha após o primeiro login!
-- ============================================================
