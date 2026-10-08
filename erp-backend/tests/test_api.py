"""Cobertura: login, clients, projects, financial, stock e calendar CRUD."""
import os
from datetime import date, timedelta

import pytest

os.environ.setdefault("APP_ENV", "test")

from app import create_app  # noqa: E402
from app.auth import hash_password  # noqa: E402
from app.extensions import db  # noqa: E402
from app.models.models import User  # noqa: E402


@pytest.fixture()
def client():
    app = create_app("test")
    app.config.update(TESTING=True)
    with app.test_client() as c:
        with app.app_context():
            db.session.query(User).filter_by(username="admin").delete()
            db.session.add(
                User(
                    username="admin",
                    name="Admin",
                    email="admin@test.local",
                    role="ADMIN",
                    password=hash_password("admin12345"),
                )
            )
            db.session.commit()
        yield c


def _login(client):
    r = client.post("/api/auth/login", json={"username": "admin", "password": "admin12345"})
    assert r.status_code == 200, r.get_data(as_text=True)
    body = r.get_json()
    assert "token" in body and "user" in body
    return {"Authorization": f"Bearer {body['token']}"}


def test_login_ok_e_me(client):
    headers = _login(client)
    r = client.get("/api/auth/me", headers=headers)
    assert r.status_code == 200
    assert r.get_json()["username"] == "admin"


def test_login_invalido_401(client):
    r = client.post("/api/auth/login", json={"username": "admin", "password": "errada"})
    assert r.status_code == 401


def test_sem_token_401(client):
    assert client.get("/api/auth/me").status_code == 401
    assert client.get("/api/clients").status_code == 401


def test_clients_crud(client):
    h = _login(client)
    r = client.post(
        "/api/clients",
        headers=h,
        json={"name": "Cliente X", "cpf_cnpj": "123", "email": "x@x.com", "phone": "1", "address": "Rua"},
    )
    assert r.status_code == 201, r.get_data(as_text=True)
    cid = r.get_json()["id"]

    assert client.get("/api/clients", headers=h).status_code == 200
    assert client.get(f"/api/clients/{cid}", headers=h).status_code == 200

    r = client.put(f"/api/clients/{cid}", headers=h, json={"phone": "999"})
    assert r.status_code == 200 and r.get_json()["phone"] == "999"

    assert client.delete(f"/api/clients/{cid}", headers=h).status_code == 200
    assert client.get(f"/api/clients/{cid}", headers=h).status_code == 404


def test_projects_crud(client):
    h = _login(client)
    cid = client.post("/api/clients", headers=h, json={"name": "Cli P", "cpf_cnpj": "p1"}).get_json()["id"]

    r = client.post(
        "/api/projects",
        headers=h,
        json={"title": "Proj 1", "client_id": cid, "description": "d", "status": "ORCAMENTO",
              "value": 1000, "deadline": "2030-01-01", "steps": []},
    )
    assert r.status_code == 201, r.get_data(as_text=True)
    pid = r.get_json()["id"]

    assert client.get("/api/projects", headers=h).status_code == 200
    assert client.get(f"/api/projects/{pid}", headers=h).status_code == 200
    assert client.get("/api/projects/overdue", headers=h).status_code == 200

    r = client.put(f"/api/projects/{pid}/status", headers=h, json={"status": "PRODUCAO"})
    assert r.status_code == 200 and r.get_json()["status"] == "PRODUCAO"

    r = client.put(f"/api/projects/{pid}", headers=h, json={"title": "Proj 1b"})
    assert r.status_code == 200 and r.get_json()["title"] == "Proj 1b"

    assert client.delete(f"/api/projects/{pid}", headers=h).status_code == 200


def test_financial_crud(client):
    h = _login(client)
    r = client.post(
        "/api/financial",
        headers=h,
        json={"description": "Venda", "type": "ENTRADA", "category": "Vendas",
              "amount": 500, "date": "2026-01-10", "status": "PENDENTE", "due_date": "2026-01-20"},
    )
    assert r.status_code == 201, r.get_data(as_text=True)
    fid = r.get_json()["id"]

    assert client.get("/api/financial", headers=h).status_code == 200
    assert client.get("/api/financial/upcoming", headers=h).status_code == 200
    assert client.get("/api/financial/overdue", headers=h).status_code == 200
    assert client.get(f"/api/financial/{fid}/receipt", headers=h).status_code == 200

    r = client.put(f"/api/financial/{fid}", headers=h, json={"status": "PAGO"})
    assert r.status_code == 200 and r.get_json()["status"] == "PAGO"

    assert client.delete(f"/api/financial/{fid}", headers=h).status_code == 200


def test_recurring_process_due(client):
    h = _login(client)
    r = client.post(
        "/api/financial/recurring",
        headers=h,
        json={"description": "Aluguel", "type": "SAIDA", "category": "Fixo",
              "amount": 100, "frequency": "MENSAL", "start_date": "2020-01-01", "next_date": "2020-01-01"},
    )
    assert r.status_code == 201, r.get_data(as_text=True)
    rid = r.get_json()["id"]
    assert client.get("/api/financial/recurring", headers=h).status_code == 200
    r = client.post("/api/financial/recurring/process-due", headers=h)
    assert r.status_code == 200 and r.get_json()["processed"] >= 1
    assert client.delete(f"/api/financial/recurring/{rid}", headers=h).status_code == 200


def test_stock_crud(client):
    h = _login(client)
    cat = client.post("/api/stock/categories", headers=h, json={"name": "Madeira", "category_type": "STOCK"}).get_json()
    assert client.get("/api/stock/categories/all", headers=h).status_code == 200

    r = client.post(
        "/api/stock",
        headers=h,
        json={"name": "MDF", "sku": "MDF-01", "category_id": cat["id"],
              "quantity": 10, "min_quantity": 2, "unit": "ch", "price": 150, "supplier": "Forn"},
    )
    assert r.status_code == 201, r.get_data(as_text=True)
    item_id = r.get_json()["id"]

    assert client.get("/api/stock", headers=h).status_code == 200

    r = client.post("/api/stock/movements", headers=h,
                    json={"item_id": item_id, "type": "ENTRADA", "quantity": 5, "reason": "compra"})
    assert r.status_code == 201, r.get_data(as_text=True)
    assert client.get("/api/stock/movements/history", headers=h).status_code == 200

    r = client.put(f"/api/stock/{item_id}", headers=h, json={"price": 160})
    assert r.status_code == 200 and r.get_json()["price"] == 160.0

    assert client.delete(f"/api/stock/{item_id}", headers=h).status_code == 200
    assert client.delete(f"/api/stock/categories/{cat['id']}", headers=h).status_code == 200


def test_calendar_crud(client):
    h = _login(client)
    r = client.post(
        "/api/calendar",
        headers=h,
        json={"title": "Medicao", "type": "MEDICAO", "status": "AGENDADO",
              "start_date": "2026-05-01", "start_time": "09:00"},
    )
    assert r.status_code == 201, r.get_data(as_text=True)
    eid = r.get_json()["id"]

    assert client.get("/api/calendar", headers=h).status_code == 200
    assert client.get("/api/calendar/today", headers=h).status_code == 200
    assert client.get("/api/calendar/week", headers=h).status_code == 200

    r = client.put(f"/api/calendar/{eid}", headers=h, json={"status": "CONFIRMADO"})
    assert r.status_code == 200 and r.get_json()["status"] == "CONFIRMADO"

    assert client.get("/api/calendar/notifications", headers=h).status_code == 200
    assert client.get("/api/calendar/notifications/count", headers=h).status_code == 200
    assert client.post("/api/calendar/notifications/generate-alerts", headers=h).status_code == 200

    assert client.delete(f"/api/calendar/{eid}", headers=h).status_code == 200


def test_reports_e_funnel(client):
    h = _login(client)
    for path in ("/api/reports/financial", "/api/reports/clients", "/api/reports/projects",
                 "/api/reports/stock"):
        r = client.get(path, headers=h)
        assert r.status_code == 200, path
        assert "rows" in r.get_json()
    r = client.get("/api/reports/dre", headers=h)
    assert r.status_code == 200
    assert "rows" in r.get_json()
    r = client.get("/api/reports/cash-flow", headers=h)
    assert r.status_code == 200
    assert "rows" in r.get_json()
    r = client.get("/api/reports/crm", headers=h)
    assert r.status_code == 200
    assert "negociacoes" in r.get_json()
    assert client.get("/api/reports/financial?format=xlsx", headers=h).status_code == 200
    assert client.get("/api/funnel-columns?type=CRM", headers=h).status_code == 200
    r = client.put("/api/funnel-columns/prospeccao?type=CRM", headers=h, json={"label": "Prospec"})
    assert r.status_code == 200


def test_project_steps_e_financial_shapes(client):
    h = _login(client)
    cid = client.post("/api/clients", headers=h, json={"name": "Cli S", "cpf_cnpj": "s1"}).get_json()["id"]
    pid = client.post(
        "/api/projects", headers=h,
        json={"title": "Proj S", "client_id": cid, "deadline": "2030-01-01", "steps": []},
    ).get_json()["id"]
    r = client.put(f"/api/projects/{pid}/steps", headers=h,
                   json={"steps": [{"id": "1", "label": "Etapa 1", "completed": True}]})
    assert r.status_code == 200 and r.get_json()["steps"][0]["completed"] is True

    r = client.get("/api/financial/upcoming?days=7", headers=h)
    assert r.status_code == 200
    body = r.get_json()
    assert set(("receivables", "payables", "total_receivables", "total_payables", "days")) <= set(body)

    r = client.get("/api/financial/overdue", headers=h)
    assert r.status_code == 200
    assert set(("clients", "grand_total")) <= set(r.get_json())

    r = client.get("/api/projects/overdue", headers=h)
    assert r.status_code == 200 and isinstance(r.get_json(), list)


def test_client_campaign_e_modelos_novos(client):
    h = _login(client)
    r = client.post("/api/clients", headers=h, json={"name": "Cliente Camp", "cpf_cnpj": "9999"})
    assert r.status_code == 201, r.get_data(as_text=True)
    cid = r.get_json()["id"]
    with client.application.app_context():
        from app.models.models import Client as ClientModel
        c = db.session.get(ClientModel, cid)
        c.campaign = "Parceria Construtora"
        c.lead_source = "Indicação de Arquiteto"
        db.session.commit()
    body = client.get(f"/api/clients/{cid}", headers=h).get_json()
    assert body["campaign"] == "Parceria Construtora"
    assert body["lead_source"] == "Indicação de Arquiteto"


def test_modelos_novos_serializacao_e_cascata(client):
    h = _login(client)
    cid = client.post("/api/clients", headers=h, json={"name": "Cliente Modelos", "cpf_cnpj": "7777"}).get_json()["id"]
    with client.application.app_context():
        from app.models.models import Attachment, Campaign, Interaction, LeadSource
        src = LeadSource(name="Indicacao Arquiteto"); db.session.add(src)
        camp = Campaign(name="Parceria Construtora"); db.session.add(camp)
        inter = Interaction(client_id=cid, type="CONVERSA", content="Cliente pediu proposta", automatic=False)
        db.session.add(inter)
        att = Attachment(client_id=cid, filename="proposta.pdf", stored_name="abc123.pdf", mime_type="application/pdf", size=1024)
        db.session.add(att)
        db.session.commit()
        assert src.to_dict()["name"] == "Indicacao Arquiteto"
        assert camp.to_dict()["name"] == "Parceria Construtora"
        d_inter = inter.to_dict()
        assert d_inter["client_id"] == cid and d_inter["type"] == "CONVERSA" and d_inter["automatic"] is False
        d_att = att.to_dict()
        assert d_att["filename"] == "proposta.pdf" and d_att["size"] == 1024 and d_att["client_id"] == cid
        from app.models.models import Client as ClientModel
        c = db.session.get(ClientModel, cid)
        assert any(i.id == inter.id for i in c.interactions)
        assert any(a.id == att.id for a in c.attachments)
    # Guard do cadastro central: cliente com historico (interacao/anexo) nao e excluido.
    r = client.delete(f"/api/clients/{cid}", headers=h)
    assert r.status_code == 400, r.get_data(as_text=True)
    assert "interacao" in r.get_data(as_text=True).lower()
    with client.application.app_context():
        from app.models.models import Attachment as AttModel, Campaign as CampModel, Interaction as IntModel, LeadSource as SrcModel
        # registros preservados apos o bloqueio (cadastro central)
        assert db.session.get(IntModel, inter.id) is not None
        assert db.session.get(AttModel, att.id) is not None
        assert db.session.get(SrcModel, src.id) is not None    # tabela independente do cliente
        assert db.session.get(CampModel, camp.id) is not None  # tabela independente do cliente
    # limpeza direta via ORM para nao vazar entre testes
    with client.application.app_context():
        from app.models.models import Attachment as AttModel2, Interaction as IntModel2
        db.session.query(IntModel2).filter_by(client_id=cid).delete()
        db.session.query(AttModel2).filter_by(client_id=cid).delete()
        db.session.commit()


def test_client_supplier_fields_crud(client):
    h = _login(client)
    # cria cliente com campos de fornecedor
    r = client.post(
        "/api/clients", headers=h,
        json={"name": "Cliente Fornecedor", "cpf_cnpj": "sup-001",
              "is_supplier": True, "contact": "Joao", "category": "Madeira",
              "payment_terms": "30 dias", "avg_delivery_days": 5},
    )
    assert r.status_code == 201, r.get_data(as_text=True)
    body = r.get_json()
    assert body["is_supplier"] is True
    assert body["contact"] == "Joao"
    assert body["category"] == "Madeira"
    assert body["payment_terms"] == "30 dias"
    assert body["avg_delivery_days"] == 5
    cid = body["id"]

    # filtro is_supplier=1
    lst = client.get("/api/clients?is_supplier=1", headers=h).get_json()
    assert any(c["id"] == cid for c in lst)

    # cliente normal nao entra no filtro
    client.post("/api/clients", headers=h, json={"name": "Normal", "cpf_cnpj": "sup-002"})
    lst2 = client.get("/api/clients?is_supplier=1", headers=h).get_json()
    assert all(c["id"] != "sup-002" for c in lst2)
    assert all(c["is_supplier"] is True for c in lst2)

    # update campos
    r = client.put(f"/api/clients/{cid}", headers=h, json={"is_supplier": False, "avg_delivery_days": ""})
    assert r.status_code == 200, r.get_data(as_text=True)
    assert r.get_json()["is_supplier"] is False
    assert r.get_json()["avg_delivery_days"] is None

    # avg_delivery_days invalido -> 400
    r = client.put(f"/api/clients/{cid}", headers=h, json={"avg_delivery_days": -1})
    assert r.status_code == 400


def test_client_delete_guard(client):
    h = _login(client)
    cid = client.post("/api/clients", headers=h, json={"name": "Com Historico", "cpf_cnpj": "hist-001"}).get_json()["id"]
    r = client.post(
        "/api/projects", headers=h,
        json={"title": "Proj H", "client_id": cid, "status": "ORCAMENTO", "value": 100, "deadline": "2030-01-01", "steps": []},
    )
    assert r.status_code == 201, r.get_data(as_text=True)
    # delete bloqueado pelo guard
    r = client.delete(f"/api/clients/{cid}", headers=h)
    assert r.status_code == 400, r.get_data(as_text=True)
    assert "projeto" in r.get_data(as_text=True).lower()
    # cliente ainda existe
    assert client.get(f"/api/clients/{cid}", headers=h).status_code == 200

    # cliente sem historico pode ser excluido
    c2 = client.post("/api/clients", headers=h, json={"name": "Limpo", "cpf_cnpj": "hist-002"}).get_json()["id"]
    assert client.delete(f"/api/clients/{c2}", headers=h).status_code == 200


def test_vendors_merge(client):
    h = _login(client)
    # supplier legado
    s = client.post("/api/suppliers", headers=h, json={"name": "Madeireira Legada", "cnpj": "11.111", "category": "Madeira"}).get_json()
    # cliente-fornecedor (cria espelho em suppliers automaticamente)
    c = client.post(
        "/api/clients", headers=h,
        json={"name": "Cliente que vende", "cpf_cnpj": "22.222", "is_supplier": True, "contact": "Maria"},
    ).get_json()
    r = client.get("/api/vendors", headers=h)
    assert r.status_code == 200, r.get_data(as_text=True)
    rows = r.get_json()
    assert len(rows) >= 2
    by_name = {row["name"]: row for row in rows}
    assert "Madeireira Legada" in by_name and by_name["Madeireira Legada"]["source"] == "supplier"
    assert by_name["Madeireira Legada"]["id"] == s["id"]
    assert "Cliente que vende" in by_name and by_name["Cliente que vende"]["source"] == "client"
    # id do espelho e um suppliers.id (FK valida), ligado ao cliente
    mirror = by_name["Cliente que vende"]
    assert mirror["client_id"] == c["id"]
    assert mirror["id"] != c["id"]
    # espelho serve como supplier_id real em compras
    r = client.post(
        "/api/purchases", headers=h,
        json={"supplier_id": mirror["id"], "request_date": "2026-09-22",
              "items": [{"material_name": "MDF", "quantity": 2, "unit_price": 100}]},
    )
    assert r.status_code == 201, r.get_data(as_text=True)


def test_client_supplier_mirror_sync(client):
    h = _login(client)
    c = client.post(
        "/api/clients", headers=h,
        json={"name": "Espelho Sync", "cpf_cnpj": "33.333", "is_supplier": True,
              "contact": "Ana", "phone": "555", "category": "Ferragens"},
    ).get_json()
    # espelho criado
    rows = client.get("/api/vendors", headers=h).get_json()
    mirror = next(r for r in rows if r.get("client_id") == c["id"])
    assert mirror["contact"] == "Ana" and mirror["category"] == "Ferragens"
    # update do cliente sincroniza o espelho
    client.put(f"/api/clients/{c['id']}", headers=h, json={"contact": "Ana Nova", "phone": "999"})
    rows = client.get("/api/vendors", headers=h).get_json()
    mirror2 = next(r for r in rows if r.get("client_id") == c["id"])
    assert mirror2["id"] == mirror["id"]  # mesmo espelho, sem duplicar
    assert mirror2["contact"] == "Ana Nova" and mirror2["phone"] == "999"


def test_client_central_sem_funil_e_importacao(client):
    # Cadastro central: funnel_id null explicito cria cliente fora do funil.
    h = _login(client)
    c = client.post(
        "/api/clients", headers=h,
        json={"name": "Cadastro Central", "cpf_cnpj": "44.444", "funnel_id": None},
    ).get_json()
    assert c["funnel_id"] is None
    # Sem funnel_id (legado/Comercial) continua caindo no funil padrao.
    c2 = client.post(
        "/api/clients", headers=h,
        json={"name": "Via Comercial", "cpf_cnpj": "55.555"},
    ).get_json()
    assert c2["funnel_id"] is not None
    # Importacao pro funil: update com funnel real.
    r = client.put(f"/api/clients/{c['id']}", headers=h, json={"funnel_id": c2["funnel_id"], "funnel_status": "PROSPECCAO"})
    assert r.status_code == 200, r.get_data(as_text=True)
    assert r.get_json()["funnel_id"] == c2["funnel_id"]


def test_status_largo_cabe_no_banco(client):
    # Regressao: etapa com chave > 20 chars (ex.: PROPOSTA_EM_ELABORACAO, 22)
    # estourava VARCHAR(20) no Postgres (500). Modelo e migracao 0019 alargam p/ 60.
    from app.models.models import Client, Project
    assert Client.__table__.c.funnel_status.type.length == 60
    assert Project.__table__.c.status.type.length == 60
    h = _login(client)
    c = client.post(
        "/api/clients", headers=h,
        json={"name": "Chave Longa", "cpf_cnpj": "66.666", "funnel_id": None},
    ).get_json()
    long_key = "PROPOSTA_EM_ELABORACAO"
    assert len(long_key) > 20
    r = client.put(f"/api/clients/{c['id']}", headers=h, json={"funnel_status": long_key})
    assert r.status_code == 200, r.get_data(as_text=True)
    assert r.get_json()["funnel_status"] == long_key


def test_desvincular_do_funil_mantem_cadastro(client):
    # Botao Excluir no Comercial: so tira do funil (funnel_id null),
    # o cadastro continua existindo no central.
    h = _login(client)
    c = client.post(
        "/api/clients", headers=h,
        json={"name": "Sai do Funil", "cpf_cnpj": "77.777"},
    ).get_json()
    assert c["funnel_id"] is not None
    r = client.put(f"/api/clients/{c['id']}", headers=h, json={"funnel_id": None})
    assert r.status_code == 200, r.get_data(as_text=True)
    assert r.get_json()["funnel_id"] is None
    rows = client.get("/api/clients", headers=h).get_json()
    assert any(x["id"] == c["id"] for x in rows)


def test_seeds_fontes_e_campanhas_idempotente(client):
    with client.application.app_context():
        from app.extensions import db
        from app.models.models import (
            Campaign, LeadSource,
            ensure_default_campaigns, ensure_default_lead_sources,
        )
        ensure_default_lead_sources()
        ensure_default_campaigns()
        n_src = db.session.query(LeadSource).count()
        n_camp = db.session.query(Campaign).count()
        assert n_src >= 11
        assert n_camp >= 5
        ensure_default_lead_sources()
        ensure_default_campaigns()
        assert db.session.query(LeadSource).count() == n_src
        assert db.session.query(Campaign).count() == n_camp


def test_config_uploads(client):
    from app.config import Config
    assert Config.MAX_CONTENT_LENGTH == 50 * 1024 * 1024
    assert Config.UPLOAD_DIR
    assert client.application.config["MAX_CONTENT_LENGTH"] == 50 * 1024 * 1024


def test_nginx_aceita_mais_que_o_backend():
    """O nginx tem de aceitar MAIS que o backend, senao vira gargalo invisivel.

    Sem `client_max_body_size` vale o default do nginx, que e 1 MB: qualquer
    anexo maior volta 413 do nginx ANTES de chegar no Flask. Foi exatamente o
    bug relatado — a tela mostrava o limite do backend (25 MB) enquanto o
    bloqueio real era 1 MB do nginx. Este teste trava o invariante.
    """
    import re
    from pathlib import Path

    from app.config import Config

    conf = Path(__file__).resolve().parents[2] / "erp-frontend" / "nginx.conf"
    texto = conf.read_text(encoding="utf-8")
    m = re.search(r"client_max_body_size\s+(\d+)m", texto)
    assert m, "nginx.conf sem client_max_body_size: vale o default de 1 MB do nginx"
    limite_nginx = int(m.group(1)) * 1024 * 1024
    assert limite_nginx > Config.MAX_CONTENT_LENGTH, (
        f"nginx ({limite_nginx} bytes) tem de ser MAIOR que o backend "
        f"({Config.MAX_CONTENT_LENGTH} bytes), senao o nginx corta antes"
    )


def test_negotiation_value_soma_itens(client):
    h = _login(client)
    cid = client.post("/api/clients", headers=h, json={"name": "Cliente Itens", "cpf_cnpj": "8888"}).get_json()["id"]
    with client.application.app_context():
        from app.extensions import db
        from app.models.models import NegotiationItem
        db.session.add(NegotiationItem(client_id=cid, name="Cozinha", quantity=1, unit_price=8000))
        db.session.add(NegotiationItem(client_id=cid, name="Sala", quantity=1, unit_price=4500))
        db.session.commit()
    r = client.get("/api/clients", headers=h)
    row = next(c for c in r.get_json() if c["id"] == cid)
    assert row["negotiation_value"] == 12500.0


def test_lead_sources_crud(client):
    h = _login(client)
    r = client.post("/api/lead-sources", headers=h, json={"name": "Feira do Móvel"})
    assert r.status_code == 201, r.get_data(as_text=True)
    src_id = r.get_json()["id"]
    r2 = client.post("/api/lead-sources", headers=h, json={"name": "Feira do Móvel"})
    assert r2.status_code == 200
    names = [s["name"] for s in client.get("/api/lead-sources", headers=h).get_json()]
    assert "Feira do Móvel" in names
    assert client.delete("/api/lead-sources/" + src_id, headers=h).status_code == 200
    names2 = [s["name"] for s in client.get("/api/lead-sources", headers=h).get_json()]
    assert "Feira do Móvel" not in names2


def test_campaigns_crud(client):
    h = _login(client)
    r = client.post("/api/campaigns", headers=h, json={"name": "Campanha Natal"})
    assert r.status_code == 201, r.get_data(as_text=True)
    camp_id = r.get_json()["id"]
    r2 = client.post("/api/campaigns", headers=h, json={"name": "Campanha Natal"})
    assert r2.status_code == 200
    names = [c["name"] for c in client.get("/api/campaigns", headers=h).get_json()]
    assert "Campanha Natal" in names
    assert client.delete("/api/campaigns/" + camp_id, headers=h).status_code == 200
    names2 = [c["name"] for c in client.get("/api/campaigns", headers=h).get_json()]
    assert "Campanha Natal" not in names2


def test_update_funil_gera_interacao_automatica(client):
    h = _login(client)
    cid = client.post("/api/clients", headers=h, json={"name": "Cliente Log", "cpf_cnpj": "6666"}).get_json()["id"]
    r = client.put("/api/clients/" + cid, headers=h, json={"funnel_status": "ORCAMENTO"})
    assert r.status_code == 200, r.get_data(as_text=True)
    inter = client.get("/api/clients/" + cid + "/interactions", headers=h).get_json()
    assert len(inter) == 1
    assert inter[0]["automatic"] is True
    assert "ORCAMENTO" in inter[0]["content"]


def test_lead_source_nova_vira_opcao(client):
    h = _login(client)
    cid = client.post("/api/clients", headers=h, json={"name": "Cliente Fonte", "cpf_cnpj": "5555"}).get_json()["id"]
    r = client.put("/api/clients/" + cid, headers=h, json={"lead_source": "Feira do Móvel"})
    assert r.status_code == 200, r.get_data(as_text=True)
    names = [s["name"] for s in client.get("/api/lead-sources", headers=h).get_json()]
    assert "Feira do Móvel" in names


def test_client_detail_agregado(client):
    h = _login(client)
    cid = client.post("/api/clients", headers=h, json={"name": "Cliente Detail", "cpf_cnpj": "4444"}).get_json()["id"]
    with client.application.app_context():
        from app.extensions import db
        from app.models.models import Attachment, CalendarEvent, Interaction, NegotiationItem, Project
        db.session.add(Project(client_id=cid, title="Cozinha", status="ORCAMENTO", value=10000))
        db.session.add(CalendarEvent(client_id=cid, title="Ligação follow-up", start_date=__import__("datetime").date(2026, 9, 18)))
        db.session.add(Interaction(client_id=cid, type="CONVERSA", content="Cliente pediu proposta", automatic=False))
        db.session.add(Attachment(client_id=cid, filename="planta.pdf", stored_name="x1.pdf", size=10))
        db.session.add(NegotiationItem(client_id=cid, name="Cozinha", quantity=1, unit_price=8000))
        db.session.commit()
    d = client.get("/api/clients/" + cid + "/detail", headers=h).get_json()
    assert d["client"]["id"] == cid
    assert len(d["projects"]) == 1 and d["projects"][0]["title"] == "Cozinha"
    assert len(d["events"]) == 1 and "follow-up" in d["events"][0]["title"]
    assert len(d["interactions"]) == 1
    assert len(d["attachments"]) == 1
    assert len(d["items"]) == 1 and d["items"][0]["subtotal"] == 8000.0


def test_interactions_manual_crud(client):
    h = _login(client)
    cid = client.post("/api/clients", headers=h, json={"name": "Cliente Interacoes", "cpf_cnpj": "5544"}).get_json()["id"]
    r = client.post("/api/clients/" + cid + "/interactions", headers=h, json={"type": "CONVERSA", "content": "Cliente ligou pedindo prazo"})
    assert r.status_code == 201, r.get_data(as_text=True)
    body = r.get_json()
    assert body["automatic"] is False
    assert body["created_by"] == "admin"
    iid = body["id"]
    r2 = client.post("/api/clients/" + cid + "/interactions", headers=h, json={"type": "FOO", "content": "tipo desconhecido"})
    assert r2.status_code == 201
    assert r2.get_json()["type"] == "OBSERVACAO"
    r3 = client.post("/api/clients/" + cid + "/interactions", headers=h, json={"type": "CONVERSA", "content": "   "})
    assert r3.status_code == 400
    lst = client.get("/api/clients/" + cid + "/interactions", headers=h).get_json()
    assert len(lst) >= 2
    assert client.delete("/api/interactions/" + iid, headers=h).status_code == 200
    lst2 = client.get("/api/clients/" + cid + "/interactions", headers=h).get_json()
    assert all(i["id"] != iid for i in lst2)


def test_log_valor_estimado_e_upsert_vazio(client):
    h = _login(client)
    cid = client.post("/api/clients", headers=h, json={"name": "Cliente Valor", "cpf_cnpj": "5545"}).get_json()["id"]
    r = client.put("/api/clients/" + cid, headers=h, json={"estimated_value": 5000})
    assert r.status_code == 200, r.get_data(as_text=True)
    inter = client.get("/api/clients/" + cid + "/interactions", headers=h).get_json()
    assert any(i["type"] == "ORCAMENTO" and "não informado" in i["content"] for i in inter)
    client.put("/api/clients/" + cid, headers=h, json={"lead_source": ""})
    names = [s["name"] for s in client.get("/api/lead-sources", headers=h).get_json()]
    assert all(n != "" for n in names)


def test_interaction_cliente_inexistente_404(client):
    h = _login(client)
    r = client.post("/api/clients/id-inexistente/interactions", headers=h, json={"type": "CONVERSA", "content": "x"})
    assert r.status_code == 404


def test_calendar_filtro_por_cliente(client):
    h = _login(client)
    ca = client.post("/api/clients", headers=h, json={"name": "CA", "cpf_cnpj": "3331"}).get_json()["id"]
    cb = client.post("/api/clients", headers=h, json={"name": "CB", "cpf_cnpj": "3332"}).get_json()["id"]
    ev_a = client.post("/api/calendar", headers=h, json={"title": "Tarefa A", "start_date": "2026-09-18", "client_id": ca}).get_json()
    client.post("/api/calendar", headers=h, json={"title": "Tarefa B", "start_date": "2026-09-18", "client_id": cb})
    rows = client.get("/api/calendar", headers=h, query_string={"client_id": ca}).get_json()
    assert len(rows) == 1
    assert rows[0]["id"] == ev_a["id"]


def test_attachment_upload_download_delete(client, tmp_path):
    with client.application.app_context():
        client.application.config["UPLOAD_DIR"] = str(tmp_path)
    h = _login(client)
    cid = client.post("/api/clients", headers=h, json={"name": "Cliente Anexo", "cpf_cnpj": "2223"}).get_json()["id"]
    import io
    data = {"file": (io.BytesIO(b"%PDF-1.4 fake pdf"), "proposta.pdf")}
    r = client.post("/api/clients/" + cid + "/attachments", headers=h, data=data, content_type="multipart/form-data")
    assert r.status_code == 201, r.get_data(as_text=True)
    att = r.get_json()
    assert att["filename"] == "proposta.pdf"
    aid = att["id"]
    lst = client.get("/api/clients/" + cid + "/attachments", headers=h).get_json()
    assert len(lst) == 1
    d = client.get("/api/attachments/" + aid + "/download", headers=h)
    assert d.status_code == 200
    assert b"%PDF-1.4" in d.data
    assert "proposta.pdf" in d.headers.get("Content-Disposition", "")
    assert client.delete("/api/attachments/" + aid, headers=h).status_code == 200
    assert client.get("/api/attachments/" + aid + "/download", headers=h).status_code == 404


def test_attachment_cliente_inexistente_404(client, tmp_path):
    with client.application.app_context():
        client.application.config["UPLOAD_DIR"] = str(tmp_path)
    h = _login(client)
    import io
    r = client.post("/api/clients/id-x/attachments", headers=h, data={"file": (io.BytesIO(b"x"), "a.txt")}, content_type="multipart/form-data")
    assert r.status_code == 404


def test_attachment_sem_token_401(client, tmp_path):
    with client.application.app_context():
        client.application.config["UPLOAD_DIR"] = str(tmp_path)
    import io
    r = client.post("/api/clients/id-x/attachments", data={"file": (io.BytesIO(b"x"), "a.txt")}, content_type="multipart/form-data")
    assert r.status_code == 401


def test_attachment_filename_longo_truncado(client, tmp_path):
    with client.application.app_context():
        client.application.config["UPLOAD_DIR"] = str(tmp_path)
    h = _login(client)
    cid = client.post("/api/clients", headers=h, json={"name": "Cliente Nome Longo", "cpf_cnpj": "2224"}).get_json()["id"]
    import io
    long_name = "a" * 300 + ".pdf"
    r = client.post("/api/clients/" + cid + "/attachments", headers=h, data={"file": (io.BytesIO(b"%PDF"), long_name)}, content_type="multipart/form-data")
    assert r.status_code == 201, r.get_data(as_text=True)
    assert len(r.get_json()["filename"]) <= 255
    assert r.get_json()["filename"].endswith(".pdf")


def test_products_crud(client):
    h = _login(client)
    r = client.post("/api/products", headers=h, json={"name": "Closet", "default_price": 3500})
    assert r.status_code == 201, r.get_data(as_text=True)
    pid = r.get_json()["id"]
    r2 = client.post("/api/products", headers=h, json={"name": "Closet", "default_price": 3600})
    assert r2.status_code == 200
    assert r2.get_json()["default_price"] == 3600
    names = [p["name"] for p in client.get("/api/products", headers=h).get_json()]
    assert "Closet" in names
    assert client.delete("/api/products/" + pid, headers=h).status_code == 200
    names2 = [p["name"] for p in client.get("/api/products", headers=h).get_json()]
    assert "Closet" not in names2


def test_items_crud_e_valor(client):
    h = _login(client)
    cid = client.post("/api/clients", headers=h, json={"name": "Cliente Items API", "cpf_cnpj": "3111"}).get_json()["id"]
    prod = client.post("/api/products", headers=h, json={"name": "Cozinha", "default_price": 8000}).get_json()
    r1 = client.post("/api/clients/" + cid + "/items", headers=h, json={"product_id": prod["id"], "quantity": 1, "unit_price": 8000})
    assert r1.status_code == 201, r1.get_data(as_text=True)
    r2 = client.post("/api/clients/" + cid + "/items", headers=h, json={"name": "Closet", "quantity": 2, "unit_price": 1000})
    assert r2.status_code == 201
    assert r2.get_json()["product_id"] is not None
    cnames = [p["name"] for p in client.get("/api/products", headers=h).get_json()]
    assert "Closet" in cnames
    row = next(c for c in client.get("/api/clients", headers=h).get_json() if c["id"] == cid)
    assert row["negotiation_value"] == 8000 + 2000
    iid = r2.get_json()["id"]
    r3 = client.put("/api/items/" + iid, headers=h, json={"unit_price": 1500})
    assert r3.status_code == 200
    row2 = next(c for c in client.get("/api/clients", headers=h).get_json() if c["id"] == cid)
    assert row2["negotiation_value"] == 8000 + 3000
    assert client.delete("/api/items/" + r1.get_json()["id"], headers=h).status_code == 200
    row3 = next(c for c in client.get("/api/clients", headers=h).get_json() if c["id"] == cid)
    assert row3["negotiation_value"] == 3000.0


