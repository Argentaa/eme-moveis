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
    assert lst[0]["title"] == "Novo: Fonte do Lead"  # ordena por entry_date desc
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
    assert body["title"] == "Fluxo de Caixa Mensal"
    jan = next(row for row in body["rows"] if row["month"] == "1 - Janeiro")
    fev = next(row for row in body["rows"] if row["month"] == "2 - Fevereiro")
    assert jan["income"] == "R$ 1.000,00" and jan["outcome"] == "R$ 300,00" and jan["balance"] == "R$ 700,00"
    assert jan["accumulated"] == "R$ 700,00"
    assert fev["income"] == "R$ 0,00" and fev["outcome"] == "R$ 200,00" and fev["accumulated"] == "R$ 500,00"
    assert sum(1 for row in body["rows"] if "R$ 0,00" in row["income"]) == 11  # 12 meses, so janeiro tem entrada PAGO


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
