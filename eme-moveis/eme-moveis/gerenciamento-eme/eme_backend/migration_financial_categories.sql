-- ============================================================
-- Migração: categorias financeiras editáveis
-- Execute este script UMA VEZ em bancos que já existiam antes desta
-- atualização (ou seja, que já têm a tabela "categories" sem a coluna
-- category_type). Quem está criando o banco do zero com init_db.sql
-- não precisa rodar este arquivo.
-- ============================================================

USE emebd;

-- 1. Adiciona a coluna category_type, com tudo que já existe marcado como STOCK
--    (preserva as categorias de estoque atuais sem alterá-las).
ALTER TABLE categories
    ADD COLUMN category_type ENUM('STOCK', 'FINANCIAL') NOT NULL DEFAULT 'STOCK' AFTER description;

-- 2. Remove a constraint UNIQUE antiga (só por "name") e cria uma nova
--    composta por (name, category_type), permitindo nomes repetidos
--    entre os dois contextos (ex.: "Outros" em STOCK e em FINANCIAL).
ALTER TABLE categories DROP INDEX name;
ALTER TABLE categories ADD CONSTRAINT uq_category_name_type UNIQUE (name, category_type);

-- 3. Insere as categorias financeiras que antes eram um Enum fixo no
--    código Python, agora como registros editáveis.
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

-- Pronto. Após rodar este script, reinicie o backend (docker compose
-- restart backend, ou apenas reinicie o processo uvicorn no modo manual).