def test_item_cliente_inexistente_404(client):
    h = _login(client)
    r = client.post("/api/clients/id-x/items", headers=h, json={"name": "X", "quantity": 1, "unit_price": 1})
    assert r.status_code == 404


def test_item_validacoes(client):
    h = _login(client)
    cid = client.post("/api/clients", headers=h, json={"name": "Cliente Val", "cpf_cnpj": "3112"}).get_json()["id"]
    assert client.post("/api/clients/" + cid + "/items", headers=h, json={"name": " ", "unit_price": 1}).status_code == 400
    assert client.post("/api/clients/" + cid + "/items", headers=h, json={"name": "X", "unit_price": -5}).status_code == 400
    assert client.post("/api/clients/" + cid + "/items", headers=h, json={"name": "X", "product_id": "nao-existe"}).status_code == 404
    assert client.post("/api/clients/" + cid + "/items", headers=h, json={"name": "Y", "quantity": "abc"}).status_code == 400


def test_item_nao_finito_400(client):
    h = _login(client)
    cid = client.post("/api/clients", headers=h, json={"name": "Cliente NaN", "cpf_cnpj": "3113"}).get_json()["id"]
    r1 = client.post("/api/clients/" + cid + "/items", headers=h, json={"name": "X", "unit_price": float("nan")})
    assert r1.status_code == 400
    r2 = client.post("/api/clients/" + cid + "/items", headers=h, json={"name": "Y", "quantity": float("inf")})
    assert r2.status_code == 400


def test_lead_sources_report(client):
    h = _login(client)
    client.post("/api/clients", headers=h, json={"name": "Cliente F1A", "cpf_cnpj": "7101", "lead_source": "Fonte X", "funnel_status": "FECHAMENTO", "estimated_value": 5000})
    client.post("/api/clients", headers=h, json={"name": "Cliente F1B", "cpf_cnpj": "7102", "lead_source": "Fonte X"})
    client.post("/api/clients", headers=h, json={"name": "Cliente F2", "cpf_cnpj": "7103", "lead_source": "Fonte Y", "campaign": "Camp Z"})
    r = client.get("/api/reports/lead-sources", headers=h)
    assert r.status_code == 200, r.get_data(as_text=True)
    body = r.get_json()
    assert body["title"] == "Relatório de Origem dos Leads"
    assert body["summary"][0]["value"] == "3"
    rx = next(row for row in body["rows"] if row["group"] == "Fonte X")
    assert rx["leads"] == "2" and rx["fechados"] == "1"
    assert rx["taxa"] == "50,0%"
    ry = next(row for row in body["rows"] if row["group"] == "Fonte Y")
    assert ry["leads"] == "1" and ry["perdidos"] == "0" and ry["taxa"] == "0,0%"
    assert "R$" in rx["valor_estimado"]
    r2 = client.get("/api/reports/lead-sources", headers=h, query_string={"group_by": "campaign"})
    rows2 = r2.get_json()["rows"]
    assert any(row["group"] == "Camp Z" for row in rows2)
    assert any(row["group"] == "Sem campanha" for row in rows2)


def test_changelog_crud(client):
    h = _login(client)
    base = client.get("/api/changelog", headers=h).get_json()
    assert len(base) >= 10  # seed de novidades vem populado com o changelog das entregas
    assert any("Novidades" in e["title"] for e in base)
    r1 = client.post("/api/changelog", headers=h, json={"title": "Novo: Fonte do Lead", "content": "Select de fonte agora é personalizável", "category": "MELHORIA", "entry_date": "2026-09-15"})
    assert r1.status_code == 201, r1.get_data(as_text=True)
    eid = r1.get_json()["id"]
    client.post("/api/changelog", headers=h, json={"title": "Correção de anexos", "content": "Filename truncado", "category": "CORRECAO", "entry_date": "2026-09-14"})
    lst = client.get("/api/changelog", headers=h).get_json()
    assert len(lst) == len(base) + 2
    # ordena por entry_date desc; seed pode conter datas futuras, então verifica ordem relativa dos novos
    idx_fonte = next((i for i, e in enumerate(lst) if e["title"] == "Novo: Fonte do Lead"), None)
    idx_anexos = next((i for i, e in enumerate(lst) if e["title"] == "Correção de anexos"), None)
    assert idx_fonte is not None and idx_anexos is not None
    assert idx_fonte < idx_anexos  # 2026-09-15 vem antes de 2026-09-14
    # verifica que lista está ordenada por entry_date desc (não crescente)
    from datetime import date as _date
    dates = [e["entry_date"] for e in lst]
    assert dates == sorted(dates, reverse=True)
    r2 = client.put("/api/changelog/" + eid, headers=h, json={"title": "Novo: Fonte + Campanha"})
    assert r2.status_code == 200 and r2.get_json()["title"] == "Novo: Fonte + Campanha"
    assert client.delete("/api/changelog/" + eid, headers=h).status_code == 200
    assert client.delete("/api/changelog/" + eid, headers=h).status_code == 404
    assert client.post("/api/changelog", headers=h, json={"title": "   "}).status_code == 400
    assert client.post("/api/changelog", json={"title": "sem token"}).status_code == 401


def test_budget_goals_crud(client):
    h = _login(client)
    r = client.post("/api/budget/goals", headers=h, json={"year": 2026, "month": 9, "category": "VENDAS", "target_value": 50000})
    assert r.status_code == 201, r.get_data(as_text=True)
    gid = r.get_json()["id"]
    r2 = client.post("/api/budget/goals", headers=h, json={"year": 2026, "category": "MATERIAL", "target_value": 12000})
    assert r2.status_code == 201
    lst = client.get("/api/budget/goals", headers=h, query_string={"year": 2026}).get_json()
    assert len(lst) == 2
    lst9 = client.get("/api/budget/goals", headers=h, query_string={"year": 2026, "month": 9}).get_json()
    assert len(lst9) == 1 and lst9[0]["category"] == "VENDAS"
    r3 = client.put("/api/budget/goals/" + gid, headers=h, json={"target_value": 60000})
    assert r3.status_code == 200 and r3.get_json()["target_value"] == 60000
    assert client.delete("/api/budget/goals/" + gid, headers=h).status_code == 200
    assert client.delete("/api/budget/goals/" + gid, headers=h).status_code == 404
    assert client.post("/api/budget/goals", headers=h, json={"year": "abc", "category": "X", "target_value": 1}).status_code == 400
    assert client.post("/api/budget/goals", headers=h, json={"year": 2026, "month": 13, "category": "X", "target_value": 1}).status_code == 400
    assert client.post("/api/budget/goals", headers=h, json={"year": 2026, "category": "  ", "target_value": 1}).status_code == 400


def test_budget_analysis(client):
    h = _login(client)
    client.post("/api/budget/goals", headers=h, json={"year": 2026, "category": "VENDAS", "target_value": 10000})
    client.post("/api/budget/goals", headers=h, json={"year": 2026, "category": "MATERIAL", "target_value": 4000})
    for p in [
        {"description": "Venda 1", "type": "ENTRADA", "category": "VENDAS", "amount": 3000, "date": "2026-03-10", "status": "PAGO"},
        {"description": "Venda 2", "type": "ENTRADA", "category": "VENDAS", "amount": 2000, "date": "2026-04-10", "status": "PAGO"},
        {"description": "Venda pendente", "type": "ENTRADA", "category": "VENDAS", "amount": 5000, "date": "2026-05-10", "status": "PENDENTE"},
        {"description": "MDF", "type": "SAIDA", "category": "MATERIAL", "amount": 1000, "date": "2026-03-15", "status": "PAGO"},
    ]:
        assert client.post("/api/financial", headers=h, json=p).status_code == 201
    r = client.get("/api/budget/analysis", headers=h, query_string={"year": 2026})
    assert r.status_code == 200, r.get_data(as_text=True)
    body = r.get_json()
    assert len(body["rows"]) == 2
    v = next(row for row in body["rows"] if row["category"] == "VENDAS")
    m = next(row for row in body["rows"] if row["category"] == "MATERIAL")
    assert v["budget"] == "R$ 10.000,00" and v["actual"] == "R$ 5.000,00"
    assert v["difference"] == "R$ 5.000,00" and v["percentage"] == "50,0%"
    assert m["budget"] == "R$ 4.000,00" and m["actual"] == "R$ 1.000,00" and m["percentage"] == "25,0%"
    assert body["summary"][0]["label"] == "Orçado Total" and body["summary"][0]["value"] == "R$ 14.000,00"
    r2 = client.get("/api/budget/analysis", headers=h, query_string={"year": 2026, "month": 3})
    rows2 = r2.get_json()["rows"]
    v2 = next(row for row in rows2 if row["category"] == "VENDAS")
    assert v2["actual"] == "R$ 3.000,00" and v2["percentage"] == "30,0%"


def test_financial_new_fields(client):
    h = _login(client)
    payload = {"description": "NF-e 123", "type": "SAIDA", "category": "MATERIAL", "amount": 1500, "date": "2026-09-01", "status": "PENDENTE", "doc_number": "NF 456", "issue_date": "2026-08-30", "doc_type": "BOLETO", "bank": "Banco X", "account_plan": "3.1.01", "item_description": "MDF 15mm", "installments": 3, "is_recurring": True}
    r = client.post("/api/financial", headers=h, json=payload)
    assert r.status_code == 201, r.get_data(as_text=True)
    row = r.get_json()
    assert row["doc_number"] == "NF 456" and row["doc_type"] == "BOLETO" and row["bank"] == "Banco X"
    assert row["account_plan"] == "3.1.01" and row["installments"] == 3 and row["is_recurring"] is True
    assert row["issue_date"] == "2026-08-30"


def test_financial_new_fields_validation(client):
    h = _login(client)
    base = {"description": "Inválido", "type": "SAIDA", "amount": 100, "date": "2026-09-01"}
    r1 = client.post("/api/financial", headers=h, json=dict(base, doc_type="CARTAO"))
    assert r1.status_code == 400, r1.get_data(as_text=True)
    r2 = client.post("/api/financial", headers=h, json=dict(base, installments=0))
    assert r2.status_code == 400, r2.get_data(as_text=True)
    r3 = client.post("/api/financial", headers=h, json=dict(base, installments="abc"))
    assert r3.status_code == 400, r3.get_data(as_text=True)


def test_suppliers_crud(client):
    h = _login(client)
    r = client.post("/api/suppliers", headers=h, json={"name": "Madeireira Sul", "cnpj": "11.222.333/0001-44", "contact": "João", "phone": "(55) 99999-0000", "email": "vendas@madeireirasul.com.br"})
    assert r.status_code == 201, r.get_data(as_text=True)
    sid = r.get_json()["id"]
    lst = client.get("/api/suppliers", headers=h).get_json()
    assert any(s["id"] == sid for s in lst)
    r2 = client.put("/api/suppliers/" + sid, headers=h, json={"phone": "(55) 98888-0000"})
    assert r2.status_code == 200 and r2.get_json()["phone"] == "(55) 98888-0000"
    assert client.delete("/api/suppliers/" + sid, headers=h).status_code == 200
    assert client.delete("/api/suppliers/" + sid, headers=h).status_code == 404
    assert client.post("/api/suppliers", headers=h, json={"name": "  "}).status_code == 400


def test_financial_with_supplier(client):
    h = _login(client)
    s = client.post("/api/suppliers", headers=h, json={"name": "Fornecedor F1"})
    assert s.status_code == 201, s.get_data(as_text=True)
    sid = s.get_json()["id"]
    r = client.post("/api/financial", headers=h, json={"description": "Compra MDF", "type": "SAIDA", "amount": 800, "date": "2026-09-01", "supplier_id": sid})
    assert r.status_code == 201, r.get_data(as_text=True)
    row = r.get_json()
    assert row["supplier_id"] == sid
    assert row["supplier_name"] == "Fornecedor F1"


def test_cash_flow_report(client):
    h = _login(client)
    base = [
        {"description": "Venda A", "type": "ENTRADA", "amount": 1000, "date": "2026-01-15", "status": "PAGO"},
        {"description": "Venda B", "type": "ENTRADA", "amount": 2500, "date": "2026-01-20", "status": "PENDENTE"},
        {"description": "Aluguel", "type": "SAIDA", "amount": 300, "date": "2026-01-05", "status": "PAGO"},
        {"description": "Material", "type": "SAIDA", "amount": 200, "date": "2026-02-10", "status": "PAGO"},
        {"description": "Fora do ano", "type": "ENTRADA", "amount": 999, "date": "2025-12-31", "status": "PAGO"},
    ]
    for p in base:
        assert client.post("/api/financial", headers=h, json=p).status_code == 201
    r = client.get("/api/reports/cash-flow", headers=h, query_string={"year": 2026})
    assert r.status_code == 200, r.get_data(as_text=True)
    body = r.get_json()
    assert body["title"] in ("Fluxo de Caixa Mensal", "Fluxo de Caixa Realizado")
    jan = next(row for row in body["rows"] if row["month"] == "1 - Janeiro")
    fev = next(row for row in body["rows"] if row["month"] == "2 - Fevereiro")
    assert jan["income"] == "R$ 1.000,00" and jan["outcome"] == "R$ 300,00" and jan["balance"] == "R$ 700,00"
    assert jan["accumulated"] == "R$ 700,00"
    assert fev["income"] == "R$ 0,00" and fev["outcome"] == "R$ 200,00" and fev["accumulated"] == "R$ 500,00"
    assert sum(1 for row in body["rows"] if "R$ 0,00" in row["income"]) == 11  # 12 meses, so janeiro tem entrada PAGO


def test_cash_flow_weekly_report(client):
    """Demonstrativo semanal do mes: entradas, saidas, saldo semanal e acumulado."""
    h = _login(client)
    base = [
        # semana 1 (dias 1-7)
        {"description": "Entrada S1", "type": "ENTRADA", "amount": 1000, "date": "2026-03-03", "status": "PAGO"},
        # semana 3 (dias 15-21)
        {"description": "Saida S3", "type": "SAIDA", "amount": 300, "date": "2026-03-18", "status": "PAGO"},
        # semana 4 (dias 22-28) — em aberto: so aparece no projetado
        {"description": "Entrada S4 pendente", "type": "ENTRADA", "amount": 500, "date": "2026-03-25", "status": "PENDENTE"},
        # outro mes: nao pode entrar no demonstrativo de marco
        {"description": "Fora do mes", "type": "ENTRADA", "amount": 777, "date": "2026-04-02", "status": "PAGO"},
    ]
    for p in base:
        assert client.post("/api/financial", headers=h, json=p).status_code == 201

    r = client.get("/api/reports/cash-flow-weekly", headers=h,
                   query_string={"year": 2026, "month": 3, "mode": "realizado"})
    assert r.status_code == 200, r.get_data(as_text=True)
    body = r.get_json()
    assert body["filters_applied"] == {"year": 2026, "month": 3, "mode": "realizado"}
    assert len(body["rows"]) == 5  # semanas 1..5 sempre presentes
    assert [row["week"] for row in body["rows"]] == [f"Semana {i}" for i in range(1, 6)]

    s1, s2, s3, s4 = body["rows"][0], body["rows"][1], body["rows"][2], body["rows"][3]
    assert s1["income"] == "R$ 1.000,00" and s1["balance"] == "R$ 1.000,00"
    assert s2["income"] == "R$ 0,00" and s2["balance"] == "R$ 0,00"
    assert s3["outcome"] == "R$ 300,00" and s3["balance"] == "R$ -300,00"
    # pendente NAO entra no realizado
    assert s4["income"] == "R$ 0,00"
    # saldo acumulado correto ao longo das semanas
    assert s1["accumulated"] == "R$ 1.000,00"
    assert s3["accumulated"] == "R$ 700,00"
    assert body["rows"][4]["accumulated"] == "R$ 700,00"
    # abril ficou fora — checar pela DESCRICAO, nao pelo texto do payload
    # inteiro: o payload traz `generated_at` com o horario da geracao, e um
    # milissegundo contendo "777" fazia este teste falhar por acidente
    # (nao deterministico, falhava ~1 vez a cada mil execucoes).
    assert "Fora do mes" not in r.get_data(as_text=True)

    rp = client.get("/api/reports/cash-flow-weekly", headers=h,
                    query_string={"year": 2026, "month": 3, "mode": "projetado"})
    assert rp.status_code == 200
    bp = rp.get_json()
    assert bp["title"] == "Fluxo de Caixa Semanal Projetado"
    assert bp["rows"][3]["income"] == "R$ 500,00"      # pendente entra no projetado
    assert bp["rows"][3]["accumulated"] == "R$ 1.200,00"

    # mes invalido -> 400
    bad = client.get("/api/reports/cash-flow-weekly", headers=h,
                     query_string={"year": 2026, "month": 13})
    assert bad.status_code == 400


def test_sales_goal_crud_and_summary(client):
    """Meta comercial: CRUD, validacoes e meta x realizado com filtro de periodo."""
    h = _login(client)
    cur_year = date.today().year

    # ── CRUD
    r = client.post("/api/goals", headers=h, json={
        "year": cur_year, "month": 3, "scope": "GERAL", "target_value": 10000})
    assert r.status_code == 201, r.get_data(as_text=True)
    gid = r.get_json()["id"]
    assert float(r.get_json()["target_value"]) == 10000.0
    assert r.get_json()["month"] == 3 and r.get_json()["scope"] == "GERAL"

    # ── validacoes
    assert client.post("/api/goals", headers=h,
                       json={"year": cur_year, "target_value": -1}).status_code == 400
    assert client.post("/api/goals", headers=h,
                       json={"year": cur_year, "scope": "VENDEDOR"}).status_code == 400
    assert client.post("/api/goals", headers=h,
                       json={"year": cur_year, "scope": "INVALIDO", "target_value": 1}).status_code == 400
    assert client.post("/api/goals", headers=h,
                       json={"year": 1990, "target_value": 1}).status_code == 400
    assert client.post("/api/goals", headers=h,
                       json={"year": cur_year, "month": 13, "target_value": 1}).status_code == 400

    r = client.put(f"/api/goals/{gid}", headers=h, json={"target_value": 12000})
    assert r.status_code == 200 and float(r.get_json()["target_value"]) == 12000.0
    lst = client.get("/api/goals", headers=h, query_string={"year": cur_year})
    assert lst.status_code == 200 and len(lst.get_json()) == 1

    # ── sem venda fechada: realizado zero
    body = client.get("/api/goals/summary", headers=h,
                      query_string={"year": cur_year, "month": 3}).get_json()
    assert body["target"] == "R$ 12.000,00" and body["target_basis"] == "mes"
    assert body["achieved"] == "R$ 0,00" and body["percent"] == "0,0%"
    assert body["deals_closed"] == 0 and body["undated"] == 0

    # ── fecha uma venda: via POST /api/sales (tela Gerar venda). Arrastar o
    # card para a etapa de ganho NAO atualiza mais meta/comissao/CRM.
    cr = client.post("/api/clients", headers=h,
                     json={"name": "Cliente Fechado", "estimated_value": 4000})
    assert cr.status_code == 201, cr.get_data(as_text=True)
    cid = cr.get_json()["id"]
    assert cr.get_json()["closed_at"] is None  # ainda nao fechado

    up = client.put(f"/api/clients/{cid}", headers=h, json={"funnel_status": "FECHAMENTO"})
    assert up.status_code == 200 and up.get_json()["closed_at"] is None
    sale = client.post("/api/sales", headers=h, json={
        "client_id": cid, "total_value": 4000, "down_payment": 4000,
        "installments": 0, "installment_value": 0, "installments_due": [],
        "sale_date": date.today().isoformat(), "environments": [],
    })
    assert sale.status_code == 201, sale.get_data(as_text=True)
    assert client.get(f"/api/clients/{cid}", headers=h).get_json()["closed_at"]

    # marco continua zerado: a venda fechou AGORA, nao em marco -> prova o filtro de periodo
    s2 = client.get("/api/goals/summary", headers=h, query_string={"year": cur_year, "month": 3})
    assert s2.get_json()["achieved"] == "R$ 0,00"

    # meta do ANO (month null) enxerga a venda do periodo corrente
    ga = client.post("/api/goals", headers=h, json={
        "year": cur_year, "scope": "GERAL", "target_value": 10000})
    assert ga.status_code == 201, ga.get_data(as_text=True)
    b3 = client.get("/api/goals/summary", headers=h,
                    query_string={"year": cur_year}).get_json()
    assert b3["target_basis"] == "ano" and b3["target"] == "R$ 10.000,00"
    assert b3["achieved"] == "R$ 4.000,00"
    assert b3["percent"] == "40,0%" and b3["remaining"] == "R$ 6.000,00"
    assert b3["deals_closed"] == 1 and b3["undated"] == 0

    # ── delete
    assert client.delete(f"/api/goals/{gid}", headers=h).status_code == 200
    assert client.delete(f"/api/goals/{gid}", headers=h).status_code == 404


def test_is_won_status():
    """Ultima coluna por posicao NAO basta: perdido nunca e venda."""
    from app.models.models import is_lost_status, is_won_status

    assert is_won_status("FECHAMENTO", "PERDIDO") is True
    assert is_won_status("PERDIDO", "PERDIDO") is False
    assert is_won_status("CANCELADO", "CANCELADO") is False
    # funil com nome proprio: ultima coluna continua valendo (comportamento antigo)
    assert is_won_status("ENTREGUE", "ENTREGUE") is True
    assert is_won_status("ORCAMENTO", "FECHAMENTO") is False
    assert is_won_status(None) is False
    assert is_lost_status("PERDIDO") is True and is_lost_status("FECHAMENTO") is False


def test_perdido_nao_conta_como_venda(client):
    """Negocio perdido nao e venda: nao grava closed_at, nao cria projeto e nao
    entra na meta comercial.

    O funil CRM padrao termina em PERDIDO, entao tratar a ultima coluna por
    posicao como "venda fechada" contava negocio perdido como venda realizada
    e criava projeto para cliente perdido.
    """
    h = _login(client)
    cur_year = date.today().year
    funnels = client.get("/api/funnels", headers=h, query_string={"kind": "CRM"}).get_json()
    fid = funnels[0]["id"]
    keys = [c["column_key"] for c in funnels[0]["columns"]]
    assert "PERDIDO" in keys and "FECHAMENTO" in keys
    # premissa do teste: a ultima coluna por posicao e a de perda
    last_key = max(funnels[0]["columns"], key=lambda c: c["position"])["column_key"]
    assert last_key == "PERDIDO", f"premissa: ultima coluna e PERDIDO, veio {last_key}"

    def novo(nome, valor):
        r = client.post("/api/clients", headers=h,
                        json={"name": nome, "funnel_id": fid, "estimated_value": valor})
        assert r.status_code == 201, r.get_data(as_text=True)
        return r.get_json()["id"]

    perdido = novo("Cliente Perdido", 5000)
    ganho = novo("Cliente Ganho", 2000)

    up = client.put(f"/api/clients/{perdido}", headers=h, json={"funnel_status": "PERDIDO"})
    assert up.status_code == 200, up.get_data(as_text=True)
    assert up.get_json()["closed_at"] is None, "perdido nao pode ter data de fechamento"

    up = client.put(f"/api/clients/{ganho}", headers=h, json={"funnel_status": "FECHAMENTO"})
    assert up.status_code == 200, up.get_data(as_text=True)
    # arrastar para a etapa de ganho nao atualiza mais nada (so a tela Gerar venda)
    assert up.get_json()["closed_at"] is None

    # fecha a venda de verdade pela tela Gerar venda
    sale = client.post("/api/sales", headers=h, json={
        "client_id": ganho, "total_value": 2000, "down_payment": 2000,
        "installments": 0, "installment_value": 0, "installments_due": [],
        "sale_date": date.today().isoformat(), "environments": [],
    })
    assert sale.status_code == 201, sale.get_data(as_text=True)

    # a meta enxerga o ganho (2000), nunca o perdido (5000)
    client.post("/api/goals", headers=h,
                json={"year": cur_year, "scope": "GERAL", "target_value": 10000})
    b = client.get("/api/goals/summary", headers=h, query_string={"year": cur_year}).get_json()
    assert b["achieved"] == "R$ 2.000,00", b["achieved"]
    assert b["deals_closed"] == 1, b["deals_closed"]
    assert b["percent"] == "20,0%", b["percent"]

    # e nao criou projeto para o cliente perdido
    titulos = [p["title"] for p in client.get("/api/projects", headers=h).get_json()]
    assert any("Cliente Ganho" in t for t in titulos), "venda ganha deveria criar projeto"
    assert not any("Cliente Perdido" in t for t in titulos), "cliente perdido nao pode criar projeto"


def test_assembly_event_fields(client):
    """Montagem e um CalendarEvent com equipe e local — nao tabela nova."""
    h = _login(client)
    r = client.post("/api/calendar", headers=h, json={
        "title": "Montagem QA", "type": "MONTAGEM",
        "start_date": date.today().isoformat(),
        "team": "Equipe A", "location": "Rua das Flores, 100",
    })
    assert r.status_code == 201, r.get_data(as_text=True)
    ev = r.get_json()
    assert ev["type"] == "MONTAGEM"
    assert ev["team"] == "Equipe A" and ev["location"] == "Rua das Flores, 100", ev

    # editar so a equipe nao pode apagar o local
    r = client.put(f"/api/calendar/{ev['id']}", headers=h, json={"team": "Equipe B"})
    assert r.status_code == 200, r.get_data(as_text=True)
    ev2 = r.get_json()
    assert ev2["team"] == "Equipe B", ev2
    assert ev2["location"] == "Rua das Flores, 100", f"local foi perdido: {ev2}"

    # evento comum continua sem equipe
    r = client.post("/api/calendar", headers=h, json={
        "title": "Reuniao QA", "type": "REUNIAO",
        "start_date": date.today().isoformat(),
    })
    assert r.status_code == 201
    assert r.get_json()["team"] is None


def test_production_pending_overview(client):
    """Pendencias de producao: ocorrencias (com custo) + checklist aberto."""
    h = _login(client)
    cid = client.post("/api/clients", headers=h,
                      json={"name": "Cliente QA Pend"}).get_json()["id"]
    pid = client.post("/api/projects", headers=h, json={
        "title": "Projeto QA Pend", "client_id": cid,
        "steps": [{"id": "1", "label": "Medição", "completed": False}]}).get_json()["id"]

    for kind, custo in (("RETRABALHO", 150.5), ("PERDA", 49.5)):
        r = client.post(f"/api/projects/{pid}/issues", headers=h, json={
            "kind": kind, "cost": custo, "issue_date": date.today().isoformat(),
            "reason": f"{kind} QA"})
        assert r.status_code == 201, r.get_data(as_text=True)

    # ocorrencia SEM custo: nao pode virar zero silencioso nem quebrar a soma
    r = client.post(f"/api/projects/{pid}/issues", headers=h, json={
        "kind": "DESPERDICIO", "issue_date": date.today().isoformat(),
        "reason": "sem custo"})
    assert r.status_code == 201, r.get_data(as_text=True)

    proj = client.get(f"/api/projects/{pid}", headers=h).get_json()
    steps = proj.get("steps") or []
    assert steps, "projeto criado com etapas deveria devolve-las"
    r = client.post(f"/api/projects/{pid}/checklists", headers=h, json={
        "step_id": str(steps[0]["id"]), "label": "Conferir puxador QA"})
    assert r.status_code == 201, r.get_data(as_text=True)

    body = client.get("/api/production/pending", headers=h).get_json()
    assert body["issues_count"] == 3, body["issues_count"]
    assert body["issues_total_cost"] == 200.0, body["issues_total_cost"]
    assert body["issues_without_cost"] == 1, "ocorrencia sem custo deve ser contada a parte"
    assert body["issues_by_kind"]["RETRABALHO"] == {"count": 1, "cost": 150.5}
    assert body["issues_by_kind"]["PERDA"] == {"count": 1, "cost": 49.5}
    assert body["issues_by_kind"]["DESPERDICIO"] == {"count": 1, "cost": 0.0}
    assert body["checklist_count"] >= 1
    assert any(c["label"] == "Conferir puxador QA" for c in body["checklist"])

    # periodo fora da janela nao traz ocorrencia
    body2 = client.get("/api/production/pending", headers=h, query_string={
        "from": "2000-01-01", "to": "2000-01-31"}).get_json()
    assert body2["issues_count"] == 0, "periodo antigo nao pode trazer ocorrencia"

    # data invalida -> 400, nao 500
    assert client.get("/api/production/pending", headers=h,
                      query_string={"from": "ontem"}).status_code == 400


def test_purchase_quotations_comparison_and_savings(client):
    """Cotacoes por compra: comparativo, vencedora unica e economia MEDIDA."""
    h = _login(client)
    hoje = date.today().isoformat()

    def fornecedor(nome):
        r = client.post("/api/suppliers", headers=h, json={"name": nome})
        assert r.status_code == 201, r.get_data(as_text=True)
        return r.get_json()["id"]

    f1 = fornecedor("Madeireira QA 1")
    f2 = fornecedor("Madeireira QA 2")
    f3 = fornecedor("Madeireira QA 3")

    r = client.post("/api/purchases", headers=h, json={
        "request_date": hoje, "carrier": "Transportes QA", "tracking": "BR123456789",
        "items": [
            {"material_name": "MDF QA A", "quantity": 10, "unit_price": 0},
            {"material_name": "MDF QA B", "quantity": 5, "unit_price": 0},
        ],
    })
    assert r.status_code == 201, r.get_data(as_text=True)
    order = r.get_json()
    oid = order["id"]
    ia, ib = order["items"][0]["id"], order["items"][1]["id"]

    assert order["carrier"] == "Transportes QA", order["carrier"]
    assert order["tracking"] == "BR123456789", order["tracking"]
    # pedido sem cotacao nao pode inventar economia
    assert order["saving_real"] == 0 and order["saving_real_items"] == 0, order["saving_real"]

    # tres cotacoes: A em 100/90/110 e B em 50/45/55
    precos = [
        (f1, [(ia, 100), (ib, 50)], 10),
        (f2, [(ia, 90), (ib, 45)], 5),
        (f3, [(ia, 110), (ib, 55)], 20),
    ]
    qids = []
    for fid, itens, dias in precos:
        r = client.post(f"/api/purchases/{oid}/quotations", headers=h, json={
            "supplier_id": fid, "delivery_days": dias, "payment_terms": "30 dias",
            "items": [{"purchase_item_id": p, "unit_price": v} for p, v in itens],
        })
        assert r.status_code == 201, r.get_data(as_text=True)
        qids.append(r.get_json()["id"])

    lst = client.get(f"/api/purchases/{oid}/quotations", headers=h).get_json()
    assert len(lst) == 3, f"esperava 3 cotacoes, veio {len(lst)}"
    # total = preco unitario x quantidade do item do pedido
    totais = sorted(round(q["total"], 2) for q in lst)
    # q1: 100*10 + 50*5 = 1250 | q2: 90*10 + 45*5 = 1125 | q3: 110*10 + 55*5 = 1375
    assert totais == [1125.0, 1250.0, 1375.0], f"totais: {totais}"
    assert not any(q["is_winner"] for q in lst), "nenhuma cotacao pode nascer vencedora"

    # aprovar a MAIS BARATA (f2: A=90, B=45)
    r = client.post(f"/api/purchases/{oid}/quotations/{qids[1]}/approve", headers=h)
    assert r.status_code == 200, r.get_data(as_text=True)
    aprovado = r.get_json()
    assert aprovado["quotations_count"] == 3, aprovado["quotations_count"]

    lst2 = client.get(f"/api/purchases/{oid}/quotations", headers=h).get_json()
    vencedoras = [q for q in lst2 if q["is_winner"]]
    assert len(vencedoras) == 1, f"{len(vencedoras)} vencedora(s) — a vencedora tem que ser unica"
    assert vencedoras[0]["id"] == qids[1], "a vencedora nao e a aprovada"

    precos_pedido = {i["id"]: i["unit_price"] for i in aprovado["items"]}
    assert precos_pedido[ia] == 90 and precos_pedido[ib] == 45, precos_pedido
    assert aprovado["status"] == "APROVADA", aprovado["status"]
    assert aprovado["supplier_id"] == f2, aprovado["supplier_name"]

    # economia MEDIDA = (maior cotado - escolhido) x quantidade
    # A: (110-90)*10 = 200 | B: (55-45)*5 = 50  => 250
    assert aprovado["saving_real"] == 250.0, aprovado["saving_real"]
    assert aprovado["saving_real_items"] == 2, aprovado["saving_real_items"]

    # cotacao com item de outro pedido nao entra
    r = client.post(f"/api/purchases/{oid}/quotations", headers=h, json={
        "supplier_id": f1, "items": [{"purchase_item_id": "id-inexistente", "unit_price": 1}]})
    assert r.status_code == 201, r.get_data(as_text=True)
    assert r.get_json()["items"] == [], "item de outro pedido nao pode entrar"

    # validacoes
    assert client.post(f"/api/purchases/{oid}/quotations", headers=h,
                       json={"delivery_days": -3}).status_code == 400
    assert client.post(f"/api/purchases/{oid}/quotations", headers=h,
                       json={"delivery_days": "muitos"}).status_code == 400
    assert client.post(f"/api/purchases/{oid}/quotations", headers=h,
                       json={"supplier_id": "nao-existe"}).status_code == 400
    assert client.get("/api/purchases/id-inexistente/quotations", headers=h).status_code == 404
    assert client.post("/api/purchases/id-inexistente/quotations/id-x/approve",
                       headers=h).status_code == 404

    # editar e excluir cotacao
    r = client.put(f"/api/quotations/{qids[0]}", headers=h,
                   json={"payment_terms": "45 dias", "delivery_days": 15})
    assert r.status_code == 200, r.get_data(as_text=True)
    assert r.get_json()["payment_terms"] == "45 dias", r.get_json()["payment_terms"]
    assert client.delete(f"/api/quotations/{qids[0]}", headers=h).status_code == 200
    # sobraram a vencedora, a terceira e a vazia criada acima
    assert len(client.get(f"/api/purchases/{oid}/quotations", headers=h).get_json()) == 3


