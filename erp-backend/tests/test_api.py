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
