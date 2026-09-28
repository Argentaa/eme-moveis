"""Propostas comerciais: CRUD, PDF e envio por WhatsApp.

A proposta e o documento que o vendedor manda ao cliente — ate agora isso vivia
fora do ERP. O total NUNCA vem do cliente da API: e sempre recalculado da soma
dos itens, para nao existir proposta cujo valor nao bate com o que esta escrito.

Envio por WhatsApp: usa a Evolution API quando ela esta configurada em
app_settings. Quando nao esta (ou falha), a resposta continua 200 e traz o link
`wa.me` pronto — o vendedor nunca fica sem como enviar. O canal realmente usado
fica gravado em `sent_channel`; o fallback NAO marca ENVIADA, porque abrir o
link nao prova que a mensagem saiu.
"""
import io
import json
from datetime import date
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from flask import Blueprint, g, jsonify, request, send_file

from app.helpers import body_json, num, parse_date
from app.auth import token_required
from app.extensions import db
from app.models.models import AppSetting, Client, Proposal, ProposalItem, utcnow

bp = Blueprint("proposals", __name__)

STATUSES = ("RASCUNHO", "ENVIADA", "ACEITA", "RECUSADA")
SETTING_KEYS = ("evolution_url", "evolution_key", "evolution_instance",
                # Fase 8: dias apos a entrega em que o pos-venda agenda contato
                # automatico (ex.: "7,30"). Editavel na aba Agenda de pos-venda.
                "posvenda_followup_days")
# chaves que nunca voltam inteiras na leitura
SECRET_KEYS = ("evolution_key",)


def _username():
    return g.current_user.username if hasattr(g, "current_user") else ""


def _so_digitos(valor):
    return "".join(ch for ch in str(valor or "") if ch.isdigit())


def _com_pais(digitos):
    """Numero no formato do wa.me: DDD + numero, com 55 na frente."""
    if not digitos:
        return ""
    if digitos.startswith("55") and len(digitos) >= 12:
        return digitos
    return "55" + digitos


def _next_number():
    """PROP-<ano>-<seq>: sequencial por ano, contado do que ja existe.

    Contar do banco (em vez de guardar um contador) evita numero duplicado se
    uma proposta for excluida — o proximo continua depois do maior que sobrou.
    """
    ano = date.today().year
    prefixo = f"PROP-{ano}-"
    existentes = db.session.query(Proposal.number).filter(
        Proposal.number.like(prefixo + "%")).all()
    maior = 0
    for (n,) in existentes:
        try:
            maior = max(maior, int(str(n).rsplit("-", 1)[1]))
        except (ValueError, IndexError):
            continue
    return f"{prefixo}{maior + 1:04d}"


def _aplicar_itens(proposal, itens):
    """Recria os itens e recalcula o total a partir deles."""
    for antigo in list(proposal.items):
        db.session.delete(antigo)
    proposal.items = []
    for pos, it in enumerate(itens or []):
        desc = (it.get("description") or "").strip()
        if not desc:
            continue  # item sem descricao nao existe
        proposal.items.append(ProposalItem(
            description=desc[:255],
            quantity=it.get("quantity") or 0,
            unit_price=it.get("unit_price") or 0,
            position=pos,
        ))
    proposal.total_value = proposal.computed_total