def test_purchases_logistics_calendar(client):
    """Calendario logistico: pedidos por data esperada, com atrasados."""
    h = _login(client)
    hoje = date.today()
    atrasado = (hoje - timedelta(days=4)).isoformat()
    futuro = (hoje + timedelta(days=9)).isoformat()

    r = client.post("/api/purchases", headers=h, json={
        "request_date": hoje.isoformat(), "expected_date": atrasado,
        "carrier": "Transportadora Atrasada", "tracking": "ATR-1",
        "items": [{"material_name": "Item atrasado", "quantity": 1, "unit_price": 10}],
    })
    assert r.status_code == 201, r.get_data(as_text=True)
    ped_atrasado = r.get_json()["id"]

    r = client.post("/api/purchases", headers=h, json={
        "request_date": hoje.isoformat(), "expected_date": futuro,
        "carrier": "Transportadora Futura", "tracking": "FUT-1",
        "items": [{"material_name": "Item futuro", "quantity": 1, "unit_price": 10}],
    })
    assert r.status_code == 201, r.get_data(as_text=True)

    por_id = {p["id"]: p for p in client.get("/api/purchases", headers=h).get_json()}
    assert por_id[ped_atrasado]["expected_date"] < hoje.isoformat(), \
        por_id[ped_atrasado]["expected_date"]
    assert por_id[ped_atrasado]["carrier"] == "Transportadora Atrasada", \
        por_id[ped_atrasado]["carrier"]
    assert por_id[ped_atrasado]["tracking"] == "ATR-1", por_id[ped_atrasado]["tracking"]

    # editar so o rastreio nao pode apagar a transportadora
    r = client.put(f"/api/purchases/{ped_atrasado}", headers=h, json={"tracking": "ATR-2"})
    assert r.status_code == 200, r.get_data(as_text=True)
    atualizado = r.get_json()
    assert atualizado["tracking"] == "ATR-2", atualizado["tracking"]
    assert atualizado["carrier"] == "Transportadora Atrasada", \
        f"transportadora foi perdida: {atualizado['carrier']}"


def test_financial_filters_and_aging(client):
    """Filtros server-side de /api/financial e o aging das contas em aberto."""
    h = _login(client)
    hoje = date.today()

    def lanc(desc, tipo, valor, dias_venc, status="PENDENTE"):
        venc = hoje + timedelta(days=dias_venc)
        r = client.post("/api/financial", headers=h, json={
            "description": desc, "type": tipo, "amount": valor,
            "date": venc.isoformat(), "due_date": venc.isoformat(), "status": status,
        })
        assert r.status_code == 201, r.get_data(as_text=True)
        return r.get_json()["id"]

    lanc("Pagar vencida", "SAIDA", 300, -5)
    lanc("Pagar 0-7", "SAIDA", 200, 3)
    lanc("Pagar 8-30", "SAIDA", 100, 20)
    lanc("Pagar +30", "SAIDA", 50, 60)
    lanc("Pagar JA PAGA", "SAIDA", 999, -5, status="PAGO")
    lanc("Receber vencida", "ENTRADA", 700, -2)

    # ── filtros ──────────────────────────────────────────────────────
    r = client.get("/api/financial", headers=h,
                   query_string={"type": "SAIDA", "status": "PENDENTE"})
    assert r.status_code == 200, r.get_data(as_text=True)
    pend = r.get_json()
    assert len(pend) == 4, f"esperava 4 SAIDA pendentes, veio {len(pend)}"
    assert all(x["type"] == "SAIDA" and x["status"] == "PENDENTE" for x in pend)
    assert 999 not in [x["amount"] for x in pend], "lancamento PAGO nao pode aparecer"

    r = client.get("/api/financial", headers=h, query_string={"type": "ENTRADA"})
    assert len(r.get_json()) == 1, "so o lancamento de entrada"

    # vencidas em aberto: as duas com vencimento no passado e status PENDENTE
    r = client.get("/api/financial", headers=h, query_string={"overdue": "1"})
    assert r.status_code == 200
    venc = r.get_json()
    assert len(venc) == 2, f"esperava 2 vencidas em aberto, veio {len(venc)}"
    assert sum(x["amount"] for x in venc) == 1000

    # janela de vencimento
    r = client.get("/api/financial", headers=h, query_string={
        "due_from": hoje.isoformat(), "due_to": (hoje + timedelta(days=30)).isoformat()})
    assert len(r.get_json()) == 2, "dentro da janela: 0-7 e 8-30"

    # parametro invalido -> 400 (nao 500: parse_date levanta ValueError)
    for qs in ({"type": "BANANA"}, {"status": "TALVEZ"}, {"due_from": "ontem"}):
        r = client.get("/api/financial", headers=h, query_string=qs)
        assert r.status_code == 400, f"{qs} deveria dar 400, deu {r.status_code}"

    # ── aging ────────────────────────────────────────────────────────
    r = client.get("/api/financial/aging", headers=h, query_string={"type": "SAIDA"})
    assert r.status_code == 200, r.get_data(as_text=True)
    a = r.get_json()
    assert a["open_count"] == 4 and a["open_total"] == 650, a
    assert a["buckets"]["vencidas"] == {"count": 1, "total": 300}, a["buckets"]["vencidas"]
    assert a["buckets"]["0_7"] == {"count": 1, "total": 200}, a["buckets"]["0_7"]
    assert a["buckets"]["8_30"] == {"count": 1, "total": 100}, a["buckets"]["8_30"]
    assert a["buckets"]["acima_30"] == {"count": 1, "total": 50}, a["buckets"]["acima_30"]
    # a conta PAGA nao entra no aging
    assert a["open_total"] == 650, "lancamento PAGO entrou no aging"

    r = client.get("/api/financial/aging", headers=h, query_string={"type": "ENTRADA"})
    ae = r.get_json()
    assert ae["open_total"] == 700 and ae["buckets"]["vencidas"]["count"] == 1, ae

    r = client.get("/api/financial/aging", headers=h, query_string={"type": "NOPE"})
    assert r.status_code == 400


def test_financial_aging_sem_vencimento(client):
    """Lancamento sem vencimento nao pode entrar em bucket nenhum."""
    h = _login(client)
    r = client.post("/api/financial", headers=h, json={
        "description": "Sem vencimento", "type": "SAIDA", "amount": 123,
        "date": date.today().isoformat(), "status": "PENDENTE",
    })
    assert r.status_code == 201, r.get_data(as_text=True)
    # o POST preenche due_date = date quando ausente; zera direto no banco
    from app.extensions import db
    from app.models.models import FinancialRecord
    with client.application.app_context():
        rec = db.session.query(FinancialRecord).filter_by(description="Sem vencimento").one()
        rec.due_date = None
        db.session.commit()

    a = client.get("/api/financial/aging", headers=h, query_string={"type": "SAIDA"}).get_json()
    assert a["no_due_date"] == {"count": 1, "total": 123}, a["no_due_date"]
    assert all(b["count"] == 0 for b in a["buckets"].values()), "foi para um bucket indevido"
    assert a["open_total"] == 123, "o total geral ainda deve contar o lancamento"


def test_dashboard_attention(client):
    """Bloco 'o que precisa da minha atencao' agrega pendencias reais."""
    h = _login(client)
    today = date.today()
    past = (today - timedelta(days=3)).isoformat()
    soon = (today + timedelta(days=2)).isoformat()

    # base limpa: nada pendente
    body = client.get("/api/dashboard/attention", headers=h).get_json()
    assert body["items"] == [] and body["total_items"] == 0
    assert body["reference_date"] == today.isoformat()

    # conta vencida + conta a vencer
    for desc, dd in (("Vencida", past), ("A vencer", soon)):
        assert client.post("/api/financial", headers=h, json={
            "description": desc, "type": "SAIDA", "amount": 100,
            "date": dd, "status": "PENDENTE", "due_date": dd}).status_code == 201

    kinds = {i["kind"]: i for i in
             client.get("/api/dashboard/attention", headers=h).get_json()["items"]}
    assert kinds["CONTA_VENCIDA"]["count"] == 1
    assert kinds["CONTA_VENCIDA"]["total"] == "R$ 100,00"
    assert kinds["CONTA_VENCIDA"]["module"] == "financial"
    assert kinds["CONTA_VENCIDA"]["tab"] == "overdue"
    assert kinds["CONTA_VENCIDA"]["tone"] == "negative"
    assert kinds["CONTA_A_VENCER"]["count"] == 1

    # uma conta PAGA nao pode contar como pendencia
    paid = client.post("/api/financial", headers=h, json={
        "description": "Paga", "type": "SAIDA", "amount": 999,
        "date": past, "status": "PAGO", "due_date": past}).get_json()["id"]
    kinds = {i["kind"]: i for i in
             client.get("/api/dashboard/attention", headers=h).get_json()["items"]}
    assert kinds["CONTA_VENCIDA"]["count"] == 1  # continua 1, nao 2
    assert "999" not in str(kinds["CONTA_VENCIDA"]["total"])
    assert paid

    cid = client.post("/api/clients", headers=h,
                      json={"name": "Cliente Atencao"}).get_json()["id"]

    # chamado de pos-venda aberto
    assert client.post("/api/tickets", headers=h, json={
        "client_id": cid, "description": "Porta desalinhou"}).status_code == 201
    # projeto com prazo vencido
    assert client.post("/api/projects", headers=h, json={
        "title": "Projeto Atrasado", "client_id": cid, "deadline": past}).status_code == 201
    # orcamento parado, sem interacao
    assert client.post("/api/clients", headers=h, json={
        "name": "Orcamento Parado", "funnel_status": "ORCAMENTO"}).status_code == 201

    body = client.get("/api/dashboard/attention", headers=h).get_json()
    kinds = {i["kind"]: i for i in body["items"]}
    assert kinds["CHAMADO_ABERTO"]["count"] == 1
    assert kinds["CHAMADO_ABERTO"]["module"] == "tickets"
    assert kinds["PROJETO_ATRASADO"]["count"] == 1
    assert kinds["PROJETO_ATRASADO"]["module"] == "production"
    assert kinds["ORCAMENTO_SEM_RETORNO"]["count"] == 1
    assert kinds["ORCAMENTO_SEM_RETORNO"]["module"] == "commercial"
    assert body["total_items"] == 5


def test_dre_table_report(client):
    h = _login(client)
    items = [
        {"description": "Venda C", "type": "ENTRADA", "amount": 6000, "date": "2026-03-10", "status": "PAGO"},
        {"description": "Venda D", "type": "ENTRADA", "amount": 4000, "date": "2026-07-10", "status": "PAGO"},
        {"description": "Pendente X", "type": "ENTRADA", "amount": 5000, "date": "2026-05-10", "status": "PENDENTE"},
        {"description": "Custo", "type": "SAIDA", "amount": 3000, "date": "2026-03-20", "status": "PAGO"},
        {"description": "Custo 2", "type": "SAIDA", "amount": 1000, "date": "2026-07-20", "status": "PAGO"},
    ]
    for p in items:
        assert client.post("/api/financial", headers=h, json=p).status_code == 201
    r = client.get("/api/reports/dre", headers=h, query_string={"year": 2026, "period": "semestral"})
    assert r.status_code == 200, r.get_data(as_text=True)
    body = r.get_json()
    assert body["title"] == "DRE - Demonstrativo do Resultado"
    s1 = next(row for row in body["rows"] if row["period"] == "1º Semestre")
    s2 = next(row for row in body["rows"] if row["period"] == "2º Semestre")
    assert s1["income"] == "R$ 6.000,00" and s1["outcome"] == "R$ 3.000,00" and s1["result"] == "R$ 3.000,00"
    assert s2["income"] == "R$ 4.000,00" and s2["outcome"] == "R$ 1.000,00" and s2["result"] == "R$ 3.000,00"
    assert s2["accumulated"] == "R$ 6.000,00"


def test_dre_detalhado_por_categoria(client):
    h = _login(client)
    items = [
        {"description": "Venda A", "type": "ENTRADA", "category": "Vendas", "amount": 8000, "date": "2026-02-10", "status": "PAGO"},
        {"description": "Venda B", "type": "ENTRADA", "category": "Serviços", "amount": 2000, "date": "2026-02-11", "status": "PAGO"},
        {"description": "Aluguel", "type": "SAIDA", "category": "Fixos", "amount": 3000, "date": "2026-02-12", "status": "PAGO"},
        {"description": "MDF", "type": "SAIDA", "category": "Insumos", "amount": 1000, "date": "2026-02-13", "status": "PAGO"},
    ]
    for p in items:
        assert client.post("/api/financial", headers=h, json=p).status_code == 201
    r = client.get("/api/reports/dre", headers=h, query_string={"year": 2026, "period": "mensal"})
    assert r.status_code == 200, r.get_data(as_text=True)
    body = r.get_json()
    fev = next(row for row in body["rows"] if "Fevereiro" in row["period"])
    assert "Vendas" in fev["income_detail"] and "Serviços" in fev["income_detail"], fev
    # Sem coluna propria: despesas por categoria vao aninhadas (lista completa)
    assert not any(c.get("key") == "outcome_detail" for c in body["columns"]), body["columns"]
    assert "outcome_detail" not in fev, fev
    breakdown = {d["categoria"]: d for d in fev["outcome_breakdown"]}
    assert breakdown["Fixos"]["participacao"] == 75.0, breakdown
    assert breakdown["Insumos"]["participacao"] == 25.0, breakdown
    assert breakdown["Fixos"]["total_fmt"] == "R$ 3.000,00", breakdown
    cats = {c["categoria"]: c for c in body["by_category"]}
    assert cats["Vendas"]["tipo"] == "receita" and cats["Vendas"]["participacao"] == 80.0, cats
    assert cats["Fixos"]["tipo"] == "despesa" and cats["Fixos"]["participacao"] == 75.0, cats
    labels = [s["label"] for s in body["summary"]]
    assert "Margem Líquida" in labels and "Principal Receita" in labels and "Principal Despesa" in labels, labels
    margem = next(s for s in body["summary"] if s["label"] == "Margem Líquida")
    assert margem["value"] == "60.0%", margem


def test_ticket_medio_usa_projetos_concluidos(client):
    h = _login(client)
    c = client.post("/api/clients", headers=h, json={"name": "Cliente Ticket", "cpf_cnpj": "ticket01"})
    assert c.status_code == 201, c.get_data(as_text=True)
    cid = c.get_json()["id"]
    p = client.post("/api/projects", headers=h, json={"title": "Proj Ticket", "client_id": cid, "value": 12000})
    assert p.status_code == 201, p.get_data(as_text=True)
    pid = p.get_json()["id"]
    # Projeto com status CONCLUIDO mas SEM conclusao pelo botao NAO entra no ticket
    assert client.put(f"/api/projects/{pid}", headers=h, json={"status": "CONCLUIDO"}).status_code == 200
    t = client.get("/api/reports/crm", headers=h).get_json()["ticket_medio"]
    assert t["media"] == 0, t
    # Conclusao pelo botao -> entra no ticket
    assert client.post(f"/api/projects/{pid}/conclude", headers=h).status_code == 200
    t = client.get("/api/reports/crm", headers=h).get_json()["ticket_medio"]
    assert t["media"] == 12000 and t["total_projetos"] == 1 and t["total_faturado"] == 12000, t


def test_ticket_medio_fallback_vendas_crm(client):
    h = _login(client)
    c = client.post("/api/clients", headers=h, json={
        "name": "Cliente Fechado", "cpf_cnpj": "ticket02",
        "funnel_status": "FECHAMENTO", "estimated_value": 5000,
    })
    assert c.status_code == 201, c.get_data(as_text=True)
    t = client.get("/api/reports/crm", headers=h).get_json()["ticket_medio"]
    assert t["media"] == 5000 and t["total_projetos"] == 1, t
    assert t["origem"] == "vendas fechadas no CRM", t


def test_funnels_crud(client):
    h = _login(client)
    r = client.get("/api/funnels", headers=h, query_string={"kind": "CRM"})
    assert r.status_code == 200
    funnels = r.get_json()
    assert len(funnels) == 1
    assert funnels[0]["name"] == "Funil de Vendas" and funnels[0]["is_default"] is True
    assert len(funnels[0]["columns"]) >= 5
    r2 = client.post("/api/funnels", headers=h, json={"name": "Funil Comercial", "kind": "CRM"})
    assert r2.status_code == 201, r2.get_data(as_text=True)
    fid = r2.get_json()["id"]
    assert len(r2.get_json()["columns"]) >= 5  # clonou etapas do padrao
    r3 = client.put("/api/funnels/" + fid, headers=h, json={"name": "Funil Comercial B2B"})
    assert r3.status_code == 200 and r3.get_json()["name"] == "Funil Comercial B2B"
    assert client.delete("/api/funnels/" + fid, headers=h).status_code == 200
    assert client.delete("/api/funnels/" + fid, headers=h).status_code == 404
    assert client.delete("/api/funnels/" + funnels[0]["id"], headers=h).status_code == 400


def test_funnels_delete_in_use(client):
    h = _login(client)
    f = client.post("/api/funnels", headers=h, json={"name": "Funil X", "kind": "CRM"}).get_json()
    c = client.post("/api/clients", headers=h, json={"name": "Cliente Funil", "cpf_cnpj": "9001", "funnel_id": f["id"]})
    assert c.status_code == 201, c.get_data(as_text=True)
    assert client.delete("/api/funnels/" + f["id"], headers=h).status_code == 400


def test_funnel_columns_dynamic(client):
    h = _login(client)
    f = client.post("/api/funnels", headers=h, json={"name": "Funil Etapas", "kind": "CRM"}).get_json()
    fid = f["id"]
    r = client.post("/api/funnels/" + fid + "/columns", headers=h, json={"label": "Pós-venda"})
    assert r.status_code == 201, r.get_data(as_text=True)
    assert r.get_json()["column_key"] == "POS_VENDA"
    r2 = client.put("/api/funnels/" + fid + "/columns/POS_VENDA", headers=h, json={"label": "Pós-Venda VIP", "position": 1})
    assert r2.status_code == 200 and r2.get_json()["label"] == "Pós-Venda VIP" and r2.get_json()["position"] == 1
    assert client.delete("/api/funnels/" + fid + "/columns/POS_VENDA", headers=h).status_code == 200
    assert client.delete("/api/funnels/" + fid + "/columns/POS_VENDA", headers=h).status_code == 404


def test_funnel_column_delete_in_use(client):
    h = _login(client)
    f = client.post("/api/funnels", headers=h, json={"name": "Funil Y", "kind": "CRM"}).get_json()
    fid = f["id"]
    client.post("/api/clients", headers=h, json={"name": "Cliente Etapa", "cpf_cnpj": "9002", "funnel_id": fid})
    assert client.delete("/api/funnels/" + fid + "/columns/PROSPECCAO", headers=h).status_code == 400


def test_client_funnel_assignment(client):
    h = _login(client)
    r = client.post("/api/clients", headers=h, json={"name": "Cliente Padrao", "cpf_cnpj": "9003"})
    assert r.status_code == 201
    default = client.get("/api/funnels", headers=h, query_string={"kind": "CRM"}).get_json()[0]
    assert r.get_json()["funnel_id"] == default["id"]
    bad = client.post("/api/clients", headers=h, json={"name": "Cliente Ruim", "cpf_cnpj": "9004", "funnel_id": "nao-existe"})
    assert bad.status_code == 400


def test_funnel_columns_legacy_compat(client):
    h = _login(client)
    r = client.get("/api/funnel-columns", headers=h, query_string={"type": "CRM"})
    assert r.status_code == 200
    cols = r.get_json()
    assert any(c["column_key"] == "PROSPECCAO" for c in cols)
    r2 = client.put("/api/funnel-columns/ORCAMENTO", headers=h, json={"label": "Orçamento 2"})
    assert r2.status_code == 200
    r3 = client.get("/api/funnel-columns", headers=h, query_string={"type": "CRM"}).get_json()
    assert next(c for c in r3 if c["column_key"] == "ORCAMENTO")["label"] == "Orçamento 2"


def test_purchase_order_model(client):
    _login(client)
    import datetime

    with client.application.app_context():
        from app.models.models import Category, PurchaseItem, PurchaseOrder, StockItem, Supplier

        cat = Category(name="Cat Compras PO", category_type="STOCK")
        db.session.add(cat)
        db.session.flush()
        stock = StockItem(
            name="MDF 18mm",
            sku="MDF-18-PO-0001",
            category_id=cat.id,
            quantity=10,
            min_quantity=2,
        )
        db.session.add(stock)
        sup = Supplier(name="Fornecedor PO Teste")
        db.session.add(sup)
        db.session.flush()

        order = PurchaseOrder(
            number="PC-TESTE-0001",
            status="SOLICITADA",
            supplier_id=sup.id,
            request_date=datetime.date.today(),
        )
        db.session.add(order)
        db.session.flush()

        item = PurchaseItem(
            order=order,
            stock_item_id=stock.id,
            material_name="MDF 18mm",
            quantity=2,
            unit_price=150,
            position=0,
        )
        db.session.add(item)
        db.session.commit()

        assert order.number == "PC-TESTE-0001"
        d = order.to_dict()
        assert d["number"] == "PC-TESTE-0001"
        assert d["status"] == "SOLICITADA"
        assert d["supplier_name"] == sup.name
        assert len(d["items"]) == 1
        assert d["total"] == 300.0

        di = item.to_dict()
        assert di["stock_item_id"] == stock.id
        assert di["material_name"] == "MDF 18mm"
        assert di["quantity"] == 2
        assert di["unit_price"] == 150
        assert di["total"] == 300.0

        oid = order.id
        db.session.delete(order)
        db.session.commit()
        assert db.session.query(PurchaseItem).filter_by(order_id=oid).count() == 0


def test_purchase_item_model(client):
    _login(client)
    import datetime

    with client.application.app_context():
        from app.models.models import Category, PurchaseItem, PurchaseOrder, StockItem, Supplier

        cat = Category(name="Cat Compras PI", category_type="STOCK")
        db.session.add(cat)
        db.session.flush()
        stock = StockItem(
            name="MDF 18mm",
            sku="MDF-18-PI-0001",
            category_id=cat.id,
            quantity=10,
            min_quantity=2,
        )
        db.session.add(stock)
        sup = Supplier(name="Fornecedor PI Teste")
        db.session.add(sup)
        db.session.flush()

        order = PurchaseOrder(
            number="PC-TESTE-0001",
            status="SOLICITADA",
            supplier_id=sup.id,
            request_date=datetime.date.today(),
        )
        db.session.add(order)
        db.session.flush()

        item = PurchaseItem(
            order=order,
            stock_item_id=stock.id,
            material_name="MDF 18mm",
            quantity=2,
            unit_price=150,
            position=0,
        )
        db.session.add(item)
        db.session.commit()

        assert order.number == "PC-TESTE-0001"
        d = order.to_dict()
        assert d["number"] == "PC-TESTE-0001"
        assert d["status"] == "SOLICITADA"
        assert d["supplier_name"] == sup.name
        assert len(d["items"]) == 1
        assert d["total"] == 300.0

        di = item.to_dict()
        assert di["stock_item_id"] == stock.id
        assert di["material_name"] == "MDF 18mm"
        assert di["quantity"] == 2
        assert di["unit_price"] == 150
        assert di["total"] == 300.0

        oid = order.id
        db.session.delete(order)
        db.session.commit()
        assert db.session.query(PurchaseItem).filter_by(order_id=oid).count() == 0


def test_purchases_crud(client):
    h = _login(client)
    import datetime

    with client.application.app_context():
        from app.models.models import Category, StockItem

        cat = Category(name="Cat Compras CRUD", category_type="STOCK")
        db.session.add(cat)
        db.session.flush()
        stock = StockItem(
            name="MDF CRUD",
            sku="MDF-CRUD-0001",
            category_id=cat.id,
            quantity=5,
            min_quantity=1,
        )
        db.session.add(stock)
        db.session.commit()
        stock_id = stock.id

    sup_resp = client.post("/api/suppliers", headers=h, json={"name": "Fornecedor CRUD"})
    assert sup_resp.status_code == 201, sup_resp.get_data(as_text=True)
    supplier_id = sup_resp.get_json()["id"]

    today = datetime.date.today().isoformat()
    expected = (datetime.date.today() + datetime.timedelta(days=7)).isoformat()
    payload = {
        "supplier_id": supplier_id,
        "request_date": today,
        "expected_date": expected,
        "notes": "compra teste",
        "items": [
            {"material_name": "MDF 18mm", "quantity": 2, "unit_price": 150, "stock_item_id": stock_id},
            {"material_name": "Parafuso", "quantity": 10, "unit_price": 2},
        ],
    }
    r = client.post("/api/purchases", headers=h, json=payload)
    assert r.status_code == 201, r.get_data(as_text=True)
    body = r.get_json()
    assert body["number"].startswith("PC-")
    assert body["status"] == "SOLICITADA"
    assert body["total"] == 320
    assert len(body["items"]) == 2
    order_id = body["id"]

    r = client.get("/api/purchases", headers=h)
    assert r.status_code == 200
    assert len(r.get_json()) == 1

    r = client.get("/api/purchases", headers=h, query_string={"status": "SOLICITADA"})
    assert r.status_code == 200
    assert len(r.get_json()) == 1

    r = client.get("/api/purchases", headers=h, query_string={"status": "RECEBIDA"})
    assert r.status_code == 200
    assert len(r.get_json()) == 0

    r = client.put(
        f"/api/purchases/{order_id}",
        headers=h,
        json={
            "notes": "atualizado",
            "status": "APROVADA",
            "items": [
                {"material_name": "MDF 15mm", "quantity": 1, "unit_price": 100},
            ],
        },
    )
    assert r.status_code == 200, r.get_data(as_text=True)
    assert r.get_json()["notes"] == "atualizado"
    assert r.get_json()["status"] == "APROVADA"

    r = client.delete(f"/api/purchases/{order_id}", headers=h)
    assert r.status_code == 204, r.get_data(as_text=True)

    r = client.get("/api/purchases", headers=h)
    assert r.status_code == 200
    assert len(r.get_json()) == 0

    # supplier opcional
    r2 = client.post(
        "/api/purchases",
        headers=h,
        json={
            "request_date": today,
            "notes": "sem fornecedor",
            "items": [{"material_name": "MDF Livre", "quantity": 1, "unit_price": 10}],
        },
    )
    assert r2.status_code == 201, r2.get_data(as_text=True)
    assert r2.get_json()["supplier_id"] is None


def test_purchase_receive_gera_stock_movement(client):
    h = _login(client)
    import datetime

    with client.application.app_context():
        from app.models.models import Category, StockItem

        cat = Category(name="Cat Compras RECV", category_type="STOCK")
        db.session.add(cat)
        db.session.flush()
        stock = StockItem(
            name="MDF RECV",
            sku="MDF-RECV-0001",
            category_id=cat.id,
            quantity=5,
            min_quantity=1,
        )
        db.session.add(stock)
        db.session.commit()
        stock_id = stock.id

    sup_id = client.post("/api/suppliers", headers=h, json={"name": "Fornecedor RECV"}).get_json()["id"]
    today = datetime.date.today().isoformat()
    r = client.post(
        "/api/purchases",
        headers=h,
        json={
            "supplier_id": sup_id,
            "request_date": today,
            "status": "APROVADA",
            "notes": "para recebimento",
            "items": [
                {"material_name": "MDF 18mm", "quantity": 3, "unit_price": 10, "stock_item_id": stock_id},
                {"material_name": "Cola", "quantity": 2, "unit_price": 5},
            ],
        },
    )
    assert r.status_code == 201, r.get_data(as_text=True)
    order_id = r.get_json()["id"]

    r = client.post(f"/api/purchases/{order_id}/receive", headers=h)
    assert r.status_code == 200, r.get_data(as_text=True)
    body = r.get_json()
    assert body["status"] == "RECEBIDA"
    assert body["received_at"] is not None
    assert body["items"][0]["received_qty"] == 3

    with client.application.app_context():
        from app.models.models import StockItem, StockMovement

        item = db.session.get(StockItem, stock_id)
        assert float(item.quantity) == 8, f"quantity {item.quantity} != 8"
        movs = db.session.query(StockMovement).filter_by(item_id=stock_id).all()
        assert len(movs) >= 1
        assert any(float(m.quantity) == 3 and m.type == "ENTRADA" for m in movs)
        assert not any(float(m.quantity) == 2 for m in movs if m.item_id == stock_id and float(m.quantity) == 2)

    r2 = client.get(f"/api/stock/{stock_id}", headers=h)
    if r2.status_code == 200:
        assert r2.get_json()["quantity"] == 8


def test_purchase_receive_sem_item_estoque(client):
    h = _login(client)
    import datetime

    today = datetime.date.today().isoformat()
    r = client.post(
        "/api/purchases",
        headers=h,
        json={
            "request_date": today,
            "status": "APROVADA",
            "items": [{"material_name": "Material Livre", "quantity": 4, "unit_price": 20}],
        },
    )
    assert r.status_code == 201, r.get_data(as_text=True)
    order_id = r.get_json()["id"]

    with client.application.app_context():
        from app.models.models import StockMovement

        before = db.session.query(StockMovement).count()

    r = client.post(f"/api/purchases/{order_id}/receive", headers=h)
    assert r.status_code == 200, r.get_data(as_text=True)
    body = r.get_json()
    assert body["status"] == "RECEBIDA"
    assert body["items"][0]["received_qty"] == 4

    with client.application.app_context():
        from app.models.models import StockMovement

        after = db.session.query(StockMovement).count()
        assert after == before


def test_purchase_validations(client):
    h = _login(client)
    import datetime

    today = datetime.date.today().isoformat()

    # sem items
    r = client.post("/api/purchases", headers=h, json={"request_date": today, "items": []})
    assert r.status_code == 400, r.get_data(as_text=True)
    assert "items" in r.get_json().get("detail", "").lower()

    # quantity <=0
    r = client.post(
        "/api/purchases",
        headers=h,
        json={"request_date": today, "items": [{"material_name": "MDF", "quantity": 0, "unit_price": 10}]},
    )
    assert r.status_code == 400, r.get_data(as_text=True)

    # material_name vazio
    r = client.post(
        "/api/purchases",
        headers=h,
        json={"request_date": today, "items": [{"material_name": "   ", "quantity": 1, "unit_price": 10}]},
    )
    assert r.status_code == 400, r.get_data(as_text=True)

    # supplier_id inexistente
    r = client.post(
        "/api/purchases",
        headers=h,
        json={
            "request_date": today,
            "supplier_id": "id-inexistente-xyz",
            "items": [{"material_name": "MDF", "quantity": 1, "unit_price": 10}],
        },
    )
    assert r.status_code == 400, r.get_data(as_text=True)

    # cria compra valida para testar receive/delete quando RECEBIDA
    r = client.post(
        "/api/purchases",
        headers=h,
        json={
            "request_date": today,
            "status": "APROVADA",
            "items": [{"material_name": "MDF", "quantity": 1, "unit_price": 10}],
        },
    )
    assert r.status_code == 201, r.get_data(as_text=True)
    oid = r.get_json()["id"]

    r = client.post(f"/api/purchases/{oid}/receive", headers=h)
    assert r.status_code == 200, r.get_data(as_text=True)

    # receive quando ja RECEBIDA
    r = client.post(f"/api/purchases/{oid}/receive", headers=h)
    assert r.status_code == 400, r.get_data(as_text=True)

    # DELETE quando RECEBIDA
    r = client.delete(f"/api/purchases/{oid}", headers=h)
    assert r.status_code == 400, r.get_data(as_text=True)


def test_supplier_campos_ricos(client):
    h = _login(client)
    payload = {
        "name": "Fornecedor Rico",
        "cnpj": "12.345.678/0001-99",
        "contact": "Ana",
        "phone": "(11) 99999-0000",
        "email": "rico@test.com",
        "address": "Rua A, 123",
        "category": "  Ferragens  ",
        "payment_terms": "  28 dias  ",
        "avg_delivery_days": 7,
    }
    r = client.post("/api/suppliers", headers=h, json=payload)
    assert r.status_code == 201, r.get_data(as_text=True)
    body = r.get_json()
    sid = body["id"]
    assert body["address"] == "Rua A, 123"
    assert body["category"] == "Ferragens"
    assert body["payment_terms"] == "28 dias"
    assert body["avg_delivery_days"] == 7

    lst = client.get("/api/suppliers", headers=h).get_json()
    row = next(s for s in lst if s["id"] == sid)
    assert row["address"] == "Rua A, 123"
    assert row["category"] == "Ferragens"
    assert row["payment_terms"] == "28 dias"
    assert row["avg_delivery_days"] == 7

    r2 = client.put(
        f"/api/suppliers/{sid}",
        headers=h,
        json={"category": "  MDF  ", "payment_terms": "  30 dias  ", "avg_delivery_days": 14, "address": "Rua B, 456"},
    )
    assert r2.status_code == 200, r2.get_data(as_text=True)
    assert r2.get_json()["category"] == "MDF"
    assert r2.get_json()["payment_terms"] == "30 dias"
    assert r2.get_json()["avg_delivery_days"] == 14
    assert r2.get_json()["address"] == "Rua B, 456"

    lst2 = client.get("/api/suppliers", headers=h).get_json()
    row2 = next(s for s in lst2 if s["id"] == sid)
    assert row2["category"] == "MDF"
    assert row2["payment_terms"] == "30 dias"
    assert row2["avg_delivery_days"] == 14
    assert row2["address"] == "Rua B, 456"

    # validacoes: avg_delivery_days negativo deve dar 400
    r3 = client.post("/api/suppliers", headers=h, json={"name": "Forn Neg", "avg_delivery_days": -1})
    assert r3.status_code == 400, r3.get_data(as_text=True)
    assert "avg_delivery_days" in r3.get_json().get("detail", "").lower()

    r4 = client.put(f"/api/suppliers/{sid}", headers=h, json={"avg_delivery_days": -5})
    assert r4.status_code == 400, r4.get_data(as_text=True)

    # category vazia aceita mas se fornecida trim (ja validado acima)
    r5 = client.post("/api/suppliers", headers=h, json={"name": "Forn Vazio", "category": ""})
    assert r5.status_code == 201, r5.get_data(as_text=True)
    assert r5.get_json()["category"] == ""


def test_supplier_filtros_e_compat(client):
    h = _login(client)
    # criar dois fornecedores com categorias distintas
    r1 = client.post("/api/suppliers", headers=h, json={"name": "Forn Filtro MDF", "category": "MDF"})
    assert r1.status_code == 201, r1.get_data(as_text=True)
    r2 = client.post("/api/suppliers", headers=h, json={"name": "Forn Filtro Ferragens", "category": "Ferragens"})
    assert r2.status_code == 201, r2.get_data(as_text=True)

    # GET filtrado por category=MDF
    lst = client.get("/api/suppliers", headers=h, query_string={"category": "MDF"}).get_json()
    assert any(s["id"] == r1.get_json()["id"] for s in lst)
    assert all(s["category"] == "MDF" for s in lst)

    # compat: criar sem campos novos (so name) deve dar 201 com defaults
    r3 = client.post("/api/suppliers", headers=h, json={"name": "Forn Compat"})
    assert r3.status_code == 201, r3.get_data(as_text=True)
    body = r3.get_json()
    assert body["name"] == "Forn Compat"
    # defaults vazios/None
    assert body.get("address") == ""
    assert body.get("category") == ""
    assert body.get("payment_terms") == ""
    assert body.get("avg_delivery_days") is None


