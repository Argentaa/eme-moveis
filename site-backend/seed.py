"""Seed inicial: admin via SITE_ADMIN_USER/SITE_ADMIN_PASS (bcrypt) + dados exemplo."""
from __future__ import annotations

import json
import logging
import os

import bcrypt

from models import SiteProject, SiteSettings, SiteTimeline, SiteUser, db

log = logging.getLogger(__name__)

DEFAULT_SETTINGS = {
    "hero_image": "/images/banner-principal.jpg",
    "about_image": "/images/sobre-nos.jpg",
    "whatsapp": "55997175616",
    "instagram": "https://www.instagram.com/ememoveis",
    "address_json": {"cidade": "Frederico Westphalen/RS"},
}

EXAMPLE_PROJECTS = [
    {
        "title": "Cozinha Gourmet Anthracite",
        "category": "Cozinha",
        "image": "https://images.unsplash.com/photo-1556911223-e1534ecdb531?auto=format&fit=crop&q=80&w=1200",
        "album": [
            "https://images.unsplash.com/photo-1556911223-e1534ecdb531?auto=format&fit=crop&q=80&w=1200",
            "https://images.unsplash.com/photo-1556909114-f6e7ad7d3136?auto=format&fit=crop&q=80&w=1200",
            "https://images.unsplash.com/photo-1484154218962-a197022b5858?auto=format&fit=crop&q=80&w=1200",
        ],
        "description": "Cozinha com acabamento em tons escuros, ilha central e ferragens alemãs de alta performance.",
    },
    {
        "title": "Suíte Master Walk-in",
        "category": "Closet",
        "image": "https://images.unsplash.com/photo-1595428774751-267868770857?auto=format&fit=crop&q=80&w=1200",
        "album": [
            "https://images.unsplash.com/photo-1595428774751-267868770857?auto=format&fit=crop&q=80&w=1200",
            "https://images.unsplash.com/photo-1592075103427-4c4f346048d0?auto=format&fit=crop&q=80&w=1200",
        ],
        "description": "Closet planejado com divisões inteligentes, iluminação em LED embutida e nichos para calçados.",
    },
    {
        "title": "Home Office Executivo",
        "category": "Quarto",
        "image": "https://images.unsplash.com/photo-1518481612222-68bbe828ecd1?auto=format&fit=crop&q=80&w=1200",
        "album": [
            "https://images.unsplash.com/photo-1518481612222-68bbe828ecd1?auto=format&fit=crop&q=80&w=1200",
            "https://images.unsplash.com/photo-1497215728101-856f4ea42174?auto=format&fit=crop&q=80&w=1200",
        ],
        "description": "Ambiente focado em produtividade com mesa em L, painéis ripados e armários para organização.",
    },
    {
        "title": "Living Integrado",
        "category": "Sala",
        "image": "https://images.unsplash.com/photo-1586023492125-27b2c045efd7?auto=format&fit=crop&q=80&w=1200",
        "album": [
            "https://images.unsplash.com/photo-1586023492125-27b2c045efd7?auto=format&fit=crop&q=80&w=1200",
            "https://images.unsplash.com/photo-1554995207-c18c203602cb?auto=format&fit=crop&q=80&w=1200",
        ],
        "description": "Painel de TV com fundo em pedra e móveis suspensos em laca branca fosca.",
    },
    {
        "title": "Adega Gourmet Climatizada",
        "category": "Adega",
        "image": "https://images.unsplash.com/photo-1560185007-c5ca9d2c014d?auto=format&fit=crop&q=80&w=1200",
        "album": ["https://images.unsplash.com/photo-1560185007-c5ca9d2c014d?auto=format&fit=crop&q=80&w=1200"],
        "description": "Churrasqueira integrada com marcenaria naval e linda adega para vinhos selecionados.",
    },
    {
        "title": "Banheiro Spa",
        "category": "Banheiro",
        "image": "https://images.unsplash.com/photo-1552321554-5fefe8c9ef14?auto=format&fit=crop&q=80&w=1200",
        "album": ["https://images.unsplash.com/photo-1552321554-5fefe8c9ef14?auto=format&fit=crop&q=80&w=1200"],
        "description": "Gabinete suspenso com gavetões e espelheira com moldura em metal.",
    },
]

EXAMPLE_TIMELINE = [
    {
        "year": "2022",
        "title": "Fundação da eMe Móveis",
        "description": "Nascimento da eMe Móveis no Rio Grande do Sul, com foco inicial em cozinhas planejadas e painéis.",
        "image": "https://images.unsplash.com/photo-1540555700478-4be289fbecef?auto=format&fit=crop&q=80&w=600",
    },
    {
        "year": "2023",
        "title": "Primeiro móvel produzido",
        "description": "Entrega do primeiro dormitório completo com ferragens telescópicas e iluminação integrada de alto padrão.",
        "image": "https://images.unsplash.com/photo-1505691938895-1758d7feb511?auto=format&fit=crop&q=80&w=600",
    },
    {
        "year": "2024",
        "title": "Sede e show-room próprio",
        "description": "Inauguração de nossa sede em Frederico Westphalen/RS, apresentando as últimas tendências em acabamentos e MDF premium.",
        "image": "https://images.unsplash.com/photo-1497366216548-37526070297c?auto=format&fit=crop&q=80&w=600",
    },
    {
        "year": "2026",
        "title": "Mais de 100 Projetos Entregues",
        "description": "Marca histórica de projetos entregues e clientes satisfeitos em nossa região, unindo qualidade e exclusividade.",
        "image": "https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&q=80&w=600",
    },
]


def _hash(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def seed_initial_data() -> None:
    """Cria admin (env) e dados exemplo apenas se as tabelas estiverem vazias."""
    admin_user = os.environ.get("SITE_ADMIN_USER", "").strip()
    admin_pass = os.environ.get("SITE_ADMIN_PASS", "")

    if SiteUser.query.count() == 0:
        if admin_user and admin_pass:
            db.session.add(SiteUser(username=admin_user, password_hash=_hash(admin_pass)))
            db.session.commit()
            log.info("Usuário admin inicial criado.")
        else:
            log.warning("SITE_ADMIN_USER/SITE_ADMIN_PASS ausentes: nenhum admin criado (defina as variáveis).")
    else:
        log.info("Tabela site_users já possui registros; seed de admin ignorado.")

    if SiteProject.query.count() == 0:
        for p in EXAMPLE_PROJECTS:
            db.session.add(SiteProject(**p))
        db.session.commit()
        log.info("Projetos exemplo inseridos.")

    if SiteTimeline.query.count() == 0:
        for t in EXAMPLE_TIMELINE:
            db.session.add(SiteTimeline(**t))
        db.session.commit()
        log.info("Timeline exemplo inserida.")

    if SiteSettings.query.count() == 0:
        db.session.add(SiteSettings(id=1, **DEFAULT_SETTINGS))
        db.session.commit()
        log.info("Settings iniciais inseridas.")
