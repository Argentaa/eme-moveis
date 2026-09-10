"""Testes de API do site-backend (Flask). Banco sqlite isolado por sessão de teste."""
import io
import os
import tempfile

import pytest

os.environ.setdefault("SITE_JWT_SECRET", "segredo-de-teste-com-32-caracteres!!")
os.environ.setdefault("SITE_ADMIN_USER", "admin_teste")
os.environ.setdefault("SITE_ADMIN_PASS", "SenhaForte123!")

_tmp = tempfile.mkdtemp(prefix="site-uploads-")
os.environ["UPLOAD_DIR"] = _tmp
_db_file = os.path.join(tempfile.mkdtemp(prefix="site-db-"), "test.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_db_file}"

from app import create_app  # noqa: E402


@pytest.fixture()
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def _login(client) -> str:
    res = client.post(
        "/api/auth/login",
        json={"username": "admin_teste", "password": "SenhaForte123!"},
    )
    assert res.status_code == 200, res.get_data(as_text=True)
    body = res.get_json()
    assert body["success"] is True
    assert body["token"] and body["token"] != "eme-moveis-secret-super-auth-token-key-2026"
    assert body["user"]["username"] == "admin_teste"
    return body["token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_login_invalido_retorna_401(client):
    res = client.post("/api/auth/login", json={"username": "admin_teste", "password": "errada"})
    assert res.status_code == 401


def test_health_e_contact_info_publicos(client):
    assert client.get("/api/health").status_code == 200
    res = client.get("/api/contact-info")
    assert res.status_code == 200
    body = res.get_json()
    assert "whatsapp" in body and "instagram" in body


def test_projects_publico_e_crud_com_auth(client):
    # GET público
    assert client.get("/api/projects").status_code == 200
    # POST sem auth -> 401
    res = client.post("/api/projects", json={"title": "X", "category": "Y", "image": "Z"})
    assert res.status_code == 401

    token = _login(client)
    payload = {
        "title": "Projeto Teste",
        "category": "Cozinha",
        "image": "/uploads/projetos/a.jpg",
        "album": ["/uploads/projetos/a.jpg", "/uploads/projetos/b.jpg"],
        "description": "Descrição de teste",
    }
    res = client.post("/api/projects", json=payload, headers=_auth(token))
    assert res.status_code == 201, res.get_data(as_text=True)
    created = res.get_json()
    assert created["mainImage"] == payload["image"]
    assert created["album"] == payload["album"]
    pid = created["id"]

    res = client.put(
        f"/api/projects/{pid}",
        json={**payload, "title": "Projeto Atualizado"},
        headers=_auth(token),
    )
    assert res.status_code == 200
    assert res.get_json()["success"] is True

    res = client.delete(f"/api/projects/{pid}", headers=_auth(token))
    assert res.status_code == 200
    assert res.get_json()["success"] is True

    res = client.delete(f"/api/projects/{pid}", headers=_auth(token))
    assert res.status_code == 404


def test_timeline_crud(client):
    assert client.get("/api/timeline").status_code == 200
    token = _login(client)
    res = client.post(
        "/api/timeline",
        json={"year": "2025", "title": "Marco", "description": "Desc", "image": "img.jpg"},
        headers=_auth(token),
    )
    assert res.status_code == 201, res.get_data(as_text=True)
    tid = res.get_json()["id"]

    res = client.put(
        f"/api/timeline/{tid}",
        json={"year": "2025", "title": "Marco 2", "description": "Desc 2"},
        headers=_auth(token),
    )
    assert res.status_code == 200

    res = client.delete(f"/api/timeline/{tid}", headers=_auth(token))
    assert res.status_code == 200


def _png_bytes() -> bytes:
    # PNG mínimo válido (1x1).
    return (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00"
        b"\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
    )


def test_upload_rejeitado_sem_auth_e_valido_com_auth(client):
    # Sem auth -> 401
    res = client.post(
        "/api/upload?folder=projetos",
        data={"file": (io.BytesIO(_png_bytes()), "foto.png")},
        content_type="multipart/form-data",
    )
    assert res.status_code == 401

    token = _login(client)
    # Tipo inválido -> 400
    res = client.post(
        "/api/upload?folder=projetos",
        data={"file": (io.BytesIO(b"nao-imagem"), "doc.txt")},
        headers=_auth(token),
        content_type="multipart/form-data",
    )
    assert res.status_code == 400

    # Pasta inválida -> 400
    res = client.post(
        "/api/upload?folder=invalida",
        data={"file": (io.BytesIO(_png_bytes()), "foto.png")},
        headers=_auth(token),
        content_type="multipart/form-data",
    )
    assert res.status_code == 400

    # Válido -> {success, filePath}
    res = client.post(
        "/api/upload?folder=projetos",
        data={"file": (io.BytesIO(_png_bytes()), "foto.png")},
        headers=_auth(token),
        content_type="multipart/form-data",
    )
    assert res.status_code == 200, res.get_data(as_text=True)
    body = res.get_json()
    assert body["success"] is True
    assert body["filePath"].startswith("/uploads/projetos/")
    # Arquivo servido em /uploads
    rel = body["filePath"].removeprefix("/uploads/")
    assert client.get(f"/uploads/{rel}").status_code == 200


def test_settings_publico_e_update_com_auth(client):
    assert client.get("/api/settings").status_code == 200
    token = _login(client)
    res = client.post(
        "/api/settings",
        json={
            "heroImage": "/uploads/site-assets/hero.png",
            "aboutImage": "/uploads/site-assets/about.png",
            "whatsapp": "55999999999",
            "instagram": "https://instagram.com/teste",
            "address": {"cidade": "Teste/RS"},
        },
        headers=_auth(token),
    )
    assert res.status_code == 200
    body = client.get("/api/settings").get_json()
    assert body["heroImage"] == "/uploads/site-assets/hero.png"
    assert body["whatsapp"] == "55999999999"
    contact = client.get("/api/contact-info").get_json()
    assert contact["whatsapp"] == "55999999999"
    assert contact["instagram"] == "https://instagram.com/teste"


def test_update_credentials(client):
    token = _login(client)
    res = client.post(
        "/api/auth/update-credentials",
        json={"username": "admin_novo"},
        headers=_auth(token),
    )
    assert res.status_code == 200
    # Login antigo falha, novo funciona
    assert (
        client.post(
            "/api/auth/login",
            json={"username": "admin_teste", "password": "SenhaForte123!"},
        ).status_code
        == 401
    )
    res = client.post(
        "/api/auth/login",
        json={"username": "admin_novo", "password": "SenhaForte123!"},
    )
    assert res.status_code == 200
    # Restaura para não afetar outros testes (ordem alfabética: este roda por último
    # entre os que usam login? garante restauração de qualquer forma)
    new_token = res.get_json()["token"]
    res = client.post(
        "/api/auth/update-credentials",
        json={"username": "admin_teste"},
        headers=_auth(new_token),
    )
    assert res.status_code == 200