def test_ticket_model(client):
    _login(client)
    with client.application.app_context():
        from app.extensions import db
        from app.models.models import Client, ServiceTicket

        c = Client(name="Cliente Teste")
        db.session.add(c)
        db.session.commit()
        ticket = ServiceTicket(
            number="CH-TESTE-0001",
            client_id=c.id,
            description="Porta desalinhou",
            status="ABERTO",
            cost=150.5,
            in_warranty=True,
        )
        db.session.add(ticket)
        db.session.commit()
        d = ticket.to_dict()
        assert d["number"] == "CH-TESTE-0001"
        assert d["client_id"] == c.id
        assert d["client_name"] == "Cliente Teste"
        assert d["status"] == "ABERTO"
        assert d["cost"] == 150.5
        assert d["in_warranty"] is True
        assert d["opened_at"] is not None
        assert d["scheduled_at"] is None
        assert d["resolved_at"] is None
        assert d["description"] == "Porta desalinhou"


def test_ticket_photo_cascade(client):
    _login(client)
    with client.application.app_context():
        from app.extensions import db
        from app.models.models import Client, ServiceTicket, TicketPhoto

        c = Client(name="Cliente Foto")
        db.session.add(c)
        db.session.commit()
        ticket = ServiceTicket(
            number="CH-TESTE-0002",
            client_id=c.id,
            description="Teste foto",
            status="ABERTO",
        )
        db.session.add(ticket)
        db.session.commit()
        photo = TicketPhoto(
            ticket_id=ticket.id,
            filename="foto.jpg",
            stored_name="abc.jpg",
            mime_type="image/jpeg",
            size=1024,
        )
        db.session.add(photo)
        db.session.commit()
        assert len(ticket.photos) == 1
        tid = ticket.id
        db.session.delete(ticket)
        db.session.commit()
        assert db.session.query(TicketPhoto).filter_by(ticket_id=tid).count() == 0


def test_tickets_crud(client):
    h = _login(client)
    with client.application.app_context():
        from app.models.models import Client, Project
        c = Client(name="Cliente Ticket")
        db.session.add(c)
        db.session.flush()
        p = Project(client_id=c.id, title="Proj Ticket", status="ORCAMENTO")
        db.session.add(p)
        db.session.commit()
        cid = c.id
        pid = p.id
    r = client.post("/api/tickets", headers=h, json={"client_id": cid, "project_id": pid, "description": "Porta desalinhou", "cost": 100, "cause": "Dobradica", "in_warranty": True})
    assert r.status_code == 201, r.get_data(as_text=True)
    body = r.get_json()
    tid = body["id"]
    assert body["number"].startswith("CH-")
    assert body["status"] == "ABERTO"
    assert body["client_name"] == "Cliente Ticket"
    assert body["cost"] == 100
    assert client.get("/api/tickets", headers=h).get_json().__len__() == 1
    assert len(client.get("/api/tickets", headers=h, query_string={"status": "ABERTO"}).get_json()) == 1
    assert len(client.get("/api/tickets", headers=h, query_string={"status": "RESOLVIDO"}).get_json()) == 0
    r2 = client.get(f"/api/tickets/{tid}", headers=h)
    assert r2.status_code == 200
    assert r2.get_json()["photos"] == []
    r3 = client.put(f"/api/tickets/{tid}", headers=h, json={"status": "EM_ANALISE", "cost": 200, "solution": "Ajuste"})
    assert r3.status_code == 200, r3.get_data(as_text=True)
    assert r3.get_json()["status"] == "EM_ANALISE"
    assert r3.get_json()["cost"] == 200
    r4 = client.delete(f"/api/tickets/{tid}", headers=h)
    assert r4.status_code in (200, 204), r4.get_data(as_text=True)
    assert len(client.get("/api/tickets", headers=h).get_json()) == 0
    # validacoes client
    r5 = client.post("/api/tickets", headers=h, json={"description": "sem client"})
    assert r5.status_code == 400, r5.get_data(as_text=True)
    assert "client_id" in r5.get_json().get("detail", "").lower()
    r6 = client.post("/api/tickets", headers=h, json={"client_id": "id-inexistente", "description": "x"})
    assert r6.status_code == 404, r6.get_data(as_text=True)
    r7 = client.post("/api/tickets", headers=h, json={"client_id": cid, "project_id": "proj-inexistente", "description": "x"})
    assert r7.status_code == 404, r7.get_data(as_text=True)


def test_ticket_status_fluxo(client):
    h = _login(client)
    with client.application.app_context():
        from app.models.models import Client
        c = Client(name="Cliente Fluxo")
        db.session.add(c)
        db.session.commit()
        cid = c.id
    r = client.post("/api/tickets", headers=h, json={"client_id": cid, "description": "Fluxo teste"})
    assert r.status_code == 201, r.get_data(as_text=True)
    tid = r.get_json()["id"]
    import datetime as _dt
    today = _dt.date.today().isoformat()
    # ABERTO -> EM_ANALISE
    assert client.put(f"/api/tickets/{tid}", headers=h, json={"status": "EM_ANALISE"}).status_code == 200
    # EM_ANALISE -> AGENDADO com scheduled_at deve criar CalendarEvent ASSISTENCIA
    r2 = client.put(f"/api/tickets/{tid}", headers=h, json={"status": "AGENDADO", "scheduled_at": today})
    assert r2.status_code == 200, r2.get_data(as_text=True)
    with client.application.app_context():
        from app.models.models import CalendarEvent
        evs = db.session.query(CalendarEvent).filter_by(type="ASSISTENCIA").all()
        assert len(evs) >= 1, "CalendarEvent ASSISTENCIA nao criado"
        assert any(e.client_id == cid for e in evs)
    # AGENDADO -> EM_ATENDIMENTO
    assert client.put(f"/api/tickets/{tid}", headers=h, json={"status": "EM_ATENDIMENTO"}).status_code == 200
    # EM_ATENDIMENTO -> RESOLVIDO deve preencher resolved_at
    r3 = client.put(f"/api/tickets/{tid}", headers=h, json={"status": "RESOLVIDO"})
    assert r3.status_code == 200, r3.get_data(as_text=True)
    assert r3.get_json()["resolved_at"] is not None
    # RESOLVIDO -> ENCERRADO deve preencher closed_at
    r4 = client.put(f"/api/tickets/{tid}", headers=h, json={"status": "ENCERRADO"})
    assert r4.status_code == 200, r4.get_data(as_text=True)
    assert r4.get_json()["closed_at"] is not None


def test_ticket_agendado_cria_evento_calendario(client):
    h = _login(client)
    with client.application.app_context():
        from app.models.models import Client, Project
        c = Client(name="Cliente Agenda")
        db.session.add(c)
        db.session.flush()
        p = Project(client_id=c.id, title="Proj Agenda", status="ORCAMENTO")
        db.session.add(p)
        db.session.commit()
        cid = c.id
        pid = p.id
        uid = db.session.query(User).filter_by(username="admin").first().id
    import datetime as _dt
    tomorrow = (_dt.date.today() + _dt.timedelta(days=1)).isoformat()
    r = client.post("/api/tickets", headers=h, json={"client_id": cid, "project_id": pid, "description": "Agendamento auto"})
    assert r.status_code == 201, r.get_data(as_text=True)
    tid = r.get_json()["id"]
    number = r.get_json()["number"]
    # PUT para AGENDADO com assigned_user_id
    r2 = client.put(f"/api/tickets/{tid}", headers=h, json={"status": "AGENDADO", "scheduled_at": tomorrow, "assigned_user_id": uid})
    assert r2.status_code == 200, r2.get_data(as_text=True)
    body = r2.get_json()
    assert body["calendar_event_id"] is not None
    with client.application.app_context():
        from app.models.models import CalendarEvent
        ev = db.session.get(CalendarEvent, body["calendar_event_id"])
        assert ev is not None
        assert ev.type == "ASSISTENCIA"
        assert ev.client_id == cid
        assert ev.project_id == pid
        assert ev.assigned_user_id == uid
        assert number in ev.title or "Agendamento auto" in ev.title or body["description"][:10] in ev.title
        before_id = ev.id
        before_cnt = db.session.query(CalendarEvent).filter_by(type="ASSISTENCIA").count()
    # mudar de AGENDADO para outro status nao deve duplicar evento
    r3 = client.put(f"/api/tickets/{tid}", headers=h, json={"status": "EM_ATENDIMENTO"})
    assert r3.status_code == 200
    assert r3.get_json()["calendar_event_id"] == before_id
    with client.application.app_context():
        from app.models.models import CalendarEvent
        after_cnt = db.session.query(CalendarEvent).filter_by(type="ASSISTENCIA").count()
        assert after_cnt == before_cnt


def test_ticket_photo_upload(client, tmp_path):
    with client.application.app_context():
        client.application.config["UPLOAD_DIR"] = str(tmp_path)
    h = _login(client)
    with client.application.app_context():
        from app.models.models import Client
        c = Client(name="Cliente Foto Upload")
        db.session.add(c)
        db.session.commit()
        cid = c.id
    r = client.post("/api/tickets", headers=h, json={"client_id": cid, "description": "foto upload"})
    assert r.status_code == 201, r.get_data(as_text=True)
    tid = r.get_json()["id"]
    import io
    data = {"file": (io.BytesIO(b"fake image data"), "foto_teste.jpg")}
    r2 = client.post(f"/api/tickets/{tid}/photos", headers=h, data=data, content_type="multipart/form-data")
    assert r2.status_code == 201, r2.get_data(as_text=True)
    photo = r2.get_json()
    assert "filename" in photo
    pid = photo["id"]
    # GET ticket deve incluir photos
    r3 = client.get(f"/api/tickets/{tid}", headers=h)
    assert r3.status_code == 200
    assert len(r3.get_json()["photos"]) == 1
    # download
    r4 = client.get(f"/api/tickets/photos/{pid}/download", headers=h)
    assert r4.status_code == 200
    assert r4.mimetype in ("image/jpeg", "application/octet-stream", "image/jpg")
    # delete
    r5 = client.delete(f"/api/tickets/photos/{pid}", headers=h)
    assert r5.status_code == 200
    assert r5.get_json().get("ok") is True
    # validacoes
    r6 = client.post("/api/tickets/id-inexistente/photos", headers=h, data={"file": (io.BytesIO(b"x"), "a.jpg")}, content_type="multipart/form-data")
    assert r6.status_code == 404
    r7 = client.post(f"/api/tickets/{tid}/photos", headers=h, data={}, content_type="multipart/form-data")
    assert r7.status_code == 400
    # sem token
    r8 = client.post(f"/api/tickets/{tid}/photos", data={"file": (io.BytesIO(b"x"), "a.jpg")}, content_type="multipart/form-data")
    assert r8.status_code == 401


def test_ticket_validations(client):
    h = _login(client)
    with client.application.app_context():
        from app.models.models import Client
        c = Client(name="Cliente Valid")
        db.session.add(c)
        db.session.commit()
        cid = c.id
    # POST sem description
    r = client.post("/api/tickets", headers=h, json={"client_id": cid})
    assert r.status_code == 400, r.get_data(as_text=True)
    # criar valido
    r2 = client.post("/api/tickets", headers=h, json={"client_id": cid, "description": "valid test"})
    assert r2.status_code == 201
    tid = r2.get_json()["id"]
    # PUT status invalido
    r3 = client.put(f"/api/tickets/{tid}", headers=h, json={"status": "INVALIDO"})
    assert r3.status_code == 400, r3.get_data(as_text=True)
    # levar para RESOLVIDO e tentar DELETE -> 400
    client.put(f"/api/tickets/{tid}", headers=h, json={"status": "RESOLVIDO"})
    r4 = client.delete(f"/api/tickets/{tid}", headers=h)
    assert r4.status_code == 400, r4.get_data(as_text=True)
    # levar para ENCERRADO e tentar DELETE -> 400
    client.put(f"/api/tickets/{tid}", headers=h, json={"status": "ENCERRADO"})
    r5 = client.delete(f"/api/tickets/{tid}", headers=h)
    assert r5.status_code == 400, r5.get_data(as_text=True)
    # GET inexistente
    assert client.get("/api/tickets/id-inexistente-xyz", headers=h).status_code == 404


def test_report_tickets(client):
    h = _login(client)
    # cria Client via API
    r_client = client.post("/api/clients", headers=h, json={"name": "Cliente Report Tickets", "cpf_cnpj": "00000000003"})
    assert r_client.status_code == 201, r_client.get_data(as_text=True)
    cid = r_client.get_json()["id"]

    # ticket1 ABERTO com cost 100 in_warranty True cause Dobradiça description Porta desalinhou
    r1 = client.post("/api/tickets", headers=h, json={"client_id": cid, "description": "Porta desalinhou", "cost": 100, "in_warranty": True, "cause": "Dobradiça", "status": "ABERTO"})
    assert r1.status_code == 201, r1.get_data(as_text=True)
    t1 = r1.get_json()
    assert t1["status"] == "ABERTO"

    # ticket2 RESOLVIDO com cost 250 in_warranty False cause Puxador (ao criar ja RESOLVIDO deve preencher resolved_at auto)
    r2 = client.post("/api/tickets", headers=h, json={"client_id": cid, "description": "Gaveta emperrada", "cost": 250, "in_warranty": False, "cause": "Puxador", "status": "RESOLVIDO"})
    assert r2.status_code == 201, r2.get_data(as_text=True)
    t2 = r2.get_json()
    assert t2["status"] == "RESOLVIDO"
    assert t2["resolved_at"] is not None

    # ticket extra ENCERRADO
    r3 = client.post("/api/tickets", headers=h, json={"client_id": cid, "description": "Reparo finalizado", "cost": 0, "cause": "Outro", "status": "ENCERRADO"})
    assert r3.status_code == 201, r3.get_data(as_text=True)
    assert r3.get_json()["status"] == "ENCERRADO"

    # GET /api/reports/tickets
    r_rep = client.get("/api/reports/tickets", headers=h)
    assert r_rep.status_code == 200, r_rep.get_data(as_text=True)
    body = r_rep.get_json()
    title = body.get("title", "")
    assert "Tickets" in title or "Pos-venda" in title or "Pós-venda" in title, f"title unexpected: {title}"

    summary = body.get("summary", [])
    def find(label_substr):
        for s in summary:
            if label_substr.lower() in s.get("label", "").lower():
                return s
        return None
    total_item = find("Total de Chamados")
    assert total_item is not None, f"summary sem Total de Chamados: {summary}"
    assert total_item["value"] == "3"
    abertos_item = find("Abertos")
    assert abertos_item is not None
    assert abertos_item["value"] == "1"
    resolvidos_item = find("Resolvidos")
    assert resolvidos_item is not None
    encerrados_item = find("Encerrados")
    assert encerrados_item is not None
    # Custo Total igual 350
    custo_total_item = find("Custo Total")
    assert custo_total_item is not None
    val = custo_total_item["value"]
    # aceita R$ 350,00 ou 350
    assert "350" in val, f"Custo Total: {val}"
    custo_medio_item = find("Custo Medio") or find("Custo Médio")
    assert custo_medio_item is not None
    dentro_item = find("Dentro")
    assert dentro_item is not None
    assert dentro_item["value"] == "1"
    fora_item = find("Fora")
    assert fora_item is not None
    assert fora_item["value"] == "1"
    tempo_item = find("Tempo Medio") or find("Tempo Médio")
    assert tempo_item is not None
    columns = body.get("columns", [])
    assert len(columns) > 0
    keys = [c.get("key") for c in columns]
    assert any(k in keys for k in ["status", "count", "causa", "custo", "description", "group"]), f"columns keys: {keys}"
    rows = body.get("rows", [])
    assert len(rows) > 0, "rows vazio"
    rows_str = str(rows)
    assert "Porta desalinhou" in rows_str or "Dobradiça" in rows_str, f"rows nao contem descricao/causa esperada: {rows}"
    # export (verifica que nao 404) — formato via ?format=json deve retornar json
    r_json = client.get("/api/reports/tickets?format=json", headers=h)
    assert r_json.status_code == 200, r_json.get_data(as_text=True)
    assert r_json.is_json
    for fmt in ["pdf", "xlsx"]:
        r_exp = client.get(f"/api/reports/tickets/export?format={fmt}", headers=h)
        assert r_exp.status_code == 200, f"export {fmt} failed: {r_exp.get_data(as_text=True)[:200]}"
        r_exp2 = client.get(f"/api/reports/tickets?format={fmt}", headers=h)
        assert r_exp2.status_code == 200


def test_environments_model(client):
    _login(client)
    from app.extensions import db
    from app.models.models import Client, Project, ProjectEnvironment

    with client.application.app_context():
        c = Client(name="Cliente Ambientes")
        db.session.add(c)
        db.session.commit()
        p = Project(client_id=c.id, title="Projeto Ambientes", status="ORCAMENTO", value=50000)
        db.session.add(p)
        db.session.commit()
        env1 = ProjectEnvironment(
            project_id=p.id,
            name="Cozinha",
            env_type="COZINHA",
            area_m2=32,
            value=15000,
            status="PLANEJADO",
        )
        env2 = ProjectEnvironment(
            project_id=p.id,
            name="Quarto",
            env_type="QUARTO",
            area_m2=21,
            value=9000,
            status="EM_PRODUCAO",
        )
        db.session.add_all([env1, env2])
        db.session.commit()

        d1 = env1.to_dict()
        assert d1["project_title"] == "Projeto Ambientes"
        assert d1["name"] == "Cozinha"
        assert d1["env_type"] == "COZINHA"

        d_proj = p.to_dict()
        assert len(d_proj["environments"]) == 2
        assert d_proj["total_area_m2"] == 53.0
        assert d_proj["total_environments"] == 2


def test_workers_machines_model(client):
    _login(client)
    from app.extensions import db
    from app.models.models import Machine, Worker

    with client.application.app_context():
        w = Worker(name="Carlos", active=True)
        m = Machine(name="Serra Circular")
        db.session.add_all([w, m])
        db.session.commit()

        dw = w.to_dict()
        assert dw["name"] == "Carlos"
        assert dw["active"] is True
        assert dw["created_at"] is not None

        dm = m.to_dict()
        assert dm["name"] == "Serra Circular"
        # Machine active default True (bool True mesmo sem passar explicito)
        assert dm["active"] is True
        assert dm["created_at"] is not None


def test_time_entries_model(client):
    _login(client)
    import datetime

    from app.extensions import db
    from app.models.models import Client, Machine, Project, ProjectEnvironment, TimeEntry, Worker

    with client.application.app_context():
        c = Client(name="Cliente Apontamento")
        db.session.add(c)
        db.session.commit()
        p = Project(client_id=c.id, title="Projeto Apontamento", status="PRODUCAO")
        db.session.add(p)
        db.session.commit()
        env = ProjectEnvironment(
            project_id=p.id, name="Sala", env_type="SALA", area_m2=15, value=5000, status="EM_PRODUCAO"
        )
        db.session.add(env)
        db.session.commit()
        w = Worker(name="Apontador 1")
        db.session.add(w)
        db.session.commit()
        m = Machine(name="Maquina Apontamento")
        db.session.add(m)
        db.session.commit()

        te = TimeEntry(
            project_id=p.id,
            environment_id=env.id,
            worker_id=w.id,
            machine_id=m.id,
            hours=8,
            hours_type="PRODUTIVA",
            work_date=datetime.date.today(),
            notes="dia cheio",
        )
        db.session.add(te)
        db.session.commit()

        d = te.to_dict()
        assert d["project_title"] == "Projeto Apontamento"
        assert d["environment_name"] == "Sala"
        assert d["worker_name"] == "Apontador 1"
        assert d["machine_name"] == "Maquina Apontamento"
        assert d["hours"] == 8
        assert d["hours_type"] == "PRODUTIVA"
        assert d["work_date"] == datetime.date.today().isoformat()
        assert d["notes"] == "dia cheio"


def test_production_issues_model(client):
    _login(client)
    import datetime

    from app.extensions import db
    from app.models.models import Client, ProductionIssue, Project, ProjectEnvironment, TimeEntry, Worker

    with client.application.app_context():
        c = Client(name="Cliente Issues")
        db.session.add(c)
        db.session.commit()
        p = Project(client_id=c.id, title="Projeto Issues", status="PRODUCAO")
        db.session.add(p)
        db.session.commit()
        w = Worker(name="Funcionario Issues")
        db.session.add(w)
        db.session.commit()

        # Ambiente e apontamento para validar cascade (Project -> env + time_entry + issues)
        env = ProjectEnvironment(
            project_id=p.id, name="Cozinha Issues", env_type="COZINHA", area_m2=10, value=1000, status="PLANEJADO"
        )
        db.session.add(env)
        db.session.commit()
        te = TimeEntry(
            project_id=p.id,
            environment_id=env.id,
            worker_id=w.id,
            hours=2,
            hours_type="PRODUTIVA",
            work_date=datetime.date.today(),
        )
        db.session.add(te)
        db.session.commit()

        today = datetime.date.today()
        iss1 = ProductionIssue(
            kind="RETRABALHO",
            project_id=p.id,
            worker_id=w.id,
            hours_spent=2.5,
            cost=120,
            reason="Peça riscada",
            issue_date=today,
        )
        iss2 = ProductionIssue(
            kind="DESPERDICIO",
            project_id=p.id,
            material="MDF",
            quantity=1,
            reason="Corte errado",
            issue_date=today,
        )
        iss3 = ProductionIssue(
            kind="PERDA",
            project_id=p.id,
            cost=300,
            reason="Furto de chapa",
            issue_date=today,
        )
        db.session.add_all([iss1, iss2, iss3])
        db.session.commit()

        d1 = iss1.to_dict()
        assert d1["kind"] == "RETRABALHO"
        assert d1["hours_spent"] == 2.5
        assert d1["cost"] == 120
        assert d1["reason"] == "Peça riscada"
        assert d1["project_title"] == "Projeto Issues"
        assert d1["worker_name"] == "Funcionario Issues"

        d2 = iss2.to_dict()
        assert d2["kind"] == "DESPERDICIO"
        assert d2["material"] == "MDF"
        assert d2["quantity"] == 1
        assert d2["reason"] == "Corte errado"

        d3 = iss3.to_dict()
        assert d3["kind"] == "PERDA"
        assert d3["cost"] == 300
        assert d3["reason"] == "Furto de chapa"

        pid = p.id
        db.session.delete(p)
        db.session.commit()
        assert db.session.query(ProductionIssue).filter_by(project_id=pid).count() == 0
        assert db.session.query(ProjectEnvironment).filter_by(project_id=pid).count() == 0
        assert db.session.query(TimeEntry).filter_by(project_id=pid).count() == 0


def test_environments_api(client):
    h = _login(client)
    # cria cliente + projeto via API
    cid = client.post("/api/clients", headers=h, json={"name": "Cli Env", "cpf_cnpj": "env1"}).get_json()["id"]
    pid = client.post("/api/projects", headers=h, json={"title": "Proj Env", "client_id": cid}).get_json()["id"]


    # POST /api/projects/<id>/environments
    r = client.post(f"/api/projects/{pid}/environments", headers=h,
                    json={"name": "Cozinha", "env_type": "COZINHA", "area_m2": 32, "value": 5000})
    assert r.status_code == 201, r.get_data(as_text=True)
    body = r.get_json()
    assert body["id"]
    assert body["name"] == "Cozinha"
    assert body["area_m2"] == 32
    assert body["project_title"] == "Proj Env"

    env_id = body["id"]

    # GET lista 1
    r = client.get(f"/api/projects/{pid}/environments", headers=h)
    assert r.status_code == 200, r.get_data(as_text=True)
    assert len(r.get_json()) == 1

    # PUT altera area_m2 para 35 value 6000 env_type SALA
    r = client.put(f"/api/environments/{env_id}", headers=h,
                   json={"area_m2": 35, "value": 6000, "env_type": "SALA"})
    assert r.status_code == 200, r.get_data(as_text=True)
    b = r.get_json()
    assert b["area_m2"] == 35
    assert b["value"] == 6000
    assert b["env_type"] == "SALA"

    # DELETE
    r = client.delete(f"/api/environments/{env_id}", headers=h)
    assert r.status_code == 200, r.get_data(as_text=True)

    # validacoes
    r = client.post(f"/api/projects/{pid}/environments", headers=h,
                    json={"env_type": "COZINHA"})
    assert r.status_code == 400, r.get_data(as_text=True)

    r = client.post(f"/api/projects/{pid}/environments", headers=h,
                    json={"name": "Teste", "env_type": "INVALIDO"})
    assert r.status_code == 400, r.get_data(as_text=True)

    r = client.post("/api/projects/id-inexistente/environments", headers=h,
                    json={"name": "X"})
    assert r.status_code == 404, r.get_data(as_text=True)


def test_workers_machines_api(client):
    h = _login(client)
    # Workers
    r = client.post("/api/workers", headers=h, json={"name": "Carlos"})
    assert r.status_code == 201, r.get_data(as_text=True)
    wid = r.get_json()["id"]

    r = client.get("/api/workers", headers=h)
    assert r.status_code == 200, r.get_data(as_text=True)
    assert len(r.get_json()) == 1

    r = client.put(f"/api/workers/{wid}", headers=h, json={"name": "Carlos Silva"})
    assert r.status_code == 200, r.get_data(as_text=True)
    assert r.get_json()["name"] == "Carlos Silva"

    # POST duplicado name deve dar 400 unique
    r = client.post("/api/workers", headers=h, json={"name": "Carlos Silva"})
    assert r.status_code == 400, r.get_data(as_text=True)

    # DELETE hard quando sem time_entries (200)
    r = client.delete(f"/api/workers/{wid}", headers=h)
    assert r.status_code == 200, r.get_data(as_text=True)

    # criar novamente para testar 400 quando em uso
    r = client.post("/api/workers", headers=h, json={"name": "Carlos Silva"})
    assert r.status_code == 201, r.get_data(as_text=True)
    wid2 = r.get_json()["id"]

    # criar dependencias para validar bloqueio
    cid = client.post("/api/clients", headers=h, json={"name": "Cli Work", "cpf_cnpj": "work1"}).get_json()["id"]
    pid = client.post("/api/projects", headers=h, json={"title": "Proj Work", "client_id": cid}).get_json()["id"]
    import datetime as _dt
    today = _dt.date.today().isoformat()
    r = client.post(f"/api/projects/{pid}/time", headers=h,
                    json={"worker_id": wid2, "hours": 2, "work_date": today})
    assert r.status_code == 201, r.get_data(as_text=True)

    r = client.delete(f"/api/workers/{wid2}", headers=h)
    assert r.status_code == 400, r.get_data(as_text=True)

    # Machines - mesmo fluxo
    r = client.post("/api/machines", headers=h, json={"name": "Serra"})
    assert r.status_code == 201, r.get_data(as_text=True)
    mid = r.get_json()["id"]

    r = client.get("/api/machines", headers=h)
    assert r.status_code == 200, r.get_data(as_text=True)
    assert len([x for x in r.get_json() if x["id"] == mid]) == 1

    r = client.put(f"/api/machines/{mid}", headers=h, json={"name": "Serra Circular"})
    assert r.status_code == 200, r.get_data(as_text=True)
    assert r.get_json()["name"] == "Serra Circular"

    r = client.post("/api/machines", headers=h, json={"name": "Serra Circular"})
    assert r.status_code == 400, r.get_data(as_text=True)

    r = client.delete(f"/api/machines/{mid}", headers=h)
    assert r.status_code == 200, r.get_data(as_text=True)


def test_time_entries_api(client):
    h = _login(client)
    import datetime as _dt
    today = _dt.date.today().isoformat()

    # cria Worker+Machine+Project+Environment
    wid = client.post("/api/workers", headers=h, json={"name": "Apontador TE"}).get_json()["id"]
    mid = client.post("/api/machines", headers=h, json={"name": "Maquina TE"}).get_json()["id"]
    cid = client.post("/api/clients", headers=h, json={"name": "Cli TE", "cpf_cnpj": "te1"}).get_json()["id"]
    pid = client.post("/api/projects", headers=h, json={"title": "Proj TE", "client_id": cid}).get_json()["id"]
    env_id = client.post(f"/api/projects/{pid}/environments", headers=h,
                         json={"name": "Sala TE", "env_type": "SALA"}).get_json()["id"]

    # POST /api/projects/<id>/time
    r = client.post(f"/api/projects/{pid}/time", headers=h,
                    json={"project_id": pid, "environment_id": env_id, "worker_id": wid, "machine_id": mid, "hours": 8, "hours_type": "PRODUTIVA", "work_date": today})
    assert r.status_code == 201, r.get_data(as_text=True)
    assert r.get_json()["hours"] == 8
    entry_id = r.get_json()["id"]

    # GET lista 1
    r = client.get(f"/api/projects/{pid}/time", headers=h)
    assert r.status_code == 200, r.get_data(as_text=True)
    assert len(r.get_json()) == 1

    # PUT altera hours para 9 IMPRODUTIVA
    r = client.put(f"/api/time-entries/{entry_id}", headers=h,
                   json={"hours": 9, "hours_type": "IMPRODUTIVA"})
    assert r.status_code == 200, r.get_data(as_text=True)
    b = r.get_json()
    assert b["hours"] == 9
    assert b["hours_type"] == "IMPRODUTIVA"

    # DELETE
    r = client.delete(f"/api/time-entries/{entry_id}", headers=h)
    assert r.status_code == 200, r.get_data(as_text=True)

    # Validacoes
    r = client.post(f"/api/projects/{pid}/time", headers=h,
                    json={"hours": 0, "work_date": today})
    assert r.status_code == 400, r.get_data(as_text=True)

    r = client.post(f"/api/projects/{pid}/time", headers=h,
                    json={"hours": 2, "hours_type": "INVALIDO", "work_date": today})
    assert r.status_code == 400, r.get_data(as_text=True)

    r = client.post(f"/api/projects/{pid}/time", headers=h,
                    json={"hours": 2, "worker_id": "id-inexistente", "work_date": today})
    assert r.status_code == 404, r.get_data(as_text=True)

    r = client.post("/api/projects/id-inexistente/time", headers=h,
                    json={"hours": 2, "work_date": today})
    assert r.status_code == 404, r.get_data(as_text=True)


def test_production_issues_api(client):
    h = _login(client)
    import datetime as _dt
    today = _dt.date.today().isoformat()

    wid = client.post("/api/workers", headers=h, json={"name": "Func Issues API"}).get_json()["id"]
    cid = client.post("/api/clients", headers=h, json={"name": "Cli Issues API", "cpf_cnpj": "issapi1"}).get_json()["id"]
    pid = client.post("/api/projects", headers=h, json={"title": "Proj Issues API", "client_id": cid}).get_json()["id"]

    # POST RETRABALHO
    r = client.post(f"/api/projects/{pid}/issues", headers=h,
                    json={"kind": "RETRABALHO", "worker_id": wid, "hours_spent": 2, "cost": 120, "reason": "Teste", "issue_date": today})
    assert r.status_code == 201, r.get_data(as_text=True)
    id1 = r.get_json()["id"]

    # POST DESPERDICIO
    r = client.post(f"/api/projects/{pid}/issues", headers=h,
                    json={"kind": "DESPERDICIO", "material": "MDF", "quantity": 1, "issue_date": today})
    assert r.status_code == 201, r.get_data(as_text=True)
    id2 = r.get_json()["id"]

    # POST PERDA
    r = client.post(f"/api/projects/{pid}/issues", headers=h,
                    json={"kind": "PERDA", "cost": 300, "issue_date": today})
    assert r.status_code == 201, r.get_data(as_text=True)
    id3 = r.get_json()["id"]

    # GET lista 3
    r = client.get(f"/api/projects/{pid}/issues", headers=h)
    assert r.status_code == 200, r.get_data(as_text=True)
    assert len(r.get_json()) == 3

    # PUT altera cost
    r = client.put(f"/api/issues/{id1}", headers=h, json={"cost": 200})
    assert r.status_code == 200, r.get_data(as_text=True)
    assert r.get_json()["cost"] == 200

    # DELETE
    r = client.delete(f"/api/issues/{id2}", headers=h)
    assert r.status_code == 200, r.get_data(as_text=True)

    # Validacoes
    r = client.post(f"/api/projects/{pid}/issues", headers=h,
                    json={"kind": "INVALIDO", "issue_date": today})
    assert r.status_code == 400, r.get_data(as_text=True)

    # RETRABALHO sem worker_id deve aceitar (cost nullable)
    r = client.post(f"/api/projects/{pid}/issues", headers=h,
                    json={"kind": "RETRABALHO", "cost": 50, "issue_date": today})
    assert r.status_code == 201, r.get_data(as_text=True)

    # se worker_id fornecido invalido 404
    r = client.post(f"/api/projects/{pid}/issues", headers=h,
                    json={"kind": "RETRABALHO", "worker_id": "id-inexistente", "issue_date": today})
    assert r.status_code == 404, r.get_data(as_text=True)

    # cost negativo 400
    r = client.post(f"/api/projects/{pid}/issues", headers=h,
                    json={"kind": "PERDA", "cost": -10, "issue_date": today})
    assert r.status_code == 400, r.get_data(as_text=True)

    # quantity negativo 400
    r = client.post(f"/api/projects/{pid}/issues", headers=h,
                    json={"kind": "DESPERDICIO", "quantity": -1, "issue_date": today})
    assert r.status_code == 400, r.get_data(as_text=True)

    # issue_date ausente deve usar today default (201)
    r = client.post(f"/api/projects/{pid}/issues", headers=h,
                    json={"kind": "PERDA", "cost": 10})
    assert r.status_code == 201, r.get_data(as_text=True)
    assert r.get_json()["issue_date"] == today