def _mensagem(p, cliente):
    linhas = [f"*{p.number}* — Orçamento EME Móveis", ""]
    linhas.append(f"Cliente: {cliente.name if cliente else '—'}")
    linhas.append("")
    for i in p.items:
        linhas.append(f"• {i.description} — {i.quantity:g} x "
                      f"R$ {num(i.unit_price):,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        linhas[-1] += f" = R$ {i.subtotal:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    linhas.append("")
    linhas.append(f"*Total: R$ {num(p.total_value):,.2f}*".replace(",", "X").replace(".", ",").replace("X", "."))
    if p.valid_until:
        linhas.append(f"Válida até {p.valid_until.strftime('%d/%m/%Y')}")
    if p.notes:
        linhas += ["", p.notes]
    return "\n".join(linhas)


# ── CRUD ──────────────────────────────────────────────────────────────
@bp.get("/api/proposals")
@token_required()
def list_proposals():
    q = db.session.query(Proposal)
    status = (request.args.get("status") or "").strip().upper()
    if status:
        q = q.filter(Proposal.status == status)
    client_id = request.args.get("client_id")
    if client_id:
        q = q.filter(Proposal.client_id == client_id)
    propostas = q.order_by(Proposal.created_at.desc()).all()
    return jsonify([p.to_dict() for p in propostas])


@bp.post("/api/proposals")
@token_required()
def create_proposal():
    data = body_json()
    client_id = data.get("client_id")
    if not client_id:
        return jsonify({"detail": "client_id e obrigatorio"}), 400
    if not db.session.get(Client, client_id):
        return jsonify({"detail": "Cliente nao encontrado"}), 404

    valid_until = None
    if data.get("valid_until"):
        try:
            valid_until = parse_date(data.get("valid_until"))
        except ValueError:
            return jsonify({"detail": "valid_until invalida"}), 400

    p = Proposal(
        number=_next_number(),
        client_id=client_id,
        project_id=data.get("project_id") or None,
        status="RASCUNHO",
        total_value=0,
        valid_until=valid_until,
        notes=(data.get("notes") or "").strip(),
        created_by=_username(),
        created_at=utcnow(),
    )
    db.session.add(p)
    db.session.flush()
    _aplicar_itens(p, data.get("items"))
    db.session.commit()
    return jsonify(p.to_dict()), 201


@bp.get("/api/proposals/<proposal_id>")
@token_required()
def get_proposal(proposal_id):
    p = db.session.get(Proposal, proposal_id)
    if not p:
        return jsonify({"detail": "Proposta nao encontrada"}), 404
    return jsonify(p.to_dict())


@bp.put("/api/proposals/<proposal_id>")
@token_required()
def update_proposal(proposal_id):
    p = db.session.get(Proposal, proposal_id)
    if not p:
        return jsonify({"detail": "Proposta nao encontrada"}), 404
    data = body_json()

    if "client_id" in data:
        if not db.session.get(Client, data.get("client_id")):
            return jsonify({"detail": "Cliente nao encontrado"}), 404
        p.client_id = data.get("client_id")

    if "status" in data:
        st = str(data.get("status") or "").strip().upper()
        if st not in STATUSES:
            return jsonify({"detail": f"status deve ser um de {', '.join(STATUSES)}"}), 400
        p.status = st

    if "valid_until" in data:
        if not data.get("valid_until"):
            p.valid_until = None
        else:
            try:
                p.valid_until = parse_date(data.get("valid_until"))
            except ValueError:
                return jsonify({"detail": "valid_until invalida"}), 400

    if "project_id" in data:
        p.project_id = data.get("project_id") or None

    if "notes" in data:
        p.notes = (data.get("notes") or "").strip()

    if "items" in data:
        _aplicar_itens(p, data.get("items"))

    db.session.commit()
    return jsonify(p.to_dict())


@bp.delete("/api/proposals/<proposal_id>")
@token_required()
def delete_proposal(proposal_id):
    p = db.session.get(Proposal, proposal_id)
    if not p:
        return jsonify({"detail": "Proposta nao encontrada"}), 404
    db.session.delete(p)
    db.session.commit()
    return jsonify({"ok": True})


# ── PDF ───────────────────────────────────────────────────────────────
def _fmt(v):
    return f"R$ {float(v or 0):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


@bp.get("/api/proposals/<proposal_id>/pdf")
@token_required()
def proposal_pdf(proposal_id):
    p = db.session.get(Proposal, proposal_id)
    if not p:
        return jsonify({"detail": "Proposta nao encontrada"}), 404

    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)

    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, 800, "EME MOVEIS")
    c.setFont("Helvetica", 10)
    c.drawString(50, 782, f"Proposta {p.number}")

    y = 750
    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, y, "Cliente")
    c.setFont("Helvetica", 10)
    y -= 16
    c.drawString(50, y, (p.client.name if p.client else "—")[:80])
    y -= 14
    if p.client and getattr(p.client, "phone", None):
        c.drawString(50, y, f"Telefone: {p.client.phone}")
        y -= 14
    c.drawString(50, y, f"Emitida em {p.created_at.strftime('%d/%m/%Y') if p.created_at else '—'}")
    y -= 14
    if p.valid_until:
        c.drawString(50, y, f"Valida ate {p.valid_until.strftime('%d/%m/%Y')}")
        y -= 14

    y -= 12
    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, y, "Descricao")
    c.drawString(330, y, "Qtd")
    c.drawString(390, y, "Unitario")
    c.drawString(470, y, "Subtotal")
    y -= 6
    c.line(50, y, 545, y)
    y -= 14
    c.setFont("Helvetica", 9)
    for i in p.items:
        c.drawString(50, y, i.description[:58])
        c.drawString(330, y, f"{num(i.quantity):g}")
        c.drawString(390, y, _fmt(i.unit_price))
        c.drawString(470, y, _fmt(i.subtotal))
        y -= 13
        if y < 70:
            c.showPage()
            y = 800
            c.setFont("Helvetica", 9)

    y -= 8
    c.line(50, y, 545, y)
    y -= 18
    c.setFont("Helvetica-Bold", 12)
    c.drawString(390, y, f"TOTAL: {_fmt(p.total_value)}")

    if p.notes:
        y -= 30
        c.setFont("Helvetica-Oblique", 9)
        for linha in str(p.notes).splitlines()[:6]:
            c.drawString(50, y, linha[:100])
            y -= 12

    c.showPage()
    c.save()
    buf.seek(0)
    return send_file(buf, mimetype="application/pdf", as_attachment=True,
                     download_name=f"{p.number}.pdf")


