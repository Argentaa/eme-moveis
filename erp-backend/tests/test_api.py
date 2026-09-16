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

    # CENARIO CONCLUIDO: status CONCLUIDO com actual_end_date preenchido -> CONCLUIDO independente do prazo
    r = client.post("/api/projects", headers=h, json={
        "title": "Projeto Concluido", "client_id": cid, "status": "CONCLUIDO",
        "deadline": deadline_yesterday, "actual_end_date": start_iso
    })
    assert r.status_code == 201, r.get_data(as_text=True)
    j = r.get_json()
    assert j["actual_end_date"] == start_iso
    assert j["deadline_status"] == "CONCLUIDO"

    # Atualizacao via PUT para CONCLUIDO com actual_end_date -> CONCLUIDO
    r = client.put(f"/api/projects/{pid}", headers=h, json={"status": "CONCLUIDO", "actual_end_date": start_iso})
    assert r.status_code == 200, r.get_data(as_text=True)
    upd = r.get_json()
    assert upd["actual_end_date"] == start_iso
    assert upd["deadline_status"] == "CONCLUIDO"
    # garantir que GET reflete CONCLUIDO
    r = client.get(f"/api/projects/{pid}", headers=h)
    assert r.get_json()["deadline_status"] == "CONCLUIDO"


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

    # Asserts no json: summary contem pelo menos os labels/valores esperados
    total_m2_item = find_summary("Total m2") or find_summary("m2")
    assert total_m2_item is not None, f"summary sem Total m2: {summary}"
    val_m2 = parse_val_to_float(total_m2_item.get("value"))
    assert val_m2 is not None and abs(val_m2 - expected_total_m2) < 0.01, f"Total m2 {val_m2} != {expected_total_m2} summary={total_m2_item}"

    total_amb = find_summary("Total Ambientes")
    assert total_amb is not None, f"summary sem Total Ambientes: {summary}"
    assert total_amb.get("value") == str(expected_total_ambientes) or parse_val_to_float(total_amb.get("value")) == expected_total_ambientes

    horas_prod_item = find_summary("Horas Produtivas")
    assert horas_prod_item is not None, f"summary sem Horas Produtivas: {summary}"
    val_prod = parse_val_to_float(horas_prod_item.get("value"))
    assert val_prod is not None and abs(val_prod - expected_horas_prod) < 0.01, f"Horas Produtivas {val_prod} != {expected_horas_prod}"

    horas_improd_item = find_summary("Horas Improdutivas")
    assert horas_improd_item is not None, f"summary sem Horas Improdutivas: {summary}"
    val_improd = parse_val_to_float(horas_improd_item.get("value"))
    assert val_improd is not None and abs(val_improd - expected_horas_improd) < 0.01, f"Horas Improdutivas {val_improd} != {expected_horas_improd}"

    total_horas_item = find_summary("Total Horas")
    assert total_horas_item is not None, f"summary sem Total Horas: {summary}"
    val_total_horas = parse_val_to_float(total_horas_item.get("value"))
    assert val_total_horas is not None and abs(val_total_horas - expected_total_horas) < 0.01, f"Total Horas {val_total_horas} != {expected_total_horas}"

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