def test_project_prazo_status(client):
    h = _login(client)
    import datetime as _dt
    today = _dt.date.today()
    # cria Client via API
    r = client.post("/api/clients", headers=h, json={"name": "Cliente Prazo", "cpf_cnpj": "prazo01"})
    assert r.status_code == 201, r.get_data(as_text=True)
    cid = r.get_json()["id"]

    deadline_3 = (today + _dt.timedelta(days=3)).isoformat()
    start_iso = today.isoformat()
    planned_iso = (today + _dt.timedelta(days=10)).isoformat()

    # CENARIO PRINCIPAL: deadline em 3 dias -> LARANJA
    r = client.post("/api/projects", headers=h, json={
        "title": "Projeto X", "client_id": cid, "status": "ORCAMENTO",
        "deadline": deadline_3, "start_date": start_iso, "planned_end_date": planned_iso
    })
    assert r.status_code == 201, r.get_data(as_text=True)
    body = r.get_json()
    assert body["start_date"] == start_iso, f"start_date {body.get('start_date')} != {start_iso}"
    assert body["planned_end_date"] == planned_iso
    assert body["actual_end_date"] is None
    assert body["deadline_status"] == "LARANJA", f"expected LARANJA got {body.get('deadline_status')}"
    pid = body["id"]

    # GET deve refletir mesmo semaforo
    r2 = client.get(f"/api/projects/{pid}", headers=h)
    assert r2.status_code == 200
    gbody = r2.get_json()
    assert gbody["start_date"] == start_iso
    assert gbody["planned_end_date"] == planned_iso
    assert gbody["actual_end_date"] is None
    assert gbody["deadline_status"] == "LARANJA"
    assert gbody["deadline"] == deadline_3

    # CENARIO VERMELHO: deadline ontem + PRODUCAO
    deadline_yesterday = (today - _dt.timedelta(days=1)).isoformat()
    r = client.post("/api/projects", headers=h, json={
        "title": "Projeto Atrasado", "client_id": cid, "status": "PRODUCAO", "deadline": deadline_yesterday
    })
    assert r.status_code == 201, r.get_data(as_text=True)
    assert r.get_json()["deadline_status"] == "VERMELHO"

    # CENARIO VERDE: deadline em 20 dias
    deadline_20 = (today + _dt.timedelta(days=20)).isoformat()
    r = client.post("/api/projects", headers=h, json={
        "title": "Projeto Verde Longe", "client_id": cid, "status": "ORCAMENTO", "deadline": deadline_20
    })
    assert r.status_code == 201, r.get_data(as_text=True)
    assert r.get_json()["deadline_status"] == "VERDE"

    # CENARIO VERDE: deadline null
    r = client.post("/api/projects", headers=h, json={
        "title": "Projeto Sem Prazo", "client_id": cid, "status": "ORCAMENTO"
    })
    assert r.status_code == 201, r.get_data(as_text=True)
    j = r.get_json()
    assert j["deadline"] is None
    assert j["deadline_status"] == "VERDE"

    # CONCLUSAO E ESTADO EXPLICITO, nao a chave da coluna do funil. Neste
    # cliente a chave "CONCLUIDO" e a coluna "Medicao In Loco" (posicao 1), e a
    # ultima coluna e "Entrega e pos-venda". Criar com status CONCLUIDO NAO
    # pode marcar o projeto como finalizado.
    r = client.post("/api/projects", headers=h, json={
        "title": "Projeto Chave Enganosa", "client_id": cid, "status": "CONCLUIDO",
        "deadline": deadline_yesterday,
    })
    assert r.status_code == 201, r.get_data(as_text=True)
    j = r.get_json()
    assert j["is_concluded"] is False, "status com a chave CONCLUIDO nao conclui o projeto"
    assert j["deadline_status"] != "CONCLUIDO", j["deadline_status"]

    # Concluir pelo botao (endpoint explicito) -> deadline_status CONCLUIDO
    r = client.post(f"/api/projects/{pid}/conclude", headers=h)
    assert r.status_code == 200, r.get_data(as_text=True)
    upd = r.get_json()
    assert upd["is_concluded"] is True
    assert upd["concluded_at"], "concluded_at tem de ser gravado"
    assert upd["actual_end_date"] == today.isoformat(), "estava None, ganha a data de hoje"
    assert upd["deadline_status"] == "CONCLUIDO"
    # GET reflete o mesmo estado
    assert client.get(f"/api/projects/{pid}", headers=h).get_json()["is_concluded"] is True


def test_report_production(client):
    h = _login(client)
    import datetime as _dt

    today = _dt.date.today().isoformat()

    # 1 Client + 2 Projects (PRODUCAO e MONTAGEM)
    r = client.post("/api/clients", headers=h, json={"name": "Cliente Producao", "cpf_cnpj": "prodreport01"})
    assert r.status_code == 201, r.get_data(as_text=True)
    cid = r.get_json()["id"]

    r = client.post("/api/projects", headers=h, json={"title": "Projeto A Producao", "client_id": cid, "status": "PRODUCAO"})
    assert r.status_code == 201, r.get_data(as_text=True)
    pid_a = r.get_json()["id"]

    r = client.post("/api/projects", headers=h, json={"title": "Projeto B Montagem", "client_id": cid, "status": "MONTAGEM"})
    assert r.status_code == 201, r.get_data(as_text=True)
    pid_b = r.get_json()["id"]

    # Para cada projeto cria 2 environments (Cozinha 32m2 value 15000, Quarto 21m2 value 9000)
    env_payloads = [
        {"name": "Cozinha", "env_type": "COZINHA", "area_m2": 32, "value": 15000},
        {"name": "Quarto", "env_type": "QUARTO", "area_m2": 21, "value": 9000},
    ]
    created_envs = []
    for pid in (pid_a, pid_b):
        for payload in env_payloads:
            r = client.post(f"/api/projects/{pid}/environments", headers=h, json=payload)
            assert r.status_code == 201, r.get_data(as_text=True)
            created_envs.append(r.get_json())

    # Cria Worker Carlos e Machine Serra
    r = client.post("/api/workers", headers=h, json={"name": "Carlos"})
    assert r.status_code == 201, r.get_data(as_text=True)
    wid = r.get_json()["id"]

    r = client.post("/api/machines", headers=h, json={"name": "Serra"})
    assert r.status_code == 201, r.get_data(as_text=True)
    mid = r.get_json()["id"]

    # Cria TimeEntry: 8h PRODUTIVA e 2h IMPRODUTIVA em cada projeto (total 16h prod + 4h improd)
    expected_horas_prod = 0
    expected_horas_improd = 0
    for pid in (pid_a, pid_b):
        r = client.post(f"/api/projects/{pid}/time", headers=h, json={"hours": 8, "hours_type": "PRODUTIVA", "work_date": today, "worker_id": wid, "machine_id": mid})
        assert r.status_code == 201, r.get_data(as_text=True)
        expected_horas_prod += 8
        r = client.post(f"/api/projects/{pid}/time", headers=h, json={"hours": 2, "hours_type": "IMPRODUTIVA", "work_date": today, "worker_id": wid})
        assert r.status_code == 201, r.get_data(as_text=True)
        expected_horas_improd += 2
    expected_total_horas = expected_horas_prod + expected_horas_improd

    # Cria ProductionIssue: RETRABALHO cost 120 hours_spent 2, DESPERDICIO material MDF quantity 1, PERDA cost 300
    r = client.post(f"/api/projects/{pid_a}/issues", headers=h, json={"kind": "RETRABALHO", "cost": 120, "hours_spent": 2, "reason": "Teste retrabalho", "issue_date": today, "worker_id": wid})
    assert r.status_code == 201, r.get_data(as_text=True)
    r = client.post(f"/api/projects/{pid_a}/issues", headers=h, json={"kind": "DESPERDICIO", "material": "MDF", "quantity": 1, "reason": "Corte errado", "issue_date": today})
    assert r.status_code == 201, r.get_data(as_text=True)
    r = client.post(f"/api/projects/{pid_b}/issues", headers=h, json={"kind": "PERDA", "cost": 300, "reason": "Perda teste", "issue_date": today})
    assert r.status_code == 201, r.get_data(as_text=True)

    expected_total_m2 = sum(float(e.get("area_m2") or 0) for e in created_envs)
    expected_total_ambientes = len(created_envs)
    expected_retrabalho = 1
    expected_desperdicio = 1
    expected_perda = 1
    expected_custo_retrabalho = 120
    expected_custo_perdas = 300

    # Chama GET /api/reports/production e GET /api/reports/production/export?format=json
    r = client.get("/api/reports/production", headers=h)
    assert r.status_code == 200, r.get_data(as_text=True)
    body = r.get_json()
    assert body is not None, "body json vazio"
    title = body.get("title", "")
    assert "Producao" in title or "Produção" in title or "Industrial" in title, f"title unexpected: {title}"
    summary = body.get("summary", [])
    assert isinstance(summary, list) and len(summary) > 0, f"summary vazio: {summary}"
    columns = body.get("columns", [])
    assert isinstance(columns, list) and len(columns) > 0
    rows = body.get("rows", [])
    assert isinstance(rows, list) and len(rows) > 0, f"rows vazio: {rows}"

    # helpers para buscar summary
    def find_summary(substr):
        for s in summary:
            if substr.lower() in s.get("label", "").lower():
                return s
        return None

    def parse_val_to_float(v):
        if v is None:
            return None
        s = str(v)
        # remove R$, h, m2, etc
        s = s.replace("R$", "").replace("h", "").replace("m²", "").replace("m2", "").strip()
        # trata formato brasileiro 1.234,56 -> 1234.56
        # se tem ',' e '.' -> remove '.' milhar, troca ',' por '.'
        s = s.strip()
        # remove espacos
        s = s.replace(" ", "")
        if "," in s and "." in s:
            s = s.replace(".", "").replace(",", ".")
        elif "," in s:
            s = s.replace(",", ".")
        try:
            return float(s)
        except Exception:
            # extrai numero com regex
            import re
            m = re.search(r"[-+]?\d*\.?\d+", s)
            if m:
                try:
                    return float(m.group(0))
                except Exception:
                    return None
            return None

    # Total m2 e Horas Produtivas SAIRAM do resumo (o cliente nao mensura por eles)
    assert find_summary("Total m2") is None and find_summary("m²") is None, f"summary ainda tem m2: {summary}"
    assert find_summary("Horas Produtivas") is None, f"summary ainda tem Horas Produtivas: {summary}"

    total_amb = find_summary("Total Ambientes")
    assert total_amb is not None, f"summary sem Total Ambientes: {summary}"
    assert total_amb.get("value") == str(expected_total_ambientes) or parse_val_to_float(total_amb.get("value")) == expected_total_ambientes

    # Horas SAIRAM do resumo (pedido do dono) — nem improdutivas nem total.
    assert find_summary("Horas Improdutivas") is None, f"summary ainda tem Horas Improdutivas: {summary}"
    assert find_summary("Total Horas") is None, f"summary ainda tem Total Horas: {summary}"

    ret_item = find_summary("Retrabalho")
    assert ret_item is not None, f"summary sem Retrabalho: {summary}"
    assert parse_val_to_float(ret_item.get("value")) == expected_retrabalho or ret_item.get("value") == str(expected_retrabalho)

    desp_item = find_summary("Desperdicio") or find_summary("Desperdício")
    assert desp_item is not None, f"summary sem Desperdicio: {summary}"
    assert parse_val_to_float(desp_item.get("value")) == expected_desperdicio or desp_item.get("value") == str(expected_desperdicio)

    perda_item = find_summary("Perda")
    assert perda_item is not None, f"summary sem Perdas: {summary}"
    # pega o que contem Perdas (evita confundir com Custo Perdas)
    # filtra labels que nao contenham Custo
    perdas_count_item = None
    for s in summary:
        lbl = s.get("label", "")
        if "perda" in lbl.lower() and "custo" not in lbl.lower():
            perdas_count_item = s
            break
    assert perdas_count_item is not None
    assert parse_val_to_float(perdas_count_item.get("value")) == expected_perda or perdas_count_item.get("value") == str(expected_perda)

    custo_ret_item = find_summary("Custo Retrabalho")
    assert custo_ret_item is not None, f"summary sem Custo Retrabalho: {summary}"
    assert "120" in str(custo_ret_item.get("value")), f"Custo Retrabalho {custo_ret_item.get('value')} nao contem 120"

    custo_perdas_item = find_summary("Custo Perdas")
    assert custo_perdas_item is not None, f"summary sem Custo Perdas: {summary}"
    assert "300" in str(custo_perdas_item.get("value")), f"Custo Perdas {custo_perdas_item.get('value')} nao contem 300"

    # columns contem chaves relevantes
    keys = [c.get("key") for c in columns]
    assert any(k in keys for k in ["metric", "value", "detail", "project", "title", "total"]), f"columns keys inesperadas: {keys}"

    # rows nao vazias e contem pelo menos um projeto ou metrica relacionada
    rows_str = str(rows)
    assert "Projeto A" in rows_str or "Projeto B" in rows_str or "Total" in rows_str or "Horas" in rows_str or "Retrabalho" in rows_str, f"rows nao contem projeto/metrica: {rows}"

    # export json
    r2 = client.get("/api/reports/production/export?format=json", headers=h)
    assert r2.status_code == 200, r2.get_data(as_text=True)
    body2 = r2.get_json()
    assert body2 is not None
    # compara title ou summary similar
    assert body2.get("title") == body.get("title") or "Producao" in body2.get("title", "") or "Industrial" in body2.get("title", "")
    assert len(body2.get("summary", [])) > 0
    assert len(body2.get("rows", [])) > 0

    # tambem verifica /api/reports/production?format=json nao quebre
    r3 = client.get("/api/reports/production?format=json", headers=h)
    assert r3.status_code == 200, r3.get_data(as_text=True)


def test_bank_account_model(client):
    _login(client)
    import datetime

    from app.models.models import BankAccount

    with client.application.app_context():
        acc = BankAccount(
            name="Principal",
            bank="Bradesco",
            agency="1234",
            account_number="56789-0",
            account_type="CORRENTE",
            opening_balance=5000,
            opening_date=datetime.date.today(),
            active=True,
            low_balance_threshold=1000,
        )
        db.session.add(acc)
        db.session.commit()
        d = acc.to_dict()
        assert d["name"] == "Principal"
        assert d["bank"] == "Bradesco"
        assert d["agency"] == "1234"
        assert d["account_number"] == "56789-0"
        assert d["account_type"] == "CORRENTE"
        assert d["opening_balance"] == 5000
        assert d["active"] is True
        assert d["low_balance_threshold"] == 1000
        assert d["current_balance"] == 5000
        assert "current_balance" in d
        # verifica que current_balance é computed property
        assert isinstance(type(acc).current_balance, property)


def test_bank_account_balance_com_lancamentos(client):
    _login(client)
    import datetime

    from app.models.models import BankAccount, FinancialRecord

    with client.application.app_context():
        acc = BankAccount(
            name="Conta Teste",
            bank="Banco X",
            opening_balance=1000,
            opening_date=datetime.date.today(),
            active=True,
        )
        db.session.add(acc)
        db.session.commit()
        acc_id = acc.id
        fr1 = FinancialRecord(
            description="Entrada paga",
            type="ENTRADA",
            category="Vendas",
            amount=500,
            date=datetime.date.today(),
            status="PAGO",
            bank_account_id=acc_id,
        )
        fr2 = FinancialRecord(
            description="Saida paga",
            type="SAIDA",
            category="Despesa",
            amount=300,
            date=datetime.date.today(),
            status="PAGO",
            bank_account_id=acc_id,
        )
        fr3 = FinancialRecord(
            description="Pendente nao conta",
            type="ENTRADA",
            category="Vendas",
            amount=200,
            date=datetime.date.today(),
            status="PENDENTE",
            bank_account_id=acc_id,
        )
        db.session.add_all([fr1, fr2, fr3])
        db.session.commit()
        # refresh
        acc_ref = db.session.get(BankAccount, acc_id)
        db.session.refresh(acc_ref)
        assert acc_ref.current_balance == 1200
        assert acc_ref.to_dict()["current_balance"] == 1200
        # financial_record to_dict inclui bank_account_id e bank_account_name
        d1 = fr1.to_dict()
        assert d1["bank_account_id"] == acc_id
        assert d1["bank_account_name"] == "Conta Teste"
        # pendente ainda tem bank_account_id mas nao afeta saldo
        assert fr3.to_dict()["bank_account_id"] == acc_id
        assert fr3.to_dict()["bank_account_name"] == "Conta Teste"


def test_financial_record_bank_account_fk(client):
    _login(client)
    import datetime

    from app.models.models import BankAccount, FinancialRecord

    with client.application.app_context():
        # FinancialRecord sem conta bancaria deve ter None nos novos campos
        fr = FinancialRecord(
            description="Sem conta",
            type="ENTRADA",
            amount=100,
            date=datetime.date.today(),
            status="PENDENTE",
        )
        db.session.add(fr)
        db.session.commit()
        d = fr.to_dict()
        assert "bank_account_id" in d
        assert "bank_account_name" in d
        assert d["bank_account_id"] is None
        assert d["bank_account_name"] is None
        # BankAccount com opening_balance None deve retornar 0 no property sem quebrar
        acc = BankAccount(name="Conta Vazia", bank="Banco Y", opening_balance=None)
        db.session.add(acc)
        db.session.commit()
        # deve lidar com None sem excecao
        assert acc.current_balance == 0 or acc.current_balance == 0.0
        # verifica FK SET NULL existe no modelo
        col = FinancialRecord.__table__.c.bank_account_id
        fks = list(col.foreign_keys)
        assert len(fks) == 1
        assert fks[0].ondelete == "SET NULL"
        assert col.nullable is True


def test_bank_accounts_api_crud(client):
    h = _login(client)
    import datetime

    today = datetime.date.today().isoformat()

    # criar conta valida
    r = client.post(
        "/api/bank-accounts",
        headers=h,
        json={
            "name": "Principal",
            "bank": "Bradesco",
            "agency": "1234",
            "account_number": "56789-0",
            "account_type": "CORRENTE",
            "opening_balance": 5000,
            "opening_date": today,
            "low_balance_threshold": 1000,
            "active": True,
        },
    )
    assert r.status_code == 201, r.get_data(as_text=True)
    body = r.get_json()
    assert "id" in body
    assert body["name"] == "Principal"
    # current_balance deve ser 5000 (opening sem lancamentos)
    assert body["current_balance"] == 5000 or body["current_balance"] == 5000.0
    bid = body["id"]

    # listar
    r = client.get("/api/bank-accounts", headers=h)
    assert r.status_code == 200, r.get_data(as_text=True)
    lst = r.get_json()
    assert isinstance(lst, list)
    assert len(lst) == 1
    assert any(x["id"] == bid for x in lst)

    # get por id
    r = client.get(f"/api/bank-accounts/{bid}", headers=h)
    assert r.status_code == 200, r.get_data(as_text=True)
    j = r.get_json()
    assert j["id"] == bid
    assert j["name"] == "Principal"
    assert "current_balance" in j
    assert j["current_balance"] == 5000 or j["current_balance"] == 5000.0

    # put altera name e opening_balance
    r = client.put(f"/api/bank-accounts/{bid}", headers=h, json={"name": "Secundaria", "opening_balance": 6000})
    assert r.status_code == 200, r.get_data(as_text=True)
    j = r.get_json()
    assert j["name"] == "Secundaria"
    # apos alterar opening para 6000, current deve refletir 6000
    assert j["current_balance"] == 6000 or j["current_balance"] == 6000.0
    assert j["opening_balance"] == 6000 or j["opening_balance"] == 6000.0

    # validacoes: sem name
    r = client.post("/api/bank-accounts", headers=h, json={"bank": "Bradesco"})
    assert r.status_code == 400, r.get_data(as_text=True)
    # account_type invalido
    r = client.post("/api/bank-accounts", headers=h, json={"name": "Invalida", "account_type": "INVALIDO"})
    assert r.status_code == 400, r.get_data(as_text=True)
    assert "account_type" in r.get_data(as_text=True).lower()

    # delete sem vinculados -> 200 ok True
    r = client.delete(f"/api/bank-accounts/{bid}", headers=h)
    assert r.status_code == 200, r.get_data(as_text=True)
    assert r.get_json().get("ok") is True
    # confirma 404 apos delete
    assert client.get(f"/api/bank-accounts/{bid}", headers=h).status_code == 404

    # delete bloqueado quando ha lancamentos vinculados
    r = client.post("/api/bank-accounts", headers=h, json={"name": "Conta Bloqueio", "opening_balance": 100})
    assert r.status_code == 201, r.get_data(as_text=True)
    bid2 = r.get_json()["id"]
    r = client.post(
        "/api/financial",
        headers=h,
        json={"description": "Venda vinculada", "type": "ENTRADA", "amount": 100, "date": today, "status": "PAGO", "bank_account_id": bid2},
    )
    assert r.status_code == 201, r.get_data(as_text=True)
    r = client.delete(f"/api/bank-accounts/{bid2}", headers=h)
    assert r.status_code == 400, r.get_data(as_text=True)
    txt = r.get_data(as_text=True).lower()
    assert "conta em uso" in txt or "em uso" in txt


def test_bank_balance_e_overview(client):
    h = _login(client)
    import datetime

    today = datetime.date.today().isoformat()

    # cria conta opening 1000
    r = client.post("/api/bank-accounts", headers=h, json={"name": "Conta Teste Balance", "opening_balance": 1000})
    assert r.status_code == 201, r.get_data(as_text=True)
    bid = r.get_json()["id"]

    # 2 lancamentos pagos + 1 pendente ENTRADA 200
    r = client.post(
        "/api/financial",
        headers=h,
        json={"description": "Entrada paga", "type": "ENTRADA", "amount": 500, "date": today, "status": "PAGO", "bank_account_id": bid},
    )
    assert r.status_code == 201, r.get_data(as_text=True)
    r = client.post(
        "/api/financial",
        headers=h,
        json={"description": "Saida paga", "type": "SAIDA", "amount": 300, "date": today, "status": "PAGO", "bank_account_id": bid},
    )
    assert r.status_code == 201, r.get_data(as_text=True)
    r = client.post(
        "/api/financial",
        headers=h,
        json={"description": "Entrada pendente", "type": "ENTRADA", "amount": 200, "date": today, "status": "PENDENTE", "bank_account_id": bid},
    )
    assert r.status_code == 201, r.get_data(as_text=True)

    # GET balance -> current 1200, opening 1000, entradas 500, saidas 300, projected 1400
    r = client.get(f"/api/bank-accounts/{bid}/balance", headers=h)
    assert r.status_code == 200, r.get_data(as_text=True)
    b = r.get_json()
    assert b["current_balance"] == 1200 or b["current_balance"] == 1200.0
    assert b["opening_balance"] == 1000 or b["opening_balance"] == 1000.0
    # entradas/saidas pagas
    assert b.get("entradas_pagas") == 500 or b.get("entradas_pagas") == 500.0
    assert b.get("saidas_pagas") == 300 or b.get("saidas_pagas") == 300.0
    # projected = current + entradas pendentes - saidas pendentes = 1200+200 =1400
    assert b["projected_balance"] == 1400 or b["projected_balance"] == 1400.0
    # pendentes detalhados
    assert b.get("entradas_pendentes") == 200 or b.get("entradas_pendentes") == 200.0
    assert b.get("saidas_pendentes") == 0 or b.get("saidas_pendentes") == 0.0

    # overview consolidado
    r = client.get("/api/bank-accounts/overview", headers=h)
    assert r.status_code == 200, r.get_data(as_text=True)
    ov = r.get_json()
    assert "total_balance" in ov
    assert ov["total_balance"] == 1200 or ov["total_balance"] == 1200.0
    assert "accounts" in ov
    assert any(a["id"] == bid for a in ov["accounts"])
    # total_projected deve ser 1400 (se houver campo)
    if "total_projected" in ov:
        assert ov["total_projected"] == 1400 or ov["total_projected"] == 1400.0

    # projecao com SAIDA pendente: cria SAIDA 150 pendente -> projected 1250
    r = client.post(
        "/api/financial",
        headers=h,
        json={"description": "Saida pendente", "type": "SAIDA", "amount": 150, "date": today, "status": "PENDENTE", "bank_account_id": bid},
    )
    assert r.status_code == 201, r.get_data(as_text=True)
    r = client.get(f"/api/bank-accounts/{bid}/balance", headers=h)
    assert r.status_code == 200, r.get_data(as_text=True)
    b2 = r.get_json()
    # current continua 1200, projected agora 1200+200-150 =1250
    assert b2["current_balance"] == 1200 or b2["current_balance"] == 1200.0
    assert b2["projected_balance"] == 1250 or b2["projected_balance"] == 1250.0
    assert b2.get("saidas_pendentes") == 150 or b2.get("saidas_pendentes") == 150.0

    # overview atualizado
    r = client.get("/api/bank-accounts/overview", headers=h)
    assert r.status_code == 200
    ov2 = r.get_json()
    if "total_projected" in ov2:
        assert ov2["total_projected"] == 1250 or ov2["total_projected"] == 1250.0


def test_financial_com_bank_account_id(client):
    h = _login(client)
    import datetime

    today = datetime.date.today().isoformat()

    # cria duas contas
    r = client.post("/api/bank-accounts", headers=h, json={"name": "Conta 01", "opening_balance": 1000})
    assert r.status_code == 201, r.get_data(as_text=True)
    acc1 = r.get_json()
    id1 = acc1["id"]
    r = client.post("/api/bank-accounts", headers=h, json={"name": "Conta 02", "opening_balance": 2000})
    assert r.status_code == 201, r.get_data(as_text=True)
    acc2 = r.get_json()
    id2 = acc2["id"]

    # POST com bank_account_id valido
    r = client.post(
        "/api/financial",
        headers=h,
        json={"description": "Venda com conta", "type": "ENTRADA", "amount": 300, "date": today, "status": "PAGO", "bank_account_id": id1},
    )
    assert r.status_code == 201, r.get_data(as_text=True)
    j = r.get_json()
    fid = j["id"]
    assert j["bank_account_id"] == id1
    assert j["bank_account_name"] == "Conta 01"

    # verifica via listagem
    r = client.get("/api/financial", headers=h)
    assert r.status_code == 200
    lst = r.get_json()
    found = next((x for x in lst if x["id"] == fid), None)
    assert found is not None
    assert found["bank_account_id"] == id1
    assert found["bank_account_name"] == "Conta 01"

    # POST com bank_account_id inexistente -> 404 ou 400 contendo bank_account
    r = client.post(
        "/api/financial",
        headers=h,
        json={"description": "Invalida", "type": "ENTRADA", "amount": 100, "date": today, "bank_account_id": "id-inexistente-xyz"},
    )
    assert r.status_code in (400, 404), r.get_data(as_text=True)
    assert "bank_account" in r.get_data(as_text=True).lower()

    # PUT alterar para outra conta valida
    r = client.put(f"/api/financial/{fid}", headers=h, json={"bank_account_id": id2})
    assert r.status_code == 200, r.get_data(as_text=True)
    pj = r.get_json()
    assert pj["bank_account_id"] == id2
    # to_dict deve refletir nome da nova conta
    assert pj.get("bank_account_name") == "Conta 02" or pj.get("bank_account_name") is not None

    # compat: POST sem bank_account_id continua funcionando e retorna null
    r = client.post(
        "/api/financial",
        headers=h,
        json={"description": "Sem conta", "type": "SAIDA", "amount": 50, "date": today, "status": "PENDENTE"},
    )
    assert r.status_code == 201, r.get_data(as_text=True)
    j2 = r.get_json()
    assert j2["bank_account_id"] is None
    # bank_account_name deve ser None
    assert j2.get("bank_account_name") is None

    # PUT para remover vinculo (None ou "")
    r = client.put(f"/api/financial/{fid}", headers=h, json={"bank_account_id": None})
    assert r.status_code == 200, r.get_data(as_text=True)
    assert r.get_json()["bank_account_id"] is None


def test_saldo_baixo_alerta(client):
    h = _login(client)
    import datetime

    today = datetime.date.today().isoformat()

    # cria conta com saldo baixo
    r = client.post("/api/bank-accounts", headers=h, json={"name": "Conta Alerta", "opening_balance": 500, "low_balance_threshold": 1000})
    assert r.status_code == 201, r.get_data(as_text=True)
    bid = r.get_json()["id"]

    # cria SAIDA PAGO 400 -> saldo 100 < 1000
    r = client.post(
        "/api/financial",
        headers=h,
        json={"description": "Saida grande", "type": "SAIDA", "amount": 400, "date": today, "status": "PAGO", "bank_account_id": bid},
    )
    assert r.status_code == 201, r.get_data(as_text=True)

    # confirma saldo via balance
    r = client.get(f"/api/bank-accounts/{bid}/balance", headers=h)
    assert r.status_code == 200, r.get_data(as_text=True)
    assert r.get_json()["current_balance"] == 100 or r.get_json()["current_balance"] == 100.0

    # gera alertas - tenta ambas as rotas por compat
    r = client.post("/api/calendar/notifications/generate-alerts", headers=h)
    if r.status_code == 404:
        r = client.post("/api/calendar/generate-alerts", headers=h)
    assert r.status_code == 200, r.get_data(as_text=True)

    # verifica notificacao SALDO_BAIXO
    r = client.get("/api/calendar/notifications", headers=h)
    assert r.status_code == 200, r.get_data(as_text=True)
    notifs = r.get_json()
    assert any(n["type"] == "SALDO_BAIXO" for n in notifs), f"notifs: {notifs}"
    assert any("Conta Alerta" in n["title"] for n in notifs if n["type"] == "SALDO_BAIXO")

    # segunda geracao nao deve duplicar por conta
    before = len([n for n in notifs if n["type"] == "SALDO_BAIXO"])
    r = client.post("/api/calendar/notifications/generate-alerts", headers=h)
    if r.status_code == 404:
        r = client.post("/api/calendar/generate-alerts", headers=h)
    assert r.status_code == 200
    r = client.get("/api/calendar/notifications", headers=h)
    after = len([n for n in r.get_json() if n["type"] == "SALDO_BAIXO"])
    assert after == before


def test_venda_fechada_cria_cards_por_ambiente(client):
    """Apartamento inteiro: gerar venda cria 1 card de producao por ambiente
    (Sala, Cozinha, Banheiro, Quarto) — e arrastar para a etapa de ganho
    sozinho nao cria nada."""
    h = _login(client)
    cid = client.post("/api/clients", headers=h,
                      json={"name": "Cliente Apt", "cpf_cnpj": "apt1",
                            "funnel_status": "FECHAMENTO"}).get_json()["id"]
    up = client.put(f"/api/clients/{cid}", headers=h, json={"funnel_status": "FECHAMENTO"})
    assert up.status_code == 200 and up.get_json()["closed_at"] is None
    projs0 = client.get("/api/projects", headers=h).get_json()
    assert not [p for p in projs0 if p.get("client_id") == cid]

    sale = client.post("/api/sales", headers=h, json={
        "client_id": cid, "total_value": 20000, "down_payment": 20000,
        "installments": 0, "installment_value": 0, "installments_due": [],
        "sale_date": date.today().isoformat(),
        "environments": ["Cozinha", "Sala", "Banheiro", "Quarto"],
    })
    assert sale.status_code == 201, sale.get_data(as_text=True)
    sid = sale.get_json()["id"]
    cards = [x for x in client.get("/api/projects", headers=h).get_json()
             if x.get("sale_id") == sid]
    assert len(cards) == 4
    assert sorted(x["title"] for x in cards) == [
        "Banheiro – Cliente Apt", "Cozinha – Cliente Apt",
        "Quarto – Cliente Apt", "Sala – Cliente Apt",
    ]

def test_alertas_financeiros(client):
    h = _login(client)
    import datetime as _dt
    today = _dt.date.today()
    yesterday = (today - _dt.timedelta(days=1)).isoformat()
    in3 = (today + _dt.timedelta(days=3)).isoformat()
    today_iso = today.isoformat()
    # cria 2 lancamentos: vencida e proxima
    r = client.post(
        "/api/financial",
        headers=h,
        json={"description": "Conta Vencida SAIDA Teste", "type": "SAIDA", "amount": 100, "date": today_iso, "due_date": yesterday, "status": "PENDENTE", "category": "Teste"},
    )
    assert r.status_code == 201, r.get_data(as_text=True)
    r = client.post(
        "/api/financial",
        headers=h,
        json={"description": "Conta Proxima ENTRADA Teste", "type": "ENTRADA", "amount": 200, "date": today_iso, "due_date": in3, "status": "PENDENTE", "category": "Teste"},
    )
    assert r.status_code == 201, r.get_data(as_text=True)
    # outro vencido tipo RECEBER (ENTRADA)
    r = client.post(
        "/api/financial",
        headers=h,
        json={"description": "Conta Vencida ENTRADA Teste", "type": "ENTRADA", "amount": 150, "date": today_iso, "due_date": yesterday, "status": "PENDENTE", "category": "Teste"},
    )
    assert r.status_code == 201, r.get_data(as_text=True)
    # chama generate-alerts
    r = client.post("/api/calendar/notifications/generate-alerts", headers=h)
    if r.status_code == 404:
        r = client.post("/api/calendar/generate-alerts", headers=h)
    assert r.status_code == 200, r.get_data(as_text=True)
    r = client.get("/api/calendar/notifications", headers=h)
    assert r.status_code == 200, r.get_data(as_text=True)
    notifs = r.get_json()
    # verifica existe CONTA_VENCIDA e CONTA_PROXIMA
    assert any(n["type"] == "CONTA_VENCIDA" for n in notifs), f"CONTA_VENCIDA nao encontrada: {notifs}"
    assert any(n["type"] == "CONTA_PROXIMA" for n in notifs), f"CONTA_PROXIMA nao encontrada: {notifs}"
    venc_count = len([n for n in notifs if n["type"] == "CONTA_VENCIDA"])
    prox_count = len([n for n in notifs if n["type"] == "CONTA_PROXIMA"])
    # dedupe: chamar generate-alerts novamente e verificar nao duplica
    r = client.post("/api/calendar/notifications/generate-alerts", headers=h)
    if r.status_code == 404:
        r = client.post("/api/calendar/generate-alerts", headers=h)
    assert r.status_code == 200
    r = client.get("/api/calendar/notifications", headers=h)
    notifs2 = r.get_json()
    venc_count2 = len([n for n in notifs2 if n["type"] == "CONTA_VENCIDA"])
    prox_count2 = len([n for n in notifs2 if n["type"] == "CONTA_PROXIMA"])
    assert venc_count2 == venc_count, f"dedupe CONTA_VENCIDA falhou: {venc_count} -> {venc_count2}"
    assert prox_count2 == prox_count, f"dedupe CONTA_PROXIMA falhou: {prox_count} -> {prox_count2}"


def test_project_attachments_api(client, tmp_path):
    with client.application.app_context():
        client.application.config["UPLOAD_DIR"] = str(tmp_path)
    h = _login(client)
    # cria cliente e projeto
    cid = client.post("/api/clients", headers=h, json={"name": "Cliente Proj Anexo", "cpf_cnpj": "p-attach-1"}).get_json()["id"]
    r = client.post(
        "/api/projects",
        headers=h,
        json={"title": "Projeto Anexo Teste", "client_id": cid, "description": "d", "status": "ORCAMENTO", "value": 5000, "deadline": "2030-06-01", "steps": []},
    )
    assert r.status_code == 201, r.get_data(as_text=True)
    pid = r.get_json()["id"]
    import io
    # sem file -> 400
    r = client.post(f"/api/projects/{pid}/attachments", headers=h, data={}, content_type="multipart/form-data")
    assert r.status_code == 400
    # projeto inexistente -> 404 (GET e POST)
    assert client.get("/api/projects/id-inexistente/attachments", headers=h).status_code == 404
    r = client.post("/api/projects/id-inexistente/attachments", headers=h, data={"file": (io.BytesIO(b"x"), "a.txt")}, content_type="multipart/form-data")
    assert r.status_code == 404
    # upload ok
    data = {"file": (io.BytesIO(b"%PDF-1.4 fake pdf projeto"), "teste.pdf")}
    r = client.post(f"/api/projects/{pid}/attachments", headers=h, data=data, content_type="multipart/form-data")
    assert r.status_code == 201, r.get_data(as_text=True)
    att = r.get_json()
    assert att["filename"] == "teste.pdf"
    assert att["project_id"] == pid
    assert att["client_id"] == cid
    aid = att["id"]
    # lista por projeto
    lst = client.get(f"/api/projects/{pid}/attachments", headers=h).get_json()
    assert len(lst) == 1
    assert lst[0]["id"] == aid
    # download via endpoint generico
    d = client.get(f"/api/attachments/{aid}/download", headers=h)
    assert d.status_code == 200
    assert b"%PDF-1.4" in d.data
    # delete
    assert client.delete(f"/api/attachments/{aid}", headers=h).status_code == 200
    assert client.get(f"/api/attachments/{aid}/download", headers=h).status_code == 404
    # lista vazia apos delete
    lst2 = client.get(f"/api/projects/{pid}/attachments", headers=h).get_json()
    assert len(lst2) == 0
    # sem token -> 401
    assert client.get(f"/api/projects/{pid}/attachments").status_code == 401

