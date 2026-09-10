-- ============================================================
-- Migração: Módulo de Agenda Operacional e Notificações
-- Execute UMA VEZ no banco já existente.
-- Quem criar o banco do zero com init_db.sql não precisa rodar.
-- ============================================================

USE emebd;

-- ── Eventos de Agenda ───────────────────────────────────────

CREATE TABLE IF NOT EXISTS calendar_events (
    id              VARCHAR(36)     PRIMARY KEY,
    title           VARCHAR(300)    NOT NULL,
    description     TEXT            NULL,
    type            ENUM(
                        'MEDICAO',
                        'REUNIAO_CLIENTE',
                        'APROVACAO_PROJETO',
                        'PRODUCAO',
                        'MONTAGEM',
                        'ENTREGA',
                        'ASSISTENCIA_TECNICA',
                        'PERSONALIZADO'
                    ) NOT NULL DEFAULT 'PERSONALIZADO',
    status          ENUM(
                        'AGENDADO',
                        'CONFIRMADO',
                        'EM_ANDAMENTO',
                        'CONCLUIDO',
                        'CANCELADO'
                    ) NOT NULL DEFAULT 'AGENDADO',
    start_date      DATE            NOT NULL,
    start_time      TIME            NULL,
    end_date        DATE            NULL,
    end_time        TIME            NULL,
    project_id      VARCHAR(36)     NULL,
    client_id       VARCHAR(36)     NULL,
    assigned_user_id VARCHAR(36)    NULL,
    observations    TEXT            NULL,
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_event_project FOREIGN KEY (project_id) REFERENCES projects(id)
        ON DELETE SET NULL,
    CONSTRAINT fk_event_client FOREIGN KEY (client_id) REFERENCES clients(id)
        ON DELETE SET NULL,
    CONSTRAINT fk_event_user FOREIGN KEY (assigned_user_id) REFERENCES users(id)
        ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- ── Notificações ────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS notifications (
    id          VARCHAR(36)     PRIMARY KEY,
    title       VARCHAR(300)    NOT NULL,
    message     TEXT            NOT NULL,
    type        ENUM(
                    'PRAZO_PROJETO',
                    'EVENTO_HOJE',
                    'EVENTO_AMANHA',
                    'PROJETO_ATRASADO',
                    'ESTOQUE_BAIXO',
                    'GERAL'
                ) NOT NULL DEFAULT 'GERAL',
    read_at     DATETIME        NULL,
    user_id     VARCHAR(36)     NULL,
    event_id    VARCHAR(36)     NULL,
    project_id  VARCHAR(36)     NULL,
    created_at  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_notif_user FOREIGN KEY (user_id) REFERENCES users(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_notif_event FOREIGN KEY (event_id) REFERENCES calendar_events(id)
        ON DELETE SET NULL,
    CONSTRAINT fk_notif_project FOREIGN KEY (project_id) REFERENCES projects(id)
        ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================
-- Após rodar este script, reinicie o backend:
-- docker compose restart backend
-- ============================================================
