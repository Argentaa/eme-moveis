"""Cobertura: login, clients, projects, financial, stock e calendar CRUD."""
import os

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
    assert "resultado_liquido" in r.get_json()
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
    assert client.delete(f"/api/clients/{cid}", headers=h).status_code == 200
    with client.application.app_context():
        from app.models.models import Attachment as AttModel, Campaign as CampModel, Interaction as IntModel, LeadSource as SrcModel
        assert db.session.get(IntModel, inter.id) is None      # cascade do banco
        assert db.session.get(AttModel, att.id) is None        # cascade do banco
        assert db.session.get(SrcModel, src.id) is not None    # tabela independente do cliente
        assert db.session.get(CampModel, camp.id) is not None  # tabela independente do cliente


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
    assert Config.MAX_CONTENT_LENGTH == 25 * 1024 * 1024
    assert Config.UPLOAD_DIR
    assert client.application.config["MAX_CONTENT_LENGTH"] == 25 * 1024 * 1024


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