def test_checklists_api(client):
    h = _login(client)
    # 404 projeto inexistente
    assert client.get("/api/projects/id-inexistente/checklists", headers=h).status_code == 404
    assert client.post("/api/projects/id-inexistente/checklists", headers=h, json={"step_id": "1", "label": "x"}).status_code == 404

    cid = client.post("/api/clients", headers=h, json={"name": "Cli Checklist", "cpf_cnpj": "chk-1"}).get_json()["id"]
    steps = [{"id": "1", "label": "Etapa 1", "completed": False}, {"id": "2", "label": "Etapa 2", "completed": False}]
    r = client.post(
        "/api/projects",
        headers=h,
        json={"title": "Proj Checklist", "client_id": cid, "status": "ORCAMENTO", "value": 1000, "deadline": "2030-01-01", "steps": steps},
    )
    assert r.status_code == 201, r.get_data(as_text=True)
    pid = r.get_json()["id"]

    # sem token -> 401
    assert client.get(f"/api/projects/{pid}/checklists").status_code == 401

    # GET inicial vazio
    r = client.get(f"/api/projects/{pid}/checklists", headers=h)
    assert r.status_code == 200 and len(r.get_json()) == 0

    # validacoes POST
    assert client.post(f"/api/projects/{pid}/checklists", headers=h, json={"step_id": "", "label": "x"}).status_code == 400
    assert client.post(f"/api/projects/{pid}/checklists", headers=h, json={"step_id": "1", "label": "   "}).status_code == 400
    assert client.post(f"/api/projects/{pid}/checklists", headers=h, json={"step_id": "99", "label": "Conferir"}).status_code == 400
    assert client.post(f"/api/projects/{pid}/checklists", headers=h, json={"step_id": "1", "label": "Teste", "assigned_user_id": "nao-existe"}).status_code == 404

    # POST ok -> 201
    r = client.post(f"/api/projects/{pid}/checklists", headers=h, json={"step_id": "1", "label": "Conferir medidas", "notes": "usar trena"})
    assert r.status_code == 201, r.get_data(as_text=True)
    body = r.get_json()
    assert body["label"] == "Conferir medidas" and body["step_id"] == "1" and body["completed"] is False
    assert body["notes"] == "usar trena"
    assert body["project_id"] == pid
    iid = body["id"]

    # GET retorna 1
    r = client.get(f"/api/projects/{pid}/checklists", headers=h)
    assert r.status_code == 200
    lst = r.get_json()
    assert len(lst) == 1 and lst[0]["id"] == iid

    # POST segunda etapa com position incrementa
    r2 = client.post(f"/api/projects/{pid}/checklists", headers=h, json={"step_id": "2", "label": "Item 2"})
    assert r2.status_code == 201
    assert r2.get_json()["position"] == 1
    iid2 = r2.get_json()["id"]

    # GET retorna 2 ordenado
    lst2 = client.get(f"/api/projects/{pid}/checklists", headers=h).get_json()
    assert len(lst2) == 2
    assert [c["position"] for c in lst2] == sorted([c["position"] for c in lst2])

    # PUT completed True deve preencher completed_at e assigned_user_name
    r = client.put(f"/api/checklist-items/{iid}", headers=h, json={"completed": True})
    assert r.status_code == 200, r.get_data(as_text=True)
    d = r.get_json()
    assert d["completed"] is True
    assert d["completed_at"] is not None
    assert d["assigned_user_name"] == "Admin"

    # PUT com step_id invalido 400
    assert client.put(f"/api/checklist-items/{iid}", headers=h, json={"step_id": "99"}).status_code == 400
    # PUT label vazio 400
    assert client.put(f"/api/checklist-items/{iid}", headers=h, json={"label": "   "}).status_code == 400

    # PUT notes e label ok
    r = client.put(f"/api/checklist-items/{iid}", headers=h, json={"label": "Conferir medidas OK", "notes": "obs"})
    assert r.status_code == 200 and r.get_json()["label"] == "Conferir medidas OK"

    # PUT completed False limpa completed_at
    r = client.put(f"/api/checklist-items/{iid}", headers=h, json={"completed": False})
    assert r.status_code == 200
    assert r.get_json()["completed"] is False
    assert r.get_json()["completed_at"] is None

    # PUT assigned_user_id invalido 404
    assert client.put(f"/api/checklist-items/{iid}", headers=h, json={"assigned_user_id": "nope"}).status_code == 404
    # DELETE 404 invalido
    assert client.delete("/api/checklist-items/nao-existe", headers=h).status_code == 404

    # DELETE retorna 200
    assert client.delete(f"/api/checklist-items/{iid}", headers=h).status_code == 200
    assert client.delete(f"/api/checklist-items/{iid2}", headers=h).status_code == 200

    # GET apos delete 0
    lst3 = client.get(f"/api/projects/{pid}/checklists", headers=h).get_json()
    assert len(lst3) == 0

    # sem token DELETE 401 e PUT 401
    r = client.post(f"/api/projects/{pid}/checklists", headers=h, json={"step_id": "1", "label": "Temp"}).get_json()
    tmp_id = r["id"]
    assert client.delete(f"/api/checklist-items/{tmp_id}").status_code == 401
    assert client.delete(f"/api/checklist-items/{tmp_id}", headers=h).status_code == 200

    r = client.post(f"/api/projects/{pid}/checklists", headers=h, json={"step_id": "1", "label": "Temp2"}).get_json()
    tmp2 = r["id"]
    assert client.put(f"/api/checklist-items/{tmp2}", json={"label": "x"}).status_code == 401
    assert client.delete(f"/api/checklist-items/{tmp2}", headers=h).status_code == 200

    # cascade project delete limpa checklists
    r = client.post(f"/api/projects/{pid}/checklists", headers=h, json={"step_id": "1", "label": "Cascade"}).get_json()
    cascade_id = r["id"]
    assert client.delete(f"/api/projects/{pid}", headers=h).status_code == 200
    assert client.delete(f"/api/checklist-items/{cascade_id}", headers=h).status_code == 404


def test_partners_api(client):
    h = _login(client)
    # name vazio 400
    assert client.post("/api/partners", headers=h, json={"name": "   "}).status_code == 400
    # sem token 401
    assert client.get("/api/partners").status_code == 401
    # create
    r = client.post("/api/partners", headers=h, json={"name": "Escritorio Silva", "office": "Silva Arquitetura", "city": "Seberi"})
    assert r.status_code == 201, r.get_data(as_text=True)
    pid = r.get_json()["id"]
    assert r.get_json()["name"] == "Escritorio Silva"
    assert r.get_json()["office"] == "Silva Arquitetura"
    assert r.get_json()["city"] == "Seberi"
    # get list 1
    lst = client.get("/api/partners", headers=h).get_json()
    assert len(lst) >= 1
    assert any(p["id"] == pid for p in lst)
    # get single
    assert client.get(f"/api/partners/{pid}", headers=h).status_code == 200
    assert client.get("/api/partners/nao-existe", headers=h).status_code == 404
    # update
    r = client.put(f"/api/partners/{pid}", headers=h, json={"office": "Silva Arq Atualizado"})
    assert r.status_code == 200 and r.get_json()["office"] == "Silva Arq Atualizado"
    # update name vazio 400
    assert client.put(f"/api/partners/{pid}", headers=h, json={"name": " "}).status_code == 400
    assert client.put("/api/partners/nao-existe", headers=h, json={"name": "x"}).status_code == 404
    # client com parceiro
    r = client.post("/api/clients", headers=h, json={"name": "Cliente A", "cpf_cnpj": "part-001", "partner_id": pid})
    assert r.status_code == 201, r.get_data(as_text=True)
    cid = r.get_json()["id"]
    assert r.get_json()["partner_id"] == pid
    assert r.get_json()["partner_name"] == "Escritorio Silva"
    # GET clients contem partner_name
    lst2 = client.get("/api/clients", headers=h).get_json()
    row = next(c for c in lst2 if c["id"] == cid)
    assert row["partner_name"] == "Escritorio Silva"
    # update client partner_id invalido 404
    assert client.put(f"/api/clients/{cid}", headers=h, json={"partner_id": "nao-existe"}).status_code == 404
    # create client com partner invalido 404
    assert client.post("/api/clients", headers=h, json={"name": "Cliente B", "cpf_cnpj": "part-002", "partner_id": "nao-existe"}).status_code == 404
    # partner em uso não pode deletar 400
    r = client.delete(f"/api/partners/{pid}", headers=h)
    assert r.status_code == 400, r.get_data(as_text=True)
    assert "em uso" in r.get_data(as_text=True).lower()
    # remover vinculo e deletar
    assert client.put(f"/api/clients/{cid}", headers=h, json={"partner_id": ""}).status_code == 200
    assert client.delete(f"/api/clients/{cid}", headers=h).status_code == 200
    assert client.delete(f"/api/partners/{pid}", headers=h).status_code == 200
    assert client.get(f"/api/partners/{pid}", headers=h).status_code == 404
    # delete nao existe 404
    assert client.delete("/api/partners/nao-existe", headers=h).status_code == 404
    # delete sem token 401
    r = client.post("/api/partners", headers=h, json={"name": "TempPartner"}).get_json()
    tmp = r["id"]
    assert client.delete(f"/api/partners/{tmp}").status_code == 401
    assert client.delete(f"/api/partners/{tmp}", headers=h).status_code == 200


def test_report_partners(client):
    h = _login(client)
    r = client.post("/api/partners", headers=h, json={"name": "Escritorio Report", "office": "Report Arq", "city": "Seberi"})
    assert r.status_code == 201, r.get_data(as_text=True)
    pid = r.get_json()["id"]
    # cria 2 clientes com partner
    c1 = client.post("/api/clients", headers=h, json={"name": "Cli Rep 1", "cpf_cnpj": "rep-001", "partner_id": pid, "estimated_value": 10000}).get_json()
    c2 = client.post("/api/clients", headers=h, json={"name": "Cli Rep 2", "cpf_cnpj": "rep-002", "partner_id": pid, "estimated_value": 5000}).get_json()
    # report partners
    r = client.get("/api/reports/partners", headers=h)
    assert r.status_code == 200, r.get_data(as_text=True)
    body = r.get_json()
    assert "Parceiro" in body["title"]
    assert len(body["rows"]) >= 1
    assert any("Escritorio Report" in str(row.get("partner", "")) for row in body["rows"])
    # verifica summary contem Clientes com Parceiro
    assert any("Clientes com Parceiro" in s["label"] for s in body["summary"])
    # verifica export xlsx
    assert client.get("/api/reports/partners?format=xlsx", headers=h).status_code == 200
    # verifica export pdf
    assert client.get("/api/reports/partners?format=pdf", headers=h).status_code == 200
    # crm tambem deve conter vendas por parceiro
    crm = client.get("/api/reports/crm", headers=h).get_json()
    assert "vendas_por_parceiro" in crm or "parceiros" in crm or "partner_clients_count" in crm
    # cleanup
    client.delete(f"/api/clients/{c1['id']}", headers=h)
    client.delete(f"/api/clients/{c2['id']}", headers=h)
    client.delete(f"/api/partners/{pid}", headers=h)


def test_proposals_crud_pdf_e_total(client):
    """Proposta: total vem dos itens, PDF sai como PDF, cliente inexistente 404."""
    h = _login(client)
    cid = client.post("/api/clients", headers=h,
                      json={"name": "Cliente Proposta QA"}).get_json()["id"]

    r = client.post("/api/proposals", headers=h, json={
        "client_id": cid, "valid_until": date.today().isoformat(),
        "notes": "Proposta de teste",
        "items": [
            {"description": "Armario planejado", "quantity": 1, "unit_price": 3500},
            {"description": "Instalacao", "quantity": 2, "unit_price": 250},
        ],
    })
    assert r.status_code == 201, r.get_data(as_text=True)
    p = r.get_json()
    assert p["number"].startswith("PROP-"), p["number"]
    assert p["status"] == "RASCUNHO"
    # 3500*1 + 250*2 = 4000
    assert p["total_value"] == 4000.0, p["total_value"]
    assert p["items_total"] == 4000.0
    assert len(p["items"]) == 2
    assert p["client_name"] == "Cliente Proposta QA"

    # cliente inexistente -> 404 | sem client_id -> 400
    assert client.post("/api/proposals", headers=h,
                       json={"client_id": "nao-existe"}).status_code == 404
    assert client.post("/api/proposals", headers=h, json={"items": []}).status_code == 400

    # PDF de verdade (magic number), nao um JSON renomeado
    r = client.get(f"/api/proposals/{p['id']}/pdf", headers=h)
    assert r.status_code == 200
    assert r.headers["Content-Type"].startswith("application/pdf")
    assert r.data[:4] == b"%PDF", r.data[:8]

    # editar itens recalcula o total: o valor NUNCA vem do cliente da API
    r = client.put(f"/api/proposals/{p['id']}", headers=h, json={
        "items": [{"description": "So um item", "quantity": 3, "unit_price": 100}],
        "status": "ENVIADA",
    })
    assert r.status_code == 200, r.get_data(as_text=True)
    atual = r.get_json()
    assert atual["total_value"] == 300.0, atual["total_value"]
    assert atual["status"] == "ENVIADA"
    assert len(atual["items"]) == 1

    # status invalido -> 400
    assert client.put(f"/api/proposals/{p['id']}", headers=h,
                      json={"status": "INVENTADO"}).status_code == 400
    # item sem descricao nao entra, e o total zera junto
    r = client.put(f"/api/proposals/{p['id']}", headers=h,
                   json={"items": [{"quantity": 5, "unit_price": 10}]})
    assert r.get_json()["items"] == []
    assert r.get_json()["total_value"] == 0.0

    assert client.get("/api/proposals/nao-existe", headers=h).status_code == 404
    assert client.get("/api/proposals/nao-existe/pdf", headers=h).status_code == 404
    assert client.delete(f"/api/proposals/{p['id']}", headers=h).status_code == 200
    assert client.get(f"/api/proposals/{p['id']}", headers=h).status_code == 404


def test_proposal_whatsapp_fallback_e_settings(client):
    """Sem Evolution configurada: 200 com link wa.me (nunca falha silenciosa)."""
    h = _login(client)
    cid = client.post("/api/clients", headers=h,
                      json={"name": "Cliente Zap QA", "phone": "(55) 99999-1234"}).get_json()["id"]
    p = client.post("/api/proposals", headers=h, json={
        "client_id": cid,
        "items": [{"description": "Mesa", "quantity": 1, "unit_price": 800}],
    }).get_json()

    st = client.get("/api/settings", headers=h)
    assert st.status_code == 200, st.get_data(as_text=True)
    assert all(not s["configured"] for s in st.get_json()), "settings deveria comecar vazio"

    r = client.post(f"/api/proposals/{p['id']}/send-whatsapp", headers=h)
    assert r.status_code == 200, r.get_data(as_text=True)
    body = r.get_json()
    assert body["sent"] is False
    assert body["fallback_wa_me"].startswith("https://wa.me/55"), body["fallback_wa_me"]
    assert "Mesa" in body["fallback_wa_me"], "a mensagem tem que ir no link"
    # fallback NAO marca enviada: abrir o link nao prova que a mensagem saiu
    assert body["proposal"]["status"] == "RASCUNHO", body["proposal"]["status"]
    assert body["proposal"]["sent_channel"] == ""

    # cliente sem telefone -> 400 (nao ha para quem enviar)
    cid2 = client.post("/api/clients", headers=h,
                       json={"name": "Cliente Sem Fone QA"}).get_json()["id"]
    p2 = client.post("/api/proposals", headers=h, json={
        "client_id": cid2,
        "items": [{"description": "X", "quantity": 1, "unit_price": 1}]}).get_json()
    assert client.post(f"/api/proposals/{p2['id']}/send-whatsapp", headers=h).status_code == 400

    # chave secreta volta mascarada
    client.put("/api/settings", headers=h, json={
        "evolution_key": "chave-secreta-1234", "evolution_url": "https://evo.exemplo.com"})
    st = {s["key"]: s for s in client.get("/api/settings", headers=h).get_json()}
    assert st["evolution_key"]["value"].endswith("1234"), st["evolution_key"]["value"]
    assert "secreta" not in st["evolution_key"]["value"], "a chave nao pode voltar inteira"
    assert st["evolution_url"]["value"] == "https://evo.exemplo.com"
    # reenviar o valor mascarado NAO pode destruir a chave guardada
    client.put("/api/settings", headers=h, json={"evolution_key": st["evolution_key"]["value"]})
    st2 = {s["key"]: s for s in client.get("/api/settings", headers=h).get_json()}
    assert st2["evolution_key"]["value"].endswith("1234"), st2["evolution_key"]["value"]


def test_commissions_calculation(client):
    """Comissao: 5% sobre venda fechada de 10.000 = 500."""
    h = _login(client)
    admin_id = client.get("/api/auth/me", headers=h).get_json()["id"]

    r = client.post("/api/commission-rules", headers=h,
                    json={"seller_id": admin_id, "percent": 5})
    assert r.status_code == 201, r.get_data(as_text=True)
    regra = r.get_json()
    assert regra["percent"] == 5.0, regra["percent"]
    assert regra["seller_name"] == "admin"
    assert regra["active"] is True

    # venda fechada: cliente com vendedor e valor, fechado pela tela Gerar venda
    cid = client.post("/api/clients", headers=h, json={
        "name": "Cliente Comissao QA", "estimated_value": 10000, "seller_id": admin_id,
    }).get_json()["id"]
    r = client.put(f"/api/clients/{cid}", headers=h, json={"funnel_status": "FECHAMENTO"})
    assert r.status_code == 200, r.get_data(as_text=True)
    assert r.get_json()["seller_id"] == admin_id, r.get_json()["seller_id"]
    assert r.get_json()["closed_at"] is None  # o funil sozinho nao fecha mais
    sale = client.post("/api/sales", headers=h, json={
        "client_id": cid, "seller_id": admin_id, "total_value": 10000,
        "down_payment": 10000, "installments": 0, "installment_value": 0,
        "installments_due": [], "sale_date": date.today().isoformat(), "environments": [],
    })
    assert sale.status_code == 201, sale.get_data(as_text=True)
    assert client.get(f"/api/clients/{cid}", headers=h).get_json()["closed_at"]

    hoje = date.today()
    rel = client.get(f"/api/commissions?year={hoje.year}&month={hoje.month}", headers=h)
    assert rel.status_code == 200, rel.get_data(as_text=True)
    dados = rel.get_json()
    linha = [l for l in dados["rows"] if l["seller_id"] == admin_id]
    assert linha, f"sem linha para o vendedor: {dados['rows']}"
    assert linha[0]["kind"] == "VENDEDOR"
    assert linha[0]["sold_value"] == 10000.0, linha[0]["sold_value"]
    assert linha[0]["commission_value"] == 500.0, linha[0]["commission_value"]
    assert dados["total_commission"] >= 500.0, dados["total_commission"]

    # mes sem venda nao pode herdar a comissao do mes com venda
    outro_mes = 1 if hoje.month != 1 else 2
    vazio = client.get(f"/api/commissions?year={hoje.year}&month={outro_mes}",
                       headers=h).get_json()
    assert vazio["total_commission"] == 0.0, vazio["total_commission"]

    # validacoes
    assert client.post("/api/commission-rules", headers=h,
                       json={"percent": 5}).status_code == 400, "regra sem dono"
    assert client.post("/api/commission-rules", headers=h,
                       json={"seller_id": admin_id, "percent": 150}).status_code == 400
    assert client.post("/api/commission-rules", headers=h,
                       json={"seller_id": admin_id, "percent": "muito"}).status_code == 400
    assert client.post("/api/commission-rules", headers=h,
                       json={"seller_id": "nao-existe", "percent": 5}).status_code == 404
    assert client.post("/api/commission-rules", headers=h,
                       json={"partner_id": "nao-existe", "percent": 5}).status_code == 404
    assert client.get("/api/commissions?year=1800", headers=h).status_code == 400
    assert client.get("/api/commissions?year=2026&month=13", headers=h).status_code == 400

    # desativar a regra tira a comissao do calculo
    assert client.put(f"/api/commission-rules/{regra['id']}",
                      headers=h, json={"active": False}).status_code == 200
    depois = client.get(f"/api/commissions?year={hoje.year}&month={hoje.month}",
                        headers=h).get_json()
    assert not [l for l in depois["rows"] if l["rule_id"] == regra["id"]], "regra inativa nao conta"
    # a venda nao some do relatorio: aparece como sem atribuicao
    assert depois["sem_atribuicao"]["count"] >= 1, depois["sem_atribuicao"]

    assert client.delete(f"/api/commission-rules/{regra['id']}", headers=h).status_code == 200
    assert client.delete("/api/commission-rules/nao-existe", headers=h).status_code == 404


def test_proposal_whatsapp_envia_pela_evolution(client, monkeypatch):
    """Com Evolution configurada, o envio marca ENVIADA e canal WHATSAPP."""
    import app.api.proposals_bp as pb
    from urllib.error import HTTPError

    class _Resp:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    chamadas = {}

    def fake_urlopen(req, timeout=None):
        chamadas["url"] = req.full_url
        chamadas["apikey"] = req.get_header("Apikey")
        chamadas["corpo"] = req.data.decode()
        return _Resp()

    monkeypatch.setattr(pb, "urlopen", fake_urlopen)

    h = _login(client)
    cid = client.post("/api/clients", headers=h, json={
        "name": "Cliente Evolution QA", "phone": "55999998888"}).get_json()["id"]
    p = client.post("/api/proposals", headers=h, json={
        "client_id": cid,
        "items": [{"description": "Armario", "quantity": 1, "unit_price": 1200}],
    }).get_json()

    # sem configuracao nao chama a Evolution nem marca nada
    r = client.post(f"/api/proposals/{p['id']}/send-whatsapp", headers=h)
    assert r.get_json()["sent"] is False
    assert not chamadas, "nao pode chamar a Evolution sem configuracao"

    client.put("/api/settings", headers=h, json={
        "evolution_url": "https://evo.exemplo.com", "evolution_key": "k-12345678",
        "evolution_instance": "eme"})

    r = client.post(f"/api/proposals/{p['id']}/send-whatsapp", headers=h)
    assert r.status_code == 200, r.get_data(as_text=True)
    body = r.get_json()
    assert body["sent"] is True, body
    assert body["channel"] == "WHATSAPP"
    assert body["fallback_wa_me"] is None, "quem enviou nao precisa de link"
    assert body["proposal"]["status"] == "ENVIADA", body["proposal"]["status"]
    assert body["proposal"]["sent_channel"] == "WHATSAPP"
    assert body["proposal"]["sent_at"], "envio tem que gravar a data"

    # a chamada foi para o lugar certo, com a chave e o telefone com pais
    assert chamadas["url"] == "https://evo.exemplo.com/message/sendText/eme", chamadas["url"]
    assert chamadas["apikey"] == "k-12345678", chamadas["apikey"]
    assert "55999998888" in chamadas["corpo"], chamadas["corpo"]
    assert "Armario" in chamadas["corpo"], chamadas["corpo"]

    # Evolution fora do ar: cai no fallback em vez de estourar 500
    def falha(req, timeout=None):
        raise HTTPError(req.full_url, 500, "erro interno", None, None)

    monkeypatch.setattr(pb, "urlopen", falha)

    p2 = client.post("/api/proposals", headers=h, json={
        "client_id": cid,
        "items": [{"description": "Mesa", "quantity": 1, "unit_price": 300}]}).get_json()
    r = client.post(f"/api/proposals/{p2['id']}/send-whatsapp", headers=h)
    assert r.status_code == 200, r.get_data(as_text=True)
    b2 = r.get_json()
    assert b2["sent"] is False, b2
    assert b2["fallback_wa_me"].startswith("https://wa.me/"), b2["fallback_wa_me"]
    assert "500" in b2["detail"], b2["detail"]
    # e nao pode ter marcado como enviada
    assert b2["proposal"]["status"] == "RASCUNHO", b2["proposal"]["status"]
    assert b2["proposal"]["sent_channel"] == ""




def test_upload_acima_do_limite_retorna_413_json():
    """413 precisa voltar em JSON com o limite REAL, nao HTML cru do Flask.

    A tela lia um numero escrito na mao ("25 MB") enquanto o nginx cortava em
    1 MB — mensagem sem relacao com o bloqueio de verdade. O limite agora vem
    do backend (corpo do 413 e /api/health), entao nao sai de sincronia.
    """
    import io

    app = create_app("test")
    app.config.update(TESTING=True)
    # Limite de 1 KB: nao precisa enviar 50 MB para exercitar o 413.
    app.config["MAX_CONTENT_LENGTH"] = 1024

    with app.test_client() as c:
        with app.app_context():
            db.session.query(User).filter_by(username="admin").delete()
            db.session.add(
                User(
                    username="admin",
                    name="Admin",
                    email="admin@test.local",
                    role="ADMIN",
                    password=hash_password("admin12345"),
                )
            )
            db.session.commit()

        h = _login(c)
        cid = c.post("/api/clients", headers=h, json={"name": "Cliente Grande"}).get_json()["id"]

        r = c.post(
            f"/api/clients/{cid}/attachments",
            headers=h,
            data={"file": (io.BytesIO(b"x" * 5000), "grande.pdf")},
            content_type="multipart/form-data",
        )

        assert r.status_code == 413, r.status_code
        body = r.get_json()
        assert body is not None, "413 voltou como HTML em vez de JSON"
        assert body.get("limit_mb") == 1, body
        assert "1 MB" in body["detail"], body

        # /api/health tambem expoe o limite, para a tela nao escrever o numero a mao
        assert c.get("/api/health").get_json()["max_upload_mb"] == 1


def test_concluir_projeto_sai_da_producao_e_vai_para_pos_venda(client):
    """Botao "Concluir projeto": flag explicita, NAO a coluna do funil.

    Neste funil de Producao a chave "CONCLUIDO" e a coluna "Medicao In Loco",
    entao a conclusao nao pode ser deduzida da chave da coluna.
    """
    h = _login(client)
    cid = client.post("/api/clients", headers=h, json={"name": "Cliente Conclusao"}).get_json()["id"]
    pid = client.post("/api/projects", headers=h, json={
        "title": "Projeto para concluir", "client_id": cid, "status": "MONTAGEM",
    }).get_json()["id"]

    # antes: em producao, fora da lista de concluidos
    assert client.get(f"/api/projects/{pid}", headers=h).get_json()["is_concluded"] is False
    concluidos = client.get("/api/projects/concluded", headers=h).get_json()
    assert all(p["id"] != pid for p in concluidos)

    # concluir pelo botao
    r = client.post(f"/api/projects/{pid}/conclude", headers=h)
    assert r.status_code == 200, r.get_data(as_text=True)
    j = r.get_json()
    assert j["is_concluded"] is True and j["concluded_at"], j

    # agora aparece na lista que alimenta o Pos-venda
    concluidos = client.get("/api/projects/concluded", headers=h).get_json()
    assert any(p["id"] == pid for p in concluidos), "concluido tem de aparecer no pos-venda"

    # idempotente: concluir de novo nao reescreve a data original
    primeira = client.get(f"/api/projects/{pid}", headers=h).get_json()["concluded_at"]
    client.post(f"/api/projects/{pid}/conclude", headers=h)
    assert client.get(f"/api/projects/{pid}", headers=h).get_json()["concluded_at"] == primeira

    # reabrir tira do pos-venda e devolve para a producao
    r = client.post(f"/api/projects/{pid}/reopen", headers=h)
    assert r.status_code == 200 and r.get_json()["is_concluded"] is False
    concluidos = client.get("/api/projects/concluded", headers=h).get_json()
    assert all(p["id"] != pid for p in concluidos)


def test_concluir_venda_cria_projeto_na_producao(client):
    """Botao "Concluir venda": marca a venda E cria o projeto, na mesma chamada."""
    h = _login(client)
    cid = client.post("/api/clients", headers=h, json={"name": "Cliente Venda"}).get_json()["id"]
    assert client.get(f"/api/clients/{cid}", headers=h).get_json()["sale_concluded_at"] is None

    r = client.post(f"/api/clients/{cid}/conclude-sale", headers=h,
                    json={"title": "Cozinha da venda", "value": 5000})
    assert r.status_code == 201, r.get_data(as_text=True)
    proj = r.get_json()
    assert proj["client_id"] == cid
    assert proj["title"] == "Cozinha da venda"
    assert float(proj["value"]) == 5000
    assert proj["is_concluded"] is False, "o projeto nasce em producao, nao concluido"

    # a venda fica marcada como concluida -> o card sai do funil de vendas
    assert client.get(f"/api/clients/{cid}", headers=h).get_json()["sale_concluded_at"]

    ids = [p["id"] for p in client.get("/api/projects", headers=h).get_json()]
    assert proj["id"] in ids, "o projeto criado tem de aparecer na producao"

    # sem title, cai no nome do cliente
    cid2 = client.post("/api/clients", headers=h, json={"name": "Cliente Sem Titulo"}).get_json()["id"]
    r = client.post(f"/api/clients/{cid2}/conclude-sale", headers=h, json={})
    assert r.status_code == 201, r.get_data(as_text=True)
    assert r.get_json()["title"] == "Projeto - Cliente Sem Titulo"


def test_concluir_venda_grava_closed_at_e_entra_na_meta(client):
    """Regressao do bug real: venda de R$ 12.570 concluida pelo botao criava o
    projeto mas nao aparecia no Dashboard inicial (meta) nem no comercial.

    Causa: conclude-sale gravava so sale_concluded_at; meta/comissao/CRM leem
    closed_at (ou a etapa FECHAMENTO). O botao agora grava closed_at junto.
    """
    from datetime import datetime
    h = _login(client)
    cur_year = datetime.now().year
    cr = client.post("/api/clients", headers=h,
                     json={"name": "Cliente 12570", "estimated_value": 12570})
    assert cr.status_code == 201, cr.get_data(as_text=True)
    cid = cr.get_json()["id"]

    r = client.post(f"/api/clients/{cid}/conclude-sale", headers=h, json={})
    assert r.status_code == 201, r.get_data(as_text=True)

    cli = client.get(f"/api/clients/{cid}", headers=h).get_json()
    assert cli["sale_concluded_at"], "o botao marca a venda como concluida"
    assert cli["closed_at"], "o botao tem de gravar closed_at (base da meta/comissao)"

    # Dashboard inicial: meta do ano enxerga a venda no realizado
    body = client.get("/api/goals/summary", headers=h,
                      query_string={"year": cur_year}).get_json()
    assert body["deals_closed"] == 1, body
    assert body["achieved"] == "R$ 12.570,00", body

    # Dashboard comercial: relatorio CRM conta a venda concluida pelo botao
    crm = client.get("/api/reports/crm", headers=h).get_json()
    conv = crm.get("conversao", {})
    assert conv.get("total_fechamentos") == 1, conv


def test_concluir_venda_idempotente_nao_reescreve_closed_at(client):
    """Concluir duas vezes nao muda a data original de fechamento."""
    h = _login(client)
    cid = client.post("/api/clients", headers=h,
                      json={"name": "Cliente Duplo"}).get_json()["id"]
    assert client.post(f"/api/clients/{cid}/conclude-sale", headers=h, json={}).status_code == 201
    primeiro = client.get(f"/api/clients/{cid}", headers=h).get_json()["closed_at"]
    assert primeiro
    assert client.post(f"/api/clients/{cid}/conclude-sale", headers=h, json={}).status_code == 201
    depois = client.get(f"/api/clients/{cid}", headers=h).get_json()["closed_at"]
    assert depois == primeiro, "segunda conclusao nao reescreve closed_at"


def test_register_direct_sale_sem_financeiro_nem_producao(client):
    """Botao Registrar venda do FECHAMENTO: cria Sale sem financeiro/producao."""
    from app.models.models import FinancialRecord, Project, Sale
    h = _login(client)
    cid = client.post("/api/clients", headers=h,
                      json={"name": "Fechado Entregue", "estimated_value": 8000,
                            "funnel_status": "FECHAMENTO"}).get_json()["id"]
    r = client.post(f"/api/clients/{cid}/register-direct-sale", headers=h, json={})
    assert r.status_code == 201, r.get_data(as_text=True)
    body = r.get_json()
    assert body["total_value"] == 8000, body
    assert body["client_id"] == cid
    with client.application.app_context():
        from app.extensions import db
        assert db.session.query(Sale).filter_by(client_id=cid).count() == 1
        assert db.session.query(Project).filter_by(client_id=cid).count() == 0
        assert db.session.query(FinancialRecord).filter_by(client_id=cid).count() == 0
    cli = client.get(f"/api/clients/{cid}", headers=h).get_json()
    assert cli["sale_concluded_at"] and cli["closed_at"]
    # card sai do funil pela flag, igual ao conclude-sale
    crm = client.get("/api/reports/crm", headers=h).get_json()
    assert crm["fechamentos_periodo"]["qtd"] >= 1
    # sem valor no card e sem valor no body -> 400 honesto
    cid2 = client.post("/api/clients", headers=h,
                       json={"name": "Fechado Sem Valor"}).get_json()["id"]
    r2 = client.post(f"/api/clients/{cid2}/register-direct-sale", headers=h, json={})
    assert r2.status_code == 400, r2.get_data(as_text=True)
    assert client.post("/api/clients/nao-existe/register-direct-sale",
                       headers=h, json={}).status_code == 404


def test_satisfaction_envia_e_responde(client):
    """POST /api/satisfaction cria com sent_at; resposta marca answered_at."""
    h = _login(client)
    cid = client.post("/api/clients", headers=h, json={"name": "Cliente Sat"}).get_json()["id"]
    r = client.post("/api/satisfaction", headers=h, json={"client_id": cid})
    assert r.status_code == 201, r.get_data(as_text=True)
    sid = r.get_json()["id"]
    assert r.get_json()["answered"] is False
    r2 = client.post(f"/api/satisfaction/{sid}/answer", headers=h,
                     json={"score": 5, "comment": "Excelente"})
    assert r2.status_code == 200
    b = r2.get_json()
    assert b["score"] == 5
    assert b["answered"] is True
    assert b["answered_at"]
    # resposta nao reescreve: segundo answer muda o score mas nao a data
    antes = b["answered_at"]
    r3 = client.post(f"/api/satisfaction/{sid}/answer", headers=h, json={"score": 4})
    b3 = r3.get_json()
    assert b3["score"] == 4
    assert b3["answered_at"] == antes