# ── envio por WhatsApp ────────────────────────────────────────────────
@bp.post("/api/proposals/<proposal_id>/send-whatsapp")
@token_required()
def send_whatsapp(proposal_id):
    p = db.session.get(Proposal, proposal_id)
    if not p:
        return jsonify({"detail": "Proposta nao encontrada"}), 404

    telefone = _so_digitos(getattr(p.client, "phone", "") if p.client else "")
    if not telefone:
        return jsonify({"detail": "Cliente sem telefone cadastrado"}), 400

    mensagem = _mensagem(p, p.client)
    cfg = {s.key: (s.value or "") for s in db.session.query(AppSetting).all()}
    url = cfg.get("evolution_url", "").rstrip("/")
    chave = cfg.get("evolution_key", "")
    instancia = cfg.get("evolution_instance", "")

    if url and chave and instancia:
        # urllib (stdlib) em vez de requests: a imagem do container nao tem
        # requests e uma dependencia nova so para UM POST nao se paga.
        try:
            corpo = json.dumps({"number": _com_pais(telefone), "text": mensagem}).encode()
            pedido = Request(f"{url}/message/sendText/{instancia}", data=corpo, method="POST")
            pedido.add_header("apikey", chave)
            pedido.add_header("Content-Type", "application/json")
            with urlopen(pedido, timeout=8) as resp:
                status = getattr(resp, "status", 200)
            if status < 300:
                p.status = "ENVIADA"
                p.sent_at = utcnow()
                p.sent_channel = "WHATSAPP"
                db.session.commit()
                return jsonify({"sent": True, "channel": "WHATSAPP", "detail": "",
                                "fallback_wa_me": None, "proposal": p.to_dict()})
            erro = f"Evolution API respondeu {status}"
        except HTTPError as e:
            erro = f"Evolution API respondeu {e.code}"
        except (URLError, OSError, ValueError) as e:
            erro = f"falha ao falar com a Evolution API ({type(e).__name__})"
    else:
        erro = "Evolution API nao configurada"

    # Fallback: o vendedor nunca fica sem enviar. Nao marca ENVIADA porque abrir
    # o link nao prova que a mensagem saiu.
    return jsonify({
        "sent": False, "channel": None, "detail": erro,
        "fallback_wa_me": f"https://wa.me/{_com_pais(telefone)}?text={quote(mensagem)}",
        "proposal": p.to_dict(),
    })


# ── configuracao (ADMIN) ──────────────────────────────────────────────
def _mascarar(key, value):
    if key in SECRET_KEYS and value:
        return "•" * 8 + value[-4:] if len(value) > 4 else "•" * 8
    return value or ""


@bp.get("/api/settings")
@token_required(roles=["ADMIN"])
def list_settings():
    atuais = {s.key: s for s in db.session.query(AppSetting).all()}
    return jsonify([
        {"key": k,
         "value": _mascarar(k, atuais[k].value if k in atuais else ""),
         "configured": bool(atuais.get(k) and atuais[k].value),
         "secret": k in SECRET_KEYS}
        for k in SETTING_KEYS
    ])


@bp.put("/api/settings")
@token_required(roles=["ADMIN"])
def update_settings():
    data = body_json()
    salvos = []
    for k in SETTING_KEYS:
        if k not in data:
            continue
        valor = (data.get(k) or "").strip()
        # valor mascarado que voltou igual nao sobrescreve o que ja existe
        if k in SECRET_KEYS and valor.startswith("•"):
            continue
        s = db.session.query(AppSetting).filter(AppSetting.key == k).first()
        if not s:
            s = AppSetting(key=k, updated_at=utcnow())
            db.session.add(s)
        s.value = valor
        s.updated_at = utcnow()
        salvos.append(k)
    db.session.commit()
    return jsonify({"saved": salvos})