def test_satisfaction_sem_duplicata_no_mesmo_dia(client):
    """Reenviar a mesma pesquisa no mesmo dia nao cria outra linha."""
    h = _login(client)
    cid = client.post("/api/clients", headers=h, json={"name": "Cliente Sat2"}).get_json()["id"]
    r1 = client.post("/api/satisfaction", headers=h, json={"client_id": cid})
    r2 = client.post("/api/satisfaction", headers=h, json={"client_id": cid})
    assert r1.status_code == 201 and r2.status_code == 200
    assert r1.get_json()["id"] == r2.get_json()["id"]


def test_satisfaction_summary_media_e_distribuicao(client):
    h = _login(client)
    # dedupe diario: um envio por cliente/dia — usa tres clientes diferentes
    cids = [client.post("/api/clients", headers=h,
                        json={"name": f"Cliente Sat3-{i}"}).get_json()["id"] for i in range(3)]
    s1 = client.post("/api/satisfaction", headers=h, json={"client_id": cids[0]}).get_json()["id"]
    client.post("/api/satisfaction", headers=h, json={"client_id": cids[1], "score": 5, "comment": "otimo"}).get_json()["id"]
    client.post("/api/satisfaction", headers=h, json={"client_id": cids[2]}).get_json()["id"]
    client.post(f"/api/satisfaction/{s1}/answer", headers=h, json={"score": 3})
    b = client.get("/api/satisfaction/summary", headers=h).get_json()
    assert b["total"] == 3
    assert b["answered"] == 2
    assert b["average"] == 4.0
    assert b["distribution"]["5"] == 1
    assert b["distribution"]["3"] == 1
    assert b["distribution"]["1"] == 0


def test_satisfaction_score_invalido(client):
    h = _login(client)
    cid = client.post("/api/clients", headers=h, json={"name": "Cliente Sat4"}).get_json()["id"]
    r = client.post("/api/satisfaction", headers=h, json={"client_id": cid, "score": 9})
    assert r.status_code == 400
    r2 = client.post("/api/satisfaction", headers=h, json={})
    assert r2.status_code == 400


def test_garantia_concluir_projeto_deriva_data_e_campo_manual_e_fallback(client):
    """Concluir projeto com warranty_months deriva warranty_until; ticket sem
    projeto usa campo manual; ticket com projeto usa o prazo do projeto."""
    h = _login(client)
    # base 15/nov/2026 + 2 meses = 15/jan/2027 (futuro, garantia vigente)
    cid = client.post("/api/clients", headers=h, json={"name": "Cliente Gar"}).get_json()["id"]
    pid = client.post("/api/projects", headers=h, json={
        "title": "Guarda 15nov", "client_id": cid,
        "actual_end_date": "2026-11-15", "warranty_months": 2,
    }).get_json()["id"]
    p = client.post(f"/api/projects/{pid}/conclude", headers=h).get_json()
    assert p["concluded_at"]
    assert p["warranty_months"] == 2
    assert p["warranty_until"] == "2027-01-15", p["warranty_until"]
    assert p["in_warranty"] is True
    # edita garantia para 0 -> esvazia
    p2 = client.patch(f"/api/projects/{pid}/warranty", headers=h, json={"warranty_months": 0}).get_json()
    assert p2["warranty_until"] is None
    assert p2["in_warranty"] is False
    # ticket ligado ao projeto (sem campo manual) herda a derivada
    p3 = client.patch(f"/api/projects/{pid}/warranty", headers=h, json={"warranty_months": 1}).get_json()
    assert p3["warranty_until"] == "2026-12-15"
    tk = client.post("/api/tickets", headers=h, json={
        "client_id": cid, "project_id": pid, "description": "Arrependido na porta"},
        ).get_json()
    assert tk["in_warranty"] is True, tk
    assert tk["warranty_until"] == "2026-12-15"
#
# O ponto que estes testes protegem: registrar uma perda NAO e so gravar um
# registro — ela tem de mexer no estoque e no extrato de movimentacoes, na
# mesma transacao. Se um dia alguem "simplificar" isso, o estoque passa a
# divergir do que o sistema mostra.


def _stock_item(client, h, *, sku, quantity=20, min_quantity=5, price=100):
    cat = client.post("/api/stock/categories", headers=h,
                      json={"name": f"Categoria {sku}", "category_type": "STOCK"}).get_json()
    r = client.post("/api/stock", headers=h, json={
        "name": f"Item {sku}", "sku": sku, "category_id": cat["id"],
        "quantity": quantity, "min_quantity": min_quantity, "unit": "un", "price": price,
    })
    assert r.status_code == 201, r.get_data(as_text=True)
    return r.get_json()


def test_perda_decrementa_estoque_e_grava_movimento(client):
    h = _login(client)
    item = _stock_item(client, h, sku="PERDA-01", quantity=20, price=100)

    r = client.post("/api/stock/losses", headers=h, json={
        "stock_item_id": item["id"], "quantity": 5, "kind": "PERDA",
        "reason": "quebrou no transporte",
    })
    assert r.status_code == 201, r.get_data(as_text=True)
    perda = r.get_json()

    # 1) o estoque caiu de 20 para 15
    depois = client.get(f"/api/stock/{item['id']}", headers=h).get_json()
    assert float(depois["quantity"]) == 15.0

    # 2) e existe EXATAMENTE 1 movimento do item, do tipo PERDA
    movs = client.get("/api/stock/movements/history", headers=h).get_json()
    do_item = [m for m in movs if m["item_id"] == item["id"]]
    assert len(do_item) == 1, do_item
    assert do_item[0]["type"] == "PERDA"
    assert float(do_item[0]["quantity"]) == 5.0
    assert "quebrou no transporte" in do_item[0]["reason"]

    # 3) o custo, sem ser informado, e o preco cadastrado x a quantidade (100 * 5)
    assert perda["cost"] == 500.0
    assert perda["kind"] == "PERDA"
    assert perda["item_name"] == item["name"]
    assert perda["item_sku"] == "PERDA-01"


def test_perda_recusa_quantidade_maior_que_o_estoque(client):
    """Perda maior que o saldo nao pode virar estoque negativo.

    Se o usuario perdeu mais do que o sistema diz que existe, o saldo ja estava
    errado antes — recusar forca corrigir, em vez de gravar um numero impossivel.
    """
    h = _login(client)
    item = _stock_item(client, h, sku="PERDA-02", quantity=3)

    r = client.post("/api/stock/losses", headers=h, json={
        "stock_item_id": item["id"], "quantity": 10, "kind": "PERDA",
    })
    assert r.status_code == 400, r.get_data(as_text=True)
    assert "estoque atual" in r.get_json()["detail"]

    # nada mudou: nem estoque, nem perda, nem movimento
    assert float(client.get(f"/api/stock/{item['id']}", headers=h).get_json()["quantity"]) == 3.0
    assert client.get("/api/stock/losses", headers=h).get_json() == []
    assert client.get("/api/stock/movements/history", headers=h).get_json() == []


def test_perda_valida_tipo_quantidade_e_item(client):
    h = _login(client)
    item = _stock_item(client, h, sku="PERDA-03", quantity=10)

    r = client.post("/api/stock/losses", headers=h,
                    json={"stock_item_id": item["id"], "quantity": 1, "kind": "EXTRAVIO"})
    assert r.status_code == 400 and "PERDA ou AVARIA" in r.get_json()["detail"]

    r = client.post("/api/stock/losses", headers=h,
                    json={"stock_item_id": item["id"], "quantity": 0, "kind": "AVARIA"})
    assert r.status_code == 400

    r = client.post("/api/stock/losses", headers=h,
                    json={"stock_item_id": "nao-existe", "quantity": 1, "kind": "PERDA"})
    assert r.status_code == 404

    # avaria e um tipo valido, e custo negativo e recusado
    r = client.post("/api/stock/losses", headers=h, json={
        "stock_item_id": item["id"], "quantity": 1, "kind": "avaria", "cost": -5,
    })
    assert r.status_code == 400

    r = client.post("/api/stock/losses", headers=h, json={
        "stock_item_id": item["id"], "quantity": 1, "kind": "avaria",
    })
    assert r.status_code == 201, r.get_data(as_text=True)
    assert r.get_json()["kind"] == "AVARIA"  # normalizado para maiusculo


def test_perda_resumo_soma_por_tipo_e_por_motivo(client):
    """O resumo existe para dizer ONDE esta o prejuizo, nao so quanto."""
    h = _login(client)
    a = _stock_item(client, h, sku="PERDA-04A", quantity=50, price=10)
    b = _stock_item(client, h, sku="PERDA-04B", quantity=50, price=100)

    for payload in (
        {"stock_item_id": a["id"], "quantity": 5, "kind": "PERDA", "reason": "transporte"},
        {"stock_item_id": a["id"], "quantity": 3, "kind": "PERDA", "reason": "transporte"},
        {"stock_item_id": b["id"], "quantity": 2, "kind": "AVARIA", "reason": "umidade"},
    ):
        assert client.post("/api/stock/losses", headers=h, json=payload).status_code == 201

    s = client.get("/api/stock/losses/summary", headers=h).get_json()
    assert s["count"] == 3
    # 5*10 + 3*10 + 2*100 = 50 + 30 + 200
    assert s["total_cost"] == 280.0
    assert s["total_quantity"] == 10.0

    por_tipo = {bloco["key"]: bloco for bloco in s["by_kind"]}
    assert por_tipo["PERDA"]["count"] == 2
    assert por_tipo["PERDA"]["cost"] == 80.0
    assert por_tipo["AVARIA"]["count"] == 1
    assert por_tipo["AVARIA"]["cost"] == 200.0

    # por motivo, do maior prejuizo para o menor — e onde se decide o que atacar
    assert [bloco["key"] for bloco in s["by_reason"]] == ["umidade", "transporte"]
    assert s["by_reason"][0]["cost"] == 200.0


def test_perda_filtra_por_tipo_e_periodo(client):
    h = _login(client)
    item = _stock_item(client, h, sku="PERDA-05", quantity=50)

    for payload in (
        {"stock_item_id": item["id"], "quantity": 1, "kind": "PERDA", "loss_date": "2026-01-10"},
        {"stock_item_id": item["id"], "quantity": 2, "kind": "AVARIA", "loss_date": "2026-03-20"},
    ):
        assert client.post("/api/stock/losses", headers=h, json=payload).status_code == 201

    todas = client.get("/api/stock/losses", headers=h).get_json()
    assert len(todas) == 2
    # mais recente primeiro
    assert todas[0]["loss_date"] == "2026-03-20"

    so_perda = client.get("/api/stock/losses?kind=PERDA", headers=h).get_json()
    assert len(so_perda) == 1 and so_perda[0]["kind"] == "PERDA"

    so_jan = client.get("/api/stock/losses?date_from=2026-01-01&date_to=2026-01-31", headers=h).get_json()
    assert len(so_jan) == 1 and so_jan[0]["loss_date"] == "2026-01-10"

    # o resumo respeita o mesmo filtro
    s = client.get("/api/stock/losses/summary?date_from=2026-01-01&date_to=2026-01-31", headers=h).get_json()
    assert s["count"] == 1
    assert s["date_from"] == "2026-01-01" and s["date_to"] == "2026-01-31"


# ── Fase 8 (parte 2) — check-ins, follow-ups e envio da pesquisa ──
#
# O ponto que estes testes protegem: o pos-venda proativo tem tres pecas
# encadeadas — concluir agenda os contatos, o check-in registra o contato
# feito, e a pesquisa sai por WhatsApp. Se uma peca quebrar, a aba vira
# enfeite: os testes prendem o encadeamento.


def test_checkin_registra_com_marcador_e_lista(client):
    h = _login(client)
    cid = client.post("/api/clients", headers=h, json={"name": "Cliente Checkin"}).get_json()["id"]
    r = client.post("/api/posvenda/checkins", headers=h, json={
        "client_id": cid, "type": "whatsapp", "content": "Perguntou da porta, tudo certo"})
    assert r.status_code == 201, r.get_data(as_text=True)
    b = r.get_json()
    assert b["type"] == "WHATSAPP"
    assert b["content"].startswith("[CHECK-IN PÓS-VENDA]")
    assert b["client_name"] == "Cliente Checkin"
    lista = client.get("/api/posvenda/checkins", headers=h).get_json()
    assert any(c["id"] == b["id"] for c in lista)
    # tipo invalido e conteudo vazio sao recusados
    r2 = client.post("/api/posvenda/checkins", headers=h,
                     json={"client_id": cid, "type": "CONVERSA", "content": "x"})
    assert r2.status_code == 400
    r3 = client.post("/api/posvenda/checkins", headers=h,
                     json={"client_id": cid, "type": "LIGACAO", "content": "  "})
    assert r3.status_code == 400


def test_interaction_aceita_ligacao_visita_whatsapp(client):
    """Os tipos novos nao sao coagidos para OBSERVACAO."""
    h = _login(client)
    cid = client.post("/api/clients", headers=h, json={"name": "Cliente Tipos"}).get_json()["id"]
    for t in ("LIGACAO", "VISITA", "WHATSAPP"):
        r = client.post(f"/api/clients/{cid}/interactions", headers=h,
                        json={"type": t, "content": f"contato {t}"})
        assert r.status_code == 201, r.get_data(as_text=True)
        assert r.get_json()["type"] == t, r.get_json()


def test_concluir_agenda_followups_e_generate_nao_duplica(client):
    from datetime import date, timedelta
    h = _login(client)
    cid = client.post("/api/clients", headers=h, json={"name": "Cliente Agenda"}).get_json()["id"]
    hoje = date.today().isoformat()
    pid = client.post("/api/projects", headers=h, json={
        "title": "Guarda Agenda", "client_id": cid, "actual_end_date": hoje}).get_json()["id"]
    client.post(f"/api/projects/{pid}/conclude", headers=h)
    agenda = client.get("/api/calendar?type=POS_VENDA", headers=h).get_json()
    meus = [e for e in agenda if e["project_id"] == pid]
    assert len(meus) == 2, meus  # default 7 e 30 dias
    assert sorted(e["start_date"] for e in meus) == sorted(
        (date.fromisoformat(hoje) + timedelta(days=d)).isoformat()
        for d in (7, 30))
    # gerar de novo nao duplica — nem por projeto, nem geral
    g1 = client.post("/api/posvenda/followups/generate", headers=h,
                     json={"project_id": pid}).get_json()
    assert g1["created"] == 0
    g2 = client.post("/api/posvenda/followups/generate", headers=h, json={}).get_json()
    assert g2["created"] == 0
    # projeto em producao nao agenda
    pid2 = client.post("/api/projects", headers=h, json={
        "title": "Guarda Aberto", "client_id": cid}).get_json()["id"]
    r = client.post("/api/posvenda/followups/generate", headers=h, json={"project_id": pid2})
    assert r.status_code == 409


def test_satisfaction_send_whatsapp_fallback_sem_evolution(client):
    """Sem Evolution configurada: 200 com wa.me pronto, sem marcar resposta."""
    h = _login(client)
    cid = client.post("/api/clients", headers=h,
                      json={"name": "Cliente Zap", "phone": "(55) 99999-1234"}).get_json()["id"]
    sid = client.post("/api/satisfaction", headers=h, json={"client_id": cid}).get_json()["id"]
    r = client.post(f"/api/satisfaction/{sid}/send-whatsapp", headers=h)
    assert r.status_code == 200, r.get_data(as_text=True)
    b = r.get_json()
    assert b["sent"] is False
    assert b["fallback_wa_me"].startswith("https://wa.me/55999991234?text=")
    assert b["survey"]["answered"] is False
    # cliente sem telefone: 400 explicito
    cid2 = client.post("/api/clients", headers=h, json={"name": "Cliente SemFone"}).get_json()["id"]
    sid2 = client.post("/api/satisfaction", headers=h, json={"client_id": cid2}).get_json()["id"]
    r2 = client.post(f"/api/satisfaction/{sid2}/send-whatsapp", headers=h)
    assert r2.status_code == 400


# ── WhatsApp interno (Evolution) ──
#
# O ponto que estes testes protegem: o webhook e porta aberta — sem chave,
# sem token, sem conversa. E telefone ambiguo nunca vincula cliente.
def _wa_hook(client, token, payload):
    return client.post(f"/api/whatsapp/webhook?token={token}", json=payload)


def _wa_upsert(instance, mid, phone, text, from_me=False, push="Joao"):
    return {
        "event": "messages.upsert",
        "instance": instance,
        "data": {
            "key": {"remoteJid": f"{phone}@s.whatsapp.net", "fromMe": from_me, "id": mid},
            "pushName": push,
            "message": {"conversation": text},
            "messageType": "conversation",
        },
    }


def test_whatsapp_webhook_sem_chave_401(client):
    """Sem evolution_key configurada, o webhook recusa (nunca aberto)."""
    r = client.post("/api/whatsapp/webhook?token=qualquer", json={"event": "x"})
    assert r.status_code == 401


def test_whatsapp_webhook_token_errado_401(client):
    from app.api.whatsapp_bp import webhook_token
    from app.models.models import AppSetting
    h = _login(client)
    with client.application.app_context():
        from app.extensions import db
        db.session.add(AppSetting(key="evolution_key", value="segredo-local"))
        db.session.commit()
    r = _wa_hook(client, "errado", {"event": "messages.upsert", "instance": "eme-moveis", "data": {}})
    assert r.status_code == 401
    tok = webhook_token("segredo-local", "eme-moveis")
    r2 = client.post("/api/whatsapp/webhook", json={"event": "connection.update"})
    assert r2.status_code == 401  # sem token nenhum tambem recusa
    assert len(tok) == 32


def test_whatsapp_webhook_grava_e_dedupa(client):
    """Inbound texto cria conversa+mensagem; redelivery nao duplica."""
    from app.api.whatsapp_bp import webhook_token
    from app.models.models import AppSetting
    h = _login(client)
    cid = client.post("/api/clients", headers=h,
                      json={"name": "Cliente Zap In", "phone": "55999998888"}).get_json()["id"]
    with client.application.app_context():
        from app.extensions import db
        if not db.session.query(AppSetting).filter_by(key="evolution_key").first():
            db.session.add(AppSetting(key="evolution_key", value="segredo-local"))
            db.session.commit()
    tok = webhook_token("segredo-local", "eme-moveis")
    r = _wa_hook(client, tok, _wa_upsert("eme-moveis", "MID-1", "5555999998888", "Ola, preciso de ajuda"))
    assert r.status_code == 200, r.get_data(as_text=True)
    assert r.get_json()["stored"] == 1
    convs = client.get("/api/whatsapp/conversations", headers=h).get_json()
    assert len(convs) == 1
    assert convs[0]["phone"] == "5555999998888"
    assert convs[0]["client_id"] == cid  # link unico pelo telefone
    assert convs[0]["last_body"] == "Ola, preciso de ajuda"
    msgs = client.get(f"/api/whatsapp/conversations/{convs[0]['id']}/messages", headers=h).get_json()
    assert len(msgs) == 1 and msgs[0]["direction"] == "in"
    r2 = _wa_hook(client, tok, _wa_upsert("eme-moveis", "MID-1", "5555999998888", "Ola, preciso de ajuda"))
    assert r2.get_json()["duplicate"] == 1
    msgs2 = client.get(f"/api/whatsapp/conversations/{convs[0]['id']}/messages", headers=h).get_json()
    assert len(msgs2) == 1  # nao duplicou


def test_whatsapp_webhook_fromme_vira_saida_e_evento_outro_ignora(client):
    """fromMe=True (celular pareado) entra como direction=out — sem isso o que
    o dono manda pelo celular nunca aparece no ERP (bug real: só a resposta do
    cliente aparecia). Evento que não é messages.upsert continua ignorado."""
    from app.api.whatsapp_bp import webhook_token
    from app.models.models import AppSetting
    h = _login(client)
    with client.application.app_context():
        from app.extensions import db
        if not db.session.query(AppSetting).filter_by(key="evolution_key").first():
            db.session.add(AppSetting(key="evolution_key", value="segredo-local"))
            db.session.commit()
    tok = webhook_token("segredo-local", "eme-moveis")
    antes = len(client.get("/api/whatsapp/conversations", headers=h).get_json())
    r = _wa_hook(client, tok, _wa_upsert("eme-moveis", "MID-ECO", "5555999000111", "oi, sou eu pelo celular", from_me=True))
    assert r.get_json()["stored"] == 1, r.get_data(as_text=True)
    convs = client.get("/api/whatsapp/conversations", headers=h).get_json()
    assert len(convs) == antes + 1
    msgs = client.get(f"/api/whatsapp/conversations/{convs[-1]['id']}/messages", headers=h).get_json()
    assert len(msgs) == 1 and msgs[0]["direction"] == "out", msgs
    assert convs[-1]["last_direction"] == "out"
    r2 = client.post(f"/api/whatsapp/webhook?token={tok}",
                     json={"event": "connection.update", "instance": "eme-moveis", "data": {}})
    assert r2.get_json()["skipped"] == "connection.update"


def test_whatsapp_eco_do_envio_proprio_nao_duplica(client, monkeypatch):
    """O send grava o provider_id da Evolution; o eco (webhook fromMe com o
    mesmo id) cai no dedupe em vez de virar segunda linha."""
    import app.api.whatsapp_bp as wb
    from app.api.whatsapp_bp import webhook_token
    from app.models.models import AppSetting
    h = _login(client)
    with client.application.app_context():
        from app.extensions import db
        if not db.session.query(AppSetting).filter_by(key="evolution_key").first():
            db.session.add(AppSetting(key="evolution_key", value="segredo-local"))
        if not db.session.query(AppSetting).filter_by(key="evolution_url").first():
            db.session.add(AppSetting(key="evolution_url", value="https://evo.exemplo.com"))
        db.session.commit()
    monkeypatch.setattr(wb, "_evo_call", lambda *a, **k: (200, {"key": {"id": "ECHO-99"}}))
    conv = client.post("/api/whatsapp/conversations", headers=h,
                       json={"phone": "5555999000222", "name": "Eco"}).get_json()
    r = client.post(f"/api/whatsapp/conversations/{conv['id']}/send", headers=h,
                    json={"text": "mensagem do ERP"})
    assert r.status_code == 201, r.get_data(as_text=True)
    assert r.get_json()["provider_id"] == "ECHO-99", r.get_json()
    tok = webhook_token("segredo-local", "eme-moveis")
    eco = _wa_hook(client, tok, _wa_upsert("eme-moveis", "ECHO-99", "5555999000222", "mensagem do ERP", from_me=True))
    assert eco.get_json()["duplicate"] == 1, eco.get_data(as_text=True)
    msgs = client.get(f"/api/whatsapp/conversations/{conv['id']}/messages", headers=h).get_json()
    assert len(msgs) == 1, msgs


def test_whatsapp_sync_puxa_historico_sem_duplicar(client, monkeypatch):
    """POST /sync grava in+out do findMessages; a 2ª chamada só dedupa."""
    import app.api.whatsapp_bp as wb
    from app.models.models import AppSetting
    h = _login(client)
    with client.application.app_context():
        from app.extensions import db
        if not db.session.query(AppSetting).filter_by(key="evolution_key").first():
            db.session.add(AppSetting(key="evolution_key", value="segredo-local"))
        if not db.session.query(AppSetting).filter_by(key="evolution_url").first():
            db.session.add(AppSetting(key="evolution_url", value="https://evo.exemplo.com"))
        db.session.commit()
    conv = client.post("/api/whatsapp/conversations", headers=h,
                       json={"phone": "5555999000333", "name": "Sync"}).get_json()
    hist = {"messages": [
        {"key": {"remoteJid": "5555999000333@s.whatsapp.net", "fromMe": True, "id": "H-1"},
         "pushName": "Dono", "message": {"conversation": "enviei antes pelo celular"},
         "messageTimestamp": 1700000000},
        {"key": {"remoteJid": "5555999000333@s.whatsapp.net", "fromMe": False, "id": "H-2"},
         "pushName": "Cliente", "message": {"conversation": "resposta posterior"},
         "messageTimestamp": 1700000600},
    ]}
    monkeypatch.setattr(wb, "_evo_call", lambda *a, **k: (200, hist))
    r = client.post(f"/api/whatsapp/conversations/{conv['id']}/sync", headers=h)
    assert r.status_code == 200, r.get_data(as_text=True)
    assert r.get_json()["stored"] == 2, r.get_json()
    msgs = client.get(f"/api/whatsapp/conversations/{conv['id']}/messages", headers=h).get_json()
    assert [m["direction"] for m in msgs] == ["out", "in"], msgs
    assert msgs[0]["body"] == "enviei antes pelo celular"
    r2 = client.post(f"/api/whatsapp/conversations/{conv['id']}/sync", headers=h)
    assert r2.get_json()["stored"] == 0 and r2.get_json()["duplicate"] == 2, r2.get_json()


def test_whatsapp_logout_desconecta_sem_apagar(client, monkeypatch):
    """POST /logout derruba a sessão na Evolution e marca o espelho local
    como desconectada — sem apagar conversas nem mensagens."""
    import app.api.whatsapp_bp as wb
    from app.models.models import AppSetting, WhatsappConversation, WhatsappInstance, WhatsappMessage
    h = _login(client)
    # sem config → 409 honesto
    assert client.post("/api/whatsapp/logout", headers=h).status_code == 409
    with client.application.app_context():
        from app.extensions import db
        db.session.add(AppSetting(key="evolution_key", value="segredo-local"))
        db.session.add(AppSetting(key="evolution_url", value="https://evo.exemplo.com"))
        db.session.add(WhatsappInstance(name="eme-moveis", status="conectada", phone="5555999998888"))
        db.session.commit()
    calls = []
    def fake_evo(method, path, key, body=None, timeout=None):
        calls.append((method, path))
        if path.startswith("/instance/logout/"):
            return 200, {}
        if path.startswith("/instance/connectionState/"):
            return 200, {"instance": {"state": "close"}}
        return 200, {}
    monkeypatch.setattr(wb, "_evo_call", fake_evo)
    r = client.post("/api/whatsapp/logout", headers=h)
    assert r.status_code == 200, r.get_data(as_text=True)
    assert r.get_json()["ok"] is True
    assert r.get_json()["connection"] == "close", r.get_json()
    assert calls[0] == ("DELETE", "/instance/logout/eme-moveis"), calls
    assert any(p.startswith("/instance/connectionState/") for _, p in calls), calls
    with client.application.app_context():
        from app.extensions import db
        row = db.session.query(WhatsappInstance).filter_by(name="eme-moveis").first()
        assert row.status == "desconectada" and row.phone == ""
    # Evolution fora do ar → 502 (não finge que desconectou)
    monkeypatch.setattr(wb, "_evo_call", lambda *a, **k: (0, {"error": "sem rede"}))
    r2 = client.post("/api/whatsapp/logout", headers=h)
    assert r2.status_code == 502, r2.get_data(as_text=True)


def test_whatsapp_logout_espera_sessao_cair(client, monkeypatch):
    """Se a Evolution ainda responde 'open' logo após o logout (estado
    transitório — o bug do print), o endpoint espera até sair do open em
    vez de devolver 'desconectado' e a tela voltar a mostrar Conectado."""
    import app.api.whatsapp_bp as wb
    from app.models.models import AppSetting
    h = _login(client)
    with client.application.app_context():
        from app.extensions import db
        if not db.session.query(AppSetting).filter_by(key="evolution_key").first():
            db.session.add(AppSetting(key="evolution_key", value="segredo-local"))
        if not db.session.query(AppSetting).filter_by(key="evolution_url").first():
            db.session.add(AppSetting(key="evolution_url", value="https://evo.exemplo.com"))
        db.session.commit()
    states = ["open", "close"]
    def fake_evo(method, path, key, body=None, timeout=None):
        if path.startswith("/instance/logout/"):
            return 200, {}
        if path.startswith("/instance/connectionState/"):
            return 200, {"instance": {"state": states.pop(0) if len(states) > 1 else states[0]}}
        return 200, []
    monkeypatch.setattr(wb, "_evo_call", fake_evo)
    monkeypatch.setattr("time.sleep", lambda s: None)
    r = client.post("/api/whatsapp/logout", headers=h)
    assert r.status_code == 200, r.get_data(as_text=True)
    body = r.get_json()
    assert body["ok"] is True and body["connection"] == "close", body


def test_whatsapp_qr_mostra_motivo_real_e_tenta_de_novo(client, monkeypatch):
    """QR: em 5xx tenta UMA vez de novo (transitorio pos-logout); se persistir,
    o detail traz o motivo real da Evolution, nao so o 'respondeu 500'."""
    import app.api.whatsapp_bp as wb
    from app.models.models import AppSetting
    h = _login(client)
    with client.application.app_context():
        from app.extensions import db
        if not db.session.query(AppSetting).filter_by(key="evolution_key").first():
            db.session.add(AppSetting(key="evolution_key", value="segredo-local"))
        if not db.session.query(AppSetting).filter_by(key="evolution_url").first():
            db.session.add(AppSetting(key="evolution_url", value="https://evo.exemplo.com"))
        db.session.commit()
    calls = []
    def fake_transitorio(method, path, key, body=None, timeout=None):
        calls.append(path)
        if len(calls) == 1:
            return 500, {"error": "Evolution API respondeu 500",
                         "raw": '{"message": "session cleaning up, try again"}'}
        return 200, {"base64": "AAA", "pairingCode": "", "code": "x"}
    monkeypatch.setattr(wb, "_evo_call", fake_transitorio)
    monkeypatch.setattr("time.sleep", lambda s: None)
    r = client.get("/api/whatsapp/qr", headers=h)
    assert r.status_code == 200, r.get_data(as_text=True)
    assert r.get_json()["base64"] == "AAA"
    assert len(calls) == 2, calls
    monkeypatch.setattr(
        wb, "_evo_call",
        lambda *a, **k: (500, {"error": "Evolution API respondeu 500",
                               "raw": '{"response": {"message": "instance not found"}}'}))
    r2 = client.get("/api/whatsapp/qr", headers=h)
    assert r2.status_code == 502, r2.get_data(as_text=True)
    body2 = r2.get_json()
    assert "instance not found" in body2["detail"], body2
    assert body2["hint"] == "Aguarde alguns segundos e tente de novo."


def test_whatsapp_conversa_renomeia_vincula_e_apaga(client):
    """PUT renomeia + vincula/desvincula cliente; DELETE apaga so no ERP."""
    h = _login(client)
    cid = client.post("/api/clients", headers=h,
                      json={"name": "Cli Zap", "phone": "5555999000444"}).get_json()["id"]
    conv = client.post("/api/whatsapp/conversations", headers=h,
                       json={"phone": "5555999000444"}).get_json()
    assert conv["client_id"] == cid  # auto-link pelo telefone
    base = f"/api/whatsapp/conversations/{conv['id']}"
    r = client.put(base, headers=h, json={"name": "Joao da Obra"})
    assert r.status_code == 200, r.get_data(as_text=True)
    assert r.get_json()["name"] == "Joao da Obra"
    assert r.get_json()["client_id"] == cid  # vinculo preservado
    r2 = client.put(base, headers=h, json={"client_id": None})
    assert r2.status_code == 200 and r2.get_json()["client_id"] is None
    r3 = client.put(base, headers=h, json={"client_id": cid})
    assert r3.get_json()["client_id"] == cid
    assert client.put(base, headers=h, json={"client_id": "nao-existe"}).status_code == 404
    assert client.put("/api/whatsapp/conversations/nao-existe", headers=h,
                      json={"name": "x"}).status_code == 404
    assert client.delete("/api/whatsapp/conversations/nao-existe", headers=h).status_code == 404
    d = client.delete(base, headers=h)
    assert d.get_json() == {"ok": True, "deleted_messages": 0}, d.get_json()
    assert client.get(f"{base}/messages", headers=h).status_code == 404


def test_whatsapp_telefone_ambiguo_nao_vincula(client):
    """O MESMO telefone em DOIS clientes: conversa sem client_id (pior e entregar errado)."""
    from app.api.whatsapp_bp import webhook_token
    from app.models.models import AppSetting, Client
    h = _login(client)
    c1 = client.post("/api/clients", headers=h,
                     json={"name": "Cliente A", "phone": "(55) 99999-7777"}).get_json()["id"]
    c2 = client.post("/api/clients", headers=h,
                     json={"name": "Cliente B", "phone": "5555999997777"}).get_json()["id"]
    with client.application.app_context():
        from app.extensions import db
        rows = db.session.query(Client).filter(Client.id.in_([c1, c2])).all()
        assert len(rows) == 2  # o par e ambiguo de verdade
        if not db.session.query(AppSetting).filter_by(key="evolution_key").first():
            db.session.add(AppSetting(key="evolution_key", value="segredo-local"))
            db.session.commit()
    tok = webhook_token("segredo-local", "eme-moveis")
    r = _wa_hook(client, tok, _wa_upsert("eme-moveis", "MID-AMB", "5555999997777", "qual e meu pedido?"))
    assert r.get_json()["stored"] == 1
    convs = client.get("/api/whatsapp/conversations", headers=h).get_json()
    alvo = next(c for c in convs if c["phone"] == "5555999997777")
    assert alvo["client_id"] is None


def test_whatsapp_send_text_mockado(client, monkeypatch):
    """Envio grava out; a Evolution e mockada (sem rede nos testes)."""
    import app.api.whatsapp_bp as wabp
    from app.models.models import AppSetting
    h = _login(client)
    with client.application.app_context():
        from app.extensions import db
        for k, v in (("evolution_url", "https://evo.invalida"), ("evolution_key", "segredo-local"),
                     ("evolution_instance", "eme-moveis")):
            if not db.session.query(AppSetting).filter_by(key=k).first():
                db.session.add(AppSetting(key=k, value=v))
        db.session.commit()
    conv = client.post("/api/whatsapp/conversations", headers=h,
                       json={"phone": "5555999000222", "name": "Maria"}).get_json()
    monkeypatch.setattr(wabp, "_evo_call", lambda *a, **k: (200, {"key": {"id": "OUT-1"}}))
    r = client.post(f"/api/whatsapp/conversations/{conv['id']}/send", headers=h,
                    json={"text": "Boa tarde, Maria!"})
    assert r.status_code == 201, r.get_data(as_text=True)
    b = r.get_json()
    assert b["direction"] == "out" and b["body"] == "Boa tarde, Maria!" and b["status"] == "sent"
    msgs = client.get(f"/api/whatsapp/conversations/{conv['id']}/messages", headers=h).get_json()
    assert len(msgs) == 1


def test_whatsapp_status_sem_config(client):
    h = _login(client)
    r = client.get("/api/whatsapp/status", headers=h)
    assert r.status_code == 200
    b = r.get_json()
    assert b["configured"] in (True, False)
    assert "connection" in b


def _wa_image_upsert(instance, mid, phone, filename="foto.jpg", mime="image/jpeg", push="Joao"):
    return {
        "event": "messages.upsert",
        "instance": instance,
        "data": {
            "key": {"remoteJid": f"{phone}@s.whatsapp.net", "fromMe": False, "id": mid},
            "pushName": push,
            "message": {"imageMessage": {"caption": "olha a foto", "fileName": filename,
                                         "mimetype": mime, "fileLength": 11}},
            "messageType": "imageMessage",
        },
    }


def test_whatsapp_midia_recebida_baixa_sob_demanda(client, monkeypatch):
    """Imagem recebida: lista marca media_pending; download busca na Evolution (mock)."""
    import base64
    import app.api.whatsapp_bp as wabp
    from app.api.whatsapp_bp import webhook_token
    from app.models.models import AppSetting
    h = _login(client)
    with client.application.app_context():
        from app.extensions import db
        for k, v in (("evolution_url", "https://evo.invalida"), ("evolution_key", "segredo-local"),
                     ("evolution_instance", "eme-moveis")):
            if not db.session.query(AppSetting).filter_by(key=k).first():
                db.session.add(AppSetting(key=k, value=v))
        db.session.commit()
    tok = webhook_token("segredo-local", "eme-moveis")
    r = _wa_hook(client, tok, _wa_image_upsert("eme-moveis", "MID-IMG-1", "5555999000333"))
    assert r.get_json()["stored"] == 1
    convs = client.get("/api/whatsapp/conversations", headers=h).get_json()
    alvo = next(c for c in convs if c["phone"] == "5555999000333")
    msgs = client.get(f"/api/whatsapp/conversations/{alvo['id']}/messages", headers=h).get_json()
    assert len(msgs) == 1
    m = msgs[0]
    assert m["kind"] == "image" and m["has_media"] is False and m["media_pending"] is True
    blob = b"FAKEJPEG123"
    monkeypatch.setattr(wabp, "_evo_call",
                        lambda *a, **k: (200, {"base64": base64.b64encode(blob).decode(),
                                              "mimetype": "image/jpeg"}))
    d1 = client.get(f"/api/whatsapp/messages/{m['id']}/media", headers=h)
    assert d1.status_code == 200, d1.get_data(as_text=True)[:200]
    assert d1.data == blob
    msgs2 = client.get(f"/api/whatsapp/conversations/{alvo['id']}/messages", headers=h).get_json()
    assert msgs2[0]["has_media"] is True and msgs2[0]["media_pending"] is False


def test_whatsapp_midia_recebida_indisponivel_502(client, monkeypatch):
    """Evolution sem a midia (mensagem antiga): 502 honesto, nada inventado."""
    import app.api.whatsapp_bp as wabp
    from app.api.whatsapp_bp import webhook_token
    from app.models.models import AppSetting
    h = _login(client)
    with client.application.app_context():
        from app.extensions import db
        for k, v in (("evolution_url", "https://evo.invalida"), ("evolution_key", "segredo-local"),
                     ("evolution_instance", "eme-moveis")):
            if not db.session.query(AppSetting).filter_by(key=k).first():
                db.session.add(AppSetting(key=k, value=v))
        db.session.commit()
    tok = webhook_token("segredo-local", "eme-moveis")
    _wa_hook(client, tok, _wa_image_upsert("eme-moveis", "MID-IMG-2", "5555999000444"))
    convs = client.get("/api/whatsapp/conversations", headers=h).get_json()
    alvo = next(c for c in convs if c["phone"] == "5555999000444")
    msgs = client.get(f"/api/whatsapp/conversations/{alvo['id']}/messages", headers=h).get_json()
    monkeypatch.setattr(wabp, "_evo_call", lambda *a, **k: (404, {"error": "Message not found"}))
    d = client.get(f"/api/whatsapp/messages/{msgs[0]['id']}/media", headers=h)
    assert d.status_code == 502
    assert "indisponivel" in d.get_json()["detail"] or "not found" in d.get_json()["detail"].lower()


def test_account_plan_seed_completo(client):
    """Seed do plano de contas (importacao do legado): 14 categorias, 54 contas agrupadas."""
    from app.models.models import AccountCategory, AccountPlan

    with client.application.app_context():
        assert AccountCategory.query.count() == 14
        assert AccountPlan.query.count() == 54
    h = _login(client)
    cats = client.get("/api/account-plan/categories", headers=h).get_json()
    assert len(cats) == 14
    assert cats[0]["code"] == 1 and cats[0]["description"] == "Receita com Vendas"
    assert cats[0]["indicator"] == "CREDITO" and cats[0]["dre_range"] == "Receitas"
    assert cats[12]["code"] == 13 and cats[12]["dre_range"] == "Nao listar no DRE"
    plano = client.get("/api/account-plan", headers=h).get_json()
    assert len(plano) == 14
    assert sum(len(g["plans"]) for g in plano) == 54
    g4 = next(g for g in plano if g["code"] == 4)
    assert any(p["structured_code"] == "4.2" and p["description"] == "Materia-prima"
               for p in g4["plans"])
    assert plano[0]["plans"][0]["label"] == "1.1 - Venda de produtos"


def test_account_plan_categorias_crud_guards(client):
    h = _login(client)
    r = client.post("/api/account-plan/categories", headers=h, json={
        "code": 99, "description": "Categoria Teste", "indicator": "DEBITO",
        "dre_range": "Custos fixos",
    })
    assert r.status_code == 201, r.get_data(as_text=True)
    cid = r.get_json()["id"]
    assert client.post("/api/account-plan/categories", headers=h,
                       json={"code": 99, "description": "Outra"}).status_code == 400
    assert client.post("/api/account-plan/categories", headers=h,
                       json={"code": 98, "description": "X",
                             "indicator": "MEIO"}).status_code == 400
    assert client.put(f"/api/account-plan/categories/{cid}", headers=h,
                      json={"description": "Categoria Renomeada"}).status_code == 200
    assert client.delete(f"/api/account-plan/categories/{cid}", headers=h).status_code == 200
    # categoria oficial com contas nao pode ser excluida
    cats = client.get("/api/account-plan/categories", headers=h).get_json()
    c1 = next(c for c in cats if c["code"] == 1)
    r = client.delete(f"/api/account-plan/categories/{c1['id']}", headers=h)
    assert r.status_code == 400 and "conta" in r.get_json()["detail"].lower()


def test_account_plan_contas_validacoes_e_guard_lancamento(client):
    h = _login(client)
    cats = client.get("/api/account-plan/categories", headers=h).get_json()
    c4 = next(c for c in cats if c["code"] == 4)
    r = client.post("/api/account-plan", headers=h, json={
        "code": 60, "structured_code": "4.X", "description": "Teste",
        "category_id": c4["id"],
    })
    assert r.status_code == 400
    r = client.post("/api/account-plan", headers=h, json={
        "code": 99, "structured_code": "4.2", "description": "Duplicada",
        "category_id": c4["id"],
    })
    assert r.status_code == 400
    r = client.post("/api/account-plan", headers=h, json={
        "code": 60, "structured_code": "4.10", "description": "Conta teste",
        "category_id": c4["id"],
    })
    assert r.status_code == 201, r.get_data(as_text=True)
    pid = r.get_json()["id"]
    fin = client.post("/api/financial", headers=h, json={
        "description": "NF teste", "type": "SAIDA", "category": "MATERIAL",
        "amount": 100, "date": "2026-09-01", "account_plan": "4.10",
    })
    assert fin.status_code == 201, fin.get_data(as_text=True)
    # conta usada em lancamento -> bloqueia exclusao
    assert client.delete(f"/api/account-plan/{pid}", headers=h).status_code == 400
    client.delete(f"/api/financial/{fin.get_json()['id']}", headers=h)
    assert client.delete(f"/api/account-plan/{pid}", headers=h).status_code == 200


def test_sale_modelo_campos(client):
    from app.models.models import Sale, SaleInstallment, SaleEnvironment, SaleItem
    from app.models.models import Project
    with client.application.app_context():
        assert hasattr(Sale, "code") and hasattr(Sale, "total_value")
        assert hasattr(SaleInstallment, "due_date") and hasattr(SaleInstallment, "financial_record_id")
        assert hasattr(SaleEnvironment, "name")
        assert hasattr(SaleItem, "product_id") and hasattr(SaleItem, "unit_price")
        assert hasattr(Project, "sale_id")


# ── Venda (Gerar venda + automações) ──────────────────────────

def _mk_sale_client(client, h, name="Cliente Venda"):
    return client.post("/api/clients", headers=h, json={"name": name, "cpf_cnpj": name}).get_json()["id"]


def _mk_sale_bank(client, h, name="Banco Venda"):
    return client.post("/api/bank-accounts", headers=h, json={
        "name": name, "bank": "Teste", "agency": "1", "account_number": "1",
        "account_type": "CORRENTE", "opening_balance": 0,
    }).get_json()["id"]


def _mk_sale_seller(client):
    import uuid
    from app.extensions import db
    from app.auth import hash_password
    from app.models.models import User
    with client.application.app_context():
        u = User(username="vendedor." + uuid.uuid4().hex[:8], name="Vendedor Um",
                 email=uuid.uuid4().hex[:8] + "@test.local", role="GERENTE",
                 password=hash_password("x12345"))
        db.session.add(u)
        db.session.commit()
        return u.id


def _mk_sale_partner(client, h, name="Escritorio Venda"):
    return client.post("/api/partners", headers=h, json={"name": name}).get_json()["id"]


def _sale_payload(client, h, client_id, **over):
    payload = {
        "client_id": client_id,
        "seller_id": _mk_sale_seller(client),
        "partner_id": _mk_sale_partner(client, h),
        "lead_source": "Indicacao",
        "sale_date": "2026-10-05",
        "total_value": 10000,
        "down_payment": 1000,
        "installments": 3,
        "installment_value": 3000,
        "installments_due": ["2026-11-05", "2026-12-05", "2027-01-05"],
        "bank_account_id": _mk_sale_bank(client, h),
        "address": "Rua X, 123",
        "delivery_date": "2026-12-20",
        "environments": ["Sala", "Cozinha"],
    }
    payload.update(over)
    return payload


def test_sale_genera_venda_automatizada(client):
    """Gerar venda: marca o cliente como concluido, cria contas a receber (entrada
    + parcelas) com vencimentos/conta, e um card de producao por ambiente."""
    h = _login(client)
    cid = _mk_sale_client(client, h)
    payload = _sale_payload(client, h, cid)
    r = client.post("/api/sales", headers=h, json=payload)
    assert r.status_code == 201, r.get_data(as_text=True)
    body = r.get_json()
    assert body["code"] == "V-0001"
    assert [e["name"] for e in body["environments"]] == ["Sala", "Cozinha"]
    cli = client.get(f"/api/clients/{cid}", headers=h).get_json()
    assert cli["sale_concluded_at"] and cli["closed_at"]
    fins = client.get("/api/financial", headers=h).get_json()
    novos = [f for f in fins if f["client_id"] == cid and f["account_plan"] == "1.1"]
    assert len(novos) == 4
    entrada = next(f for f in novos if "Entrada" in f["description"])
    assert entrada["amount"] == 1000 and entrada["status"] == "PENDENTE"
    parcelas = sorted([f for f in novos if "parcela" in f["description"]], key=lambda f: f["due_date"])
    assert [f["amount"] for f in parcelas] == [3000, 3000, 3000]
    assert [f["due_date"] for f in parcelas] == ["2026-11-05", "2026-12-05", "2027-01-05"]
    assert all(f["bank_account_id"] == payload["bank_account_id"] for f in novos)
    projs = client.get("/api/projects", headers=h).get_json()
    cards = [p for p in projs if p.get("sale_id") == body["id"]]
    assert len(cards) == 2
    assert sorted(p["title"] for p in cards) == ["Cozinha – Cliente Venda", "Sala – Cliente Venda"]
    assert all(p["deadline"] == "2026-12-20" for p in cards)
    assert all(si["financial_record_id"] for si in body["installments_list"])


def test_sale_valida_soma_parcelas(client):
    h = _login(client)
    cid = _mk_sale_client(client, h)
    p = _sale_payload(client, h, cid, down_payment=500, installment_value=3000)
    r = client.post("/api/sales", headers=h, json=p)
    assert r.status_code == 400
    assert "totalizar" in r.get_json()["detail"].lower()


def test_sale_exige_vencimentos_por_parcela(client):
    h = _login(client)
    cid = _mk_sale_client(client, h)
    p = _sale_payload(client, h, cid, installments_due=["2026-11-05"])
    r = client.post("/api/sales", headers=h, json=p)
    assert r.status_code == 400
    assert "vencimento" in r.get_json()["detail"].lower()


def test_sale_sem_ambientes_cria_card_generico(client):
    h = _login(client)
    cid = _mk_sale_client(client, h)
    p = _sale_payload(client, h, cid, environments=[])
    r = client.post("/api/sales", headers=h, json=p)
    assert r.status_code == 201, r.get_data(as_text=True)
    sid = r.get_json()["id"]
    projs = client.get("/api/projects", headers=h).get_json()
    cards = [x for x in projs if x.get("sale_id") == sid]
    assert len(cards) == 1 and cards[0]["title"] == "Projeto – Cliente Venda"


def test_sale_404_seller_partner_bank_invalidos(client):
    h = _login(client)
    cid = _mk_sale_client(client, h)
    p = _sale_payload(client, h, cid, seller_id="nao-existe")
    assert client.post("/api/sales", headers=h, json=p).status_code == 404
    p = _sale_payload(client, h, cid, partner_id="nao-existe")
    assert client.post("/api/sales", headers=h, json=p).status_code == 404
    p = _sale_payload(client, h, cid, bank_account_id="nao-existe")
    assert client.post("/api/sales", headers=h, json=p).status_code == 404


def test_sale_com_produtos_grava_itens(client):
    h = _login(client)
    cid = _mk_sale_client(client, h)
    prod = client.post("/api/products", headers=h,
                       json={"name": "Cozinha Planejada", "default_price": 6000}).get_json()
    p = _sale_payload(client, h, cid, total_value=12000, down_payment=12000,
                      installments=0, installment_value=0, installments_due=[],
                      items=[{"product_id": prod["id"], "quantity": 1, "unit_price": 6000},
                             {"name": "Painel TV", "quantity": 2, "unit_price": 2500}])
    r = client.post("/api/sales", headers=h, json=p)
    assert r.status_code == 201, r.get_data(as_text=True)
    body = r.get_json()
    assert len(body["items"]) == 2
    cozinha = next(i for i in body["items"] if i["product_id"] == prod["id"])
    assert cozinha["name"] == "Cozinha Planejada" and cozinha["subtotal"] == 6000
    painel = next(i for i in body["items"] if i["name"] == "Painel TV")
    assert painel["quantity"] == 2 and painel["subtotal"] == 5000
    assert body["items_total_diff"] == 1000


def test_sale_product_id_invalido_400(client):
    h = _login(client)
    cid = _mk_sale_client(client, h)
    p = _sale_payload(client, h, cid, items=[{"product_id": "x", "name": "X",
                                              "quantity": 1, "unit_price": 1}])
    assert client.post("/api/sales", headers=h, json=p).status_code == 400


def test_sale_lista_e_detalhe(client):
    h = _login(client)
    cid = _mk_sale_client(client, h)
    sid = client.post("/api/sales", headers=h,
                      json=_sale_payload(client, h, cid)).get_json()["id"]
    lst = client.get("/api/sales", headers=h).get_json()
    assert len(lst) >= 1 and lst[0]["client_name"] == "Cliente Venda"
    d = client.get(f"/api/sales/{sid}", headers=h).get_json()
    assert d["code"] == "V-0001" and len(d["environments"]) == 2


def test_funil_ganho_nao_atualiza_relatorio(client):
    """Arrastar o card para a etapa de ganho NAO atualiza meta/relatorio nem
    cria projeto — so a tela Gerar venda (POST /api/sales) faz isso."""
    from app.models.models import FinancialRecord, Project
    h = _login(client)
    cid = _mk_sale_client(client, h)
    with client.application.app_context():
        before_p = Project.query.count()
        before_f = FinancialRecord.query.count()
    r = client.put(f"/api/clients/{cid}", headers=h, json={"funnel_status": "FECHAMENTO"})
    assert r.status_code == 200, r.get_data(as_text=True)
    cli = r.get_json()
    assert cli.get("sale_concluded_at") is None and cli.get("closed_at") is None
    with client.application.app_context():
        assert Project.query.count() == before_p
        assert FinancialRecord.query.count() == before_f


def test_crm_report_top_products(client):
    h = _login(client)
    cid1 = _mk_sale_client(client, h, "Cliente A")
    cid2 = _mk_sale_client(client, h, "Cliente B")
    p1 = _sale_payload(client, h, cid1, total_value=20000, down_payment=20000,
                       installments=0, installment_value=0, installments_due=[],
                       items=[{"name": "Cozinha", "quantity": 2, "unit_price": 6000},
                              {"name": "Painel TV", "quantity": 1, "unit_price": 3000}])
    assert client.post("/api/sales", headers=h, json=p1).status_code == 201
    p2 = _sale_payload(client, h, cid2, total_value=15000, down_payment=15000,
                       installments=0, installment_value=0, installments_due=[],
                       items=[{"name": "Cozinha", "quantity": 1, "unit_price": 9000},
                              {"name": "Quarto", "quantity": 3, "unit_price": 2000}])
    assert client.post("/api/sales", headers=h, json=p2).status_code == 201
    rel = client.get("/api/reports/crm", headers=h).get_json()
    top = rel.get("top_products") or []
    by_name = {t["name"]: t for t in top}
    assert by_name["Cozinha"]["qty"] == 3 and by_name["Cozinha"]["receita"] == 21000
    assert by_name["Painel TV"]["qty"] == 1 and by_name["Painel TV"]["receita"] == 3000
    assert top[0]["name"] == "Cozinha"  # empate em qty resolve por nome


def test_relatorio_produtos_vendidos(client):
    h = _login(client)
    cid = _mk_sale_client(client, h)
    p = _sale_payload(client, h, cid, sale_date="2026-09-15", total_value=12000,
                      down_payment=12000, installments=0, installment_value=0,
                      installments_due=[],
                      items=[{"name": "Painel TV", "quantity": 2, "unit_price": 3000}])
    assert client.post("/api/sales", headers=h, json=p).status_code == 201
    r = client.get("/api/reports/best-products?year=2026&month=9", headers=h)
    assert r.status_code == 200, r.get_data(as_text=True)
    body = r.get_json()
    assert any(row["produto"] == "Painel TV" and row["qtd"] == "2" and row["receita"] == "R$ 6.000,00"
               for row in body["rows"]), body["rows"]
    r2 = client.get("/api/reports/best-products?year=1999", headers=h)
    assert r2.status_code == 200
    assert all(row["qtd"] == 0 for row in r2.get_json()["rows"]) or not r2.get_json()["rows"]


def test_products_update_e_reativar(client):
    """PUT do catalogo: edicao, inativacao (some da lista normal) e reativacao."""
    h = _login(client)
    pid = client.post("/api/products", headers=h,
                      json={"name": "Produto Edita", "default_price": 100}).get_json()["id"]
    r = client.put(f"/api/products/{pid}", headers=h,
                   json={"name": "Produto Editado", "default_price": 150, "active": False})
    assert r.status_code == 200, r.get_data(as_text=True)
    row = r.get_json()
    assert row["name"] == "Produto Editado" and row["active"] is False
    names = [p["name"] for p in client.get("/api/products", headers=h).get_json()]
    assert "Produto Editado" not in names
    names_all = [p["name"] for p in client.get("/api/products?all=1", headers=h).get_json()]
    assert "Produto Editado" in names_all
    r2 = client.put(f"/api/products/{pid}", headers=h, json={"active": True})
    assert r2.status_code == 200 and r2.get_json()["active"] is True
    names2 = [p["name"] for p in client.get("/api/products", headers=h).get_json()]
    assert "Produto Editado" in names2
    # nome duplicado bloqueia
    cid2 = client.post("/api/products", headers=h, json={"name": "Outro Produto"}).get_json()["id"]
    r3 = client.put(f"/api/products/{cid2}", headers=h, json={"name": "Produto Editado"})
    assert r3.status_code == 400


def test_crm_fase1_vendas_orcamentos_origem(client):
    """Fase 1 Comercial: vendas mes/ano + evolucao, orcamentos e pizza por origem."""
    from datetime import date as _date
    h = _login(client)
    hoje = _date.today()
    mes_atual = f"{hoje.year}-{hoje.month:02d}-15"
    outro = hoje.month - 1 or 12
    mes_outro = f"{hoje.year}-{outro:02d}-10"

    cid1 = _mk_sale_client(client, h, "Cliente Fase1 A")
    cid2 = _mk_sale_client(client, h, "Cliente Fase1 B")
    p1 = _sale_payload(client, h, cid1, lead_source="Instagram",
                       sale_date=mes_atual, total_value=10000,
                       down_payment=10000, installments=0,
                       installment_value=0, installments_due=[])
    assert client.post("/api/sales", headers=h, json=p1).status_code == 201
    p2 = _sale_payload(client, h, cid2, lead_source="Indicacao",
                       sale_date=mes_outro, total_value=5000,
                       down_payment=5000, installments=0,
                       installment_value=0, installments_due=[])
    assert client.post("/api/sales", headers=h, json=p2).status_code == 201

    def _prop(status, itens):
        r = client.post("/api/proposals", headers=h,
                        json={"client_id": cid1, "items": itens})
        assert r.status_code == 201, r.get_data(as_text=True)
        pid = r.get_json()["id"]
        if status != "RASCUNHO":
            r2 = client.put(f"/api/proposals/{pid}", headers=h,
                            json={"status": status})
            assert r2.status_code == 200, r2.get_data(as_text=True)
        return pid

    _prop("ENVIADA", [{"description": "Armario", "quantity": 2, "unit_price": 1000}])
    _prop("RASCUNHO", [{"description": "Rascunho", "quantity": 1, "unit_price": 500}])
    _prop("ACEITA", [{"description": "Cozinha", "quantity": 1, "unit_price": 3000}])

    rel = client.get("/api/reports/crm", headers=h).get_json()
    assert rel["vendas_mes"]["total"] == 10000
    assert rel["vendas_mes"]["qtd"] == 1
    assert rel["vendas_ano"]["total"] == 15000
    assert rel["vendas_ano"]["qtd"] == 2
    assert len(rel["vendas_ano"]["evolucao"]) == 12
    evo = {e["mes"]: e for e in rel["vendas_ano"]["evolucao"]}
    assert evo[mes_atual[:7]]["total"] == 10000
    assert evo[mes_outro[:7]]["total"] == 5000
    assert rel["orcamentos"]["qtd"] == 2
    assert rel["orcamentos"]["valor"] == 5000
    assert rel["orcamentos"]["aceitas"] == 1
    por_origem = {o["origem"]: o for o in rel["vendas_por_origem"]}
    assert por_origem["Instagram"]["valor"] == 10000
    assert por_origem["Indicacao"]["valor"] == 5000


def test_financial_fase2_indicadores(client):
    """Fase 2 Financeiro: faturamento, recebimentos, margem e inadimplencia."""
    h = _login(client)

    def _lanc(tipo, valor, status, plano="", categoria="GERAL", venc=None):
        payload = {"description": "Fase2 %s %s" % (tipo, valor), "type": tipo,
                   "category": categoria, "amount": valor, "date": "2026-10-01",
                   "status": status, "due_date": venc or "2026-10-01"}
        if plano:
            payload["account_plan"] = plano
        r = client.post("/api/financial", headers=h, json=payload)
        assert r.status_code == 201, r.get_data(as_text=True)

    _lanc("ENTRADA", 10000, "PAGO", plano="1.1")
    _lanc("ENTRADA", 3000, "PENDENTE", venc="2025-06-01")
    _lanc("ENTRADA", 2000, "PENDENTE", venc="2027-01-15")
    _lanc("SAIDA", 4000, "PAGO", plano="4.1", categoria="MATERIA-PRIMA")
    _lanc("SAIDA", 500, "PAGO", categoria="Custos Variáveis")
    _lanc("SAIDA", 1000, "PAGO", plano="5.1", categoria="PESSOAL")
    _lanc("SAIDA", 700, "PENDENTE", plano="4.2")

    body = client.get("/api/reports/financial", headers=h).get_json()
    res = {s["label"]: s["value"] for s in body["summary"]}
    assert res["Faturamento"] == "R$ 15.000,00", res
    assert res["Recebimentos"] == "R$ 10.000,00", res
    assert res["Margem de Contribuição"] == "R$ 5.500,00", res
    assert "R$ 3.000,00" in res["Inadimplência"] and "1 título" in res["Inadimplência"], res
    # Sem regressao nos antigos.
    assert res["Saldo do Período"] == "R$ 8.800,00", res


def test_production_fase2_indicadores(client):
    """Fase 3 Producao: em producao, atrasados, entregas, produzido, perdas, pendencias."""
    import datetime as _dt
    from app.extensions import db
    from app.models.models import ChecklistItem
    h = _login(client)
    hoje = _dt.date.today()
    r = client.post("/api/clients", headers=h, json={"name": "Cliente Fase3", "cpf_cnpj": "fase3cli"})
    assert r.status_code == 201, r.get_data(as_text=True)
    cid = r.get_json()["id"]

    def _proj(title, deadline, value, status="PRODUCAO"):
        r = client.post("/api/projects", headers=h,
                        json={"title": title, "client_id": cid, "status": status,
                              "deadline": deadline, "value": value})
        assert r.status_code == 201, r.get_data(as_text=True)
        return r.get_json()["id"]

    pid_atras = _proj("Atrasado Fase3", "2025-01-10", 8000)
    pid_fut = _proj("Futuro Fase3", "2027-06-15", 5000)
    pid_ok = _proj("Concluido Fase3", hoje.isoformat(), 12000)
    assert client.post(f"/api/projects/{pid_ok}/conclude", headers=h).status_code == 200

    r = client.post(f"/api/projects/{pid_atras}/issues", headers=h,
                    json={"kind": "RETRABALHO", "cost": 100, "hours_spent": 3,
                          "reason": "Refazer", "issue_date": hoje.isoformat()})
    assert r.status_code == 201, r.get_data(as_text=True)
    r = client.post(f"/api/projects/{pid_atras}/issues", headers=h,
                    json={"kind": "DESPERDICIO", "material": "MDF", "quantity": 2.5,
                          "cost": 50, "reason": "Corte errado", "issue_date": hoje.isoformat()})
    assert r.status_code == 201, r.get_data(as_text=True)
    r = client.post(f"/api/projects/{pid_atras}/issues", headers=h,
                    json={"kind": "PERDA", "cost": 200, "reason": "Quebra",
                          "issue_date": hoje.isoformat()})
    assert r.status_code == 201, r.get_data(as_text=True)
    with client.application.app_context():
        db.session.add(ChecklistItem(project_id=pid_atras, step_id="s1",
                                     label="Cortar MDF", completed=False))
        db.session.commit()

    body = client.get("/api/reports/production", headers=h).get_json()
    res = {s["label"]: s["value"] for s in body["summary"]}
    assert "Horas Improdutivas" not in res and "Total Horas" not in res, res
    assert res["Projetos em Produção"] == "2", res
    assert res["Projetos Atrasados"] == "1 · R$ 8.000,00", res
    assert res["Entregas Previstas"] == "1", res
    assert res["Produzido no Mês"] == "R$ 12.000,00", res
    assert res["Produzido no Ano"] == "R$ 12.000,00", res
    assert res["Retrabalhos"] == "1", res
    assert res["Horas Perdidas (retrabalho)"] == "3.0h", res
    assert res["Desperdicios"] == "1", res
    assert res["Material Desperdiçado"] == "2.5", res
    assert res["Perdas Financeiras"] == "R$ 350,00", res
    assert res["Pendências de Produção"] == "1", res
    assert body["produzido_mes"]["total"] == 12000
    assert body["produzido_ano"]["total"] == 12000
    assert len(body["produzido_ano"]["evolucao"]) == 12
    assert any(e["title"] == "Futuro Fase3" for e in body["entregas_previstas"])
    # Periodo estilo DRE + parametro invalido.
    tri = client.get("/api/reports/production?period=trimestral", headers=h).get_json()
    assert len(tri["produzido_ano"]["evolucao"]) == 4
    sem = client.get("/api/reports/production?period=semestral", headers=h).get_json()
    assert len(sem["produzido_ano"]["evolucao"]) == 2
    assert client.get("/api/reports/production?period=quinzenal", headers=h).status_code == 400


def test_crm_periodos_buckets(client):
    """Periodo estilo DRE no CRM: mensal/trimestral/semestral/anual + 400."""
    import datetime as _dt
    h = _login(client)
    ano = _dt.date.today().year
    cid = _mk_sale_client(client, h, "Cliente Periodo")
    p = _sale_payload(client, h, cid, sale_date="%d-02-10" % ano, total_value=7000,
                      down_payment=7000, installments=0,
                      installment_value=0, installments_due=[])
    assert client.post("/api/sales", headers=h, json=p).status_code == 201

    base = "/api/reports/crm?year=%d" % ano
    mens = client.get(base, headers=h).get_json()
    assert len(mens["vendas_ano"]["evolucao"]) == 12
    assert mens["vendas_ano"]["total"] == 7000
    fev = client.get(base + "&month=2", headers=h).get_json()
    assert fev["vendas_mes"]["total"] == 7000
    tri = client.get(base + "&period=trimestral", headers=h).get_json()
    evo = tri["vendas_ano"]["evolucao"]
    assert len(evo) == 4
    assert {e["mes"]: e["total"] for e in evo}["%d-T1" % ano] == 7000
    assert all("rotulo" in e for e in evo)
    sem = client.get(base + "&period=semestral", headers=h).get_json()
    assert len(sem["vendas_ano"]["evolucao"]) == 2
    anu = client.get(base + "&period=anual", headers=h).get_json()
    evo_a = anu["vendas_ano"]["evolucao"]
    assert len(evo_a) == 1 and evo_a[0]["total"] == 7000
    assert client.get("/api/reports/crm?period=quinzenal", headers=h).status_code == 400


def test_crm_conversao_respeita_periodo_e_declara_undated(client):
    """Pedido do dono (video 2026-10-01): o dashboard inicial somava fechados
    de todos os tempos dentro do mes. conversao agora e do periodo; fechado
    sem data (fluxo antigo / arrasto p/ ganho, que nao grava closed_at) sai da
    conta mas aparece declarado em undated."""
    import datetime as _dt
    h = _login(client)
    cid = client.post("/api/clients", headers=h,
                      json={"name": "Fechado Hoje"}).get_json()["id"]
    assert client.post(f"/api/clients/{cid}/conclude-sale", headers=h, json={}).status_code == 201
    und = client.post("/api/clients", headers=h,
                      json={"name": "Fechado Antigo", "funnel_status": "FECHAMENTO"})
    assert und.status_code == 201, und.get_data(as_text=True)

    crm = client.get("/api/reports/crm", headers=h).get_json()
    conv = crm["conversao"]
    assert conv["total_fechamentos"] == 1, conv
    assert conv["undated"] == 1, conv
    assert conv["total_clientes"] == 2, conv
    assert conv["taxa"] == 50.0, conv

    fp = crm["fechamentos_periodo"]
    assert fp["qtd"] == 1 and fp["undated"] == 1, fp
    assert fp["itens"][0]["origem"] == "crm", fp
    assert fp["itens"][0]["name"] == "Fechado Hoje", fp

    # mes antigo vazio: nada do periodo, undated continua declarado
    vazio = client.get("/api/reports/crm?year=2001&month=1", headers=h).get_json()
    assert vazio["conversao"]["total_fechamentos"] == 0, vazio["conversao"]
    assert vazio["conversao"]["undated"] == 1, vazio["conversao"]
    assert vazio["fechamentos_periodo"]["qtd"] == 0


def test_crm_fechamentos_periodo_une_sale_e_crm_sem_dobrar(client):
    """Gerar venda grava Sale + closed_at juntos: o drill-down conta uma vez
    (a Sale vence o CRM no dedup por cliente)."""
    import datetime as _dt
    h = _login(client)
    hoje = _dt.date.today()
    cid = client.post("/api/clients", headers=h,
                      json={"name": "Cliente Gerar"}).get_json()["id"]
    r = client.post("/api/sales", headers=h, json={
        "client_id": cid, "total_value": 3000, "down_payment": 3000,
        "installments": 0, "installment_value": 0, "installments_due": [],
        "sale_date": hoje.isoformat(), "environments": [],
    })
    assert r.status_code == 201, r.get_data(as_text=True)
    crm = client.get("/api/reports/crm", headers=h).get_json()
    fp = crm["fechamentos_periodo"]
    assert fp["qtd"] == 1, fp
    assert fp["itens"][0]["origem"] == "sale", fp
    assert fp["itens"][0]["name"] == "Cliente Gerar", fp
    assert fp["valor_total"] == 3000, fp
    assert crm["vendas_mes"]["qtd"] == 1
    assert len(crm["vendas_mes"]["itens"]) == 1, crm["vendas_mes"]
    assert crm["vendas_ano"]["qtd"] == 1
    assert len(crm["vendas_ano"]["itens"]) == 1, crm["vendas_ano"]


def _brl_num(txt):
    return float(str(txt).replace("R$", "").replace(".", "").replace(",", ".").strip())


def test_cash_flow_periodo_trimestral_e_default_mensal(client):
    """Fluxo de caixa aceita ?period= estilo DRE; default mensal inalterado."""
    import datetime as _dt
    h = _login(client)
    ano = _dt.date.today().year
    for dia, tipo, valor in (("02-10", "ENTRADA", 1000), ("05-20", "SAIDA", 200)):
        r = client.post("/api/financial", headers=h, json={
            "description": "CF %s" % tipo, "type": tipo, "category": "Teste",
            "amount": valor, "date": "%d-%s" % (ano, dia), "status": "PAGO"})
        assert r.status_code == 201, r.get_data(as_text=True)
    base = "/api/reports/cash-flow?year=%d" % ano
    mens = client.get(base, headers=h).get_json()
    assert len(mens["rows"]) == 12, len(mens["rows"])
    assert mens["filters_applied"]["period"] == "mensal"
    assert mens["rows"][1]["month"] == "2 - Fevereiro", mens["rows"][1]
    assert _brl_num(mens["rows"][1]["income"]) == 1000
    tri = client.get(base + "&period=trimestral", headers=h).get_json()
    assert len(tri["rows"]) == 4, tri["rows"]
    assert tri["rows"][0]["month"] == "1º Trimestre", tri["rows"][0]
    assert _brl_num(tri["rows"][0]["income"]) == 1000
    assert _brl_num(tri["rows"][0]["outcome"]) == 0
    assert _brl_num(tri["rows"][1]["outcome"]) == 200
    sem = client.get(base + "&period=semestral", headers=h).get_json()
    assert len(sem["rows"]) == 2
    assert sem["rows"][0]["month"] == "1º Semestre"
    assert _brl_num(sem["rows"][0]["income"]) == 1000
    anu = client.get(base + "&period=anual", headers=h).get_json()
    assert len(anu["rows"]) == 1
    assert _brl_num(anu["rows"][0]["income"]) == 1000
    assert _brl_num(anu["rows"][0]["outcome"]) == 200
    assert client.get(base + "&period=quinzenal", headers=h).status_code == 400
