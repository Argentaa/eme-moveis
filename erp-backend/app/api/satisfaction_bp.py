"""Pesquisa de satisfacao pos-entrega (Fase 8).

Fluxo: o usuario (ou a automacao) envia a pesquisa pelo botao no Pos-venda —
`POST /api/satisfaction` cria o registro com `sent_at`. A resposta pode chegar
de dois jeitos: digitada direto aqui (score/comment junto no POST) ou via
WhatsApp mais tarde (`POST /api/satisfaction/<id>/answer`). O resumo alimenta
a aba de resultados ("Pesquisa de satisfacao" do plano, 8.3).

Regra de data: `answered_at` e gravado na resposta e nunca reescrito;
reexecutar o POST do mesmo envio nao duplica (mesmo client_id+project_id no
mesmo dia nao cria outra linha).
"""
from datetime import date, datetime
import json
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from flask import Blueprint, jsonify, request

from app.helpers import body_json, iso
from app.auth import token_required
from app.extensions import db
from app.models.models import AppSetting, SatisfactionSurvey, utcnow

bp = Blueprint("satisfaction", __name__)


def _dup_check(client_id, project_id, ticket_id):
    hoje = date.today()
    q = SatisfactionSurvey.query.filter_by(client_id=client_id)
    if project_id:
        q = q.filter_by(project_id=project_id)
    if ticket_id:
        q = q.filter_by(ticket_id=ticket_id)
    for s in q.all():
        if s.sent_at.date() == hoje:
            return s
    return None


@bp.get("/api/satisfaction")
@token_required()
def list_surveys():
    rows = SatisfactionSurvey.query.order_by(SatisfactionSurvey.sent_at.desc()).all()
    return jsonify([s.to_dict() for s in rows])


@bp.post("/api/satisfaction")
@token_required()
def create_survey():
    data = body_json() or {}
    client_id = (data.get("client_id") or "").strip()
    if not client_id:
        return jsonify({"error": "client_id obrigatorio"}), 400
    project_id = (data.get("project_id") or "").strip() or None
    ticket_id = (data.get("ticket_id") or "").strip() or None
    score = data.get("score")
    comment = (data.get("comment") or "").strip() or None

    duplicado = _dup_check(client_id, project_id, ticket_id)
    if duplicado:
        return jsonify(duplicado.to_dict()), 200

    if score is not None:
        try:
            score = int(score)
        except (TypeError, ValueError):
            return jsonify({"error": "score deve ser 1 a 5"}), 400
        if score < 1 or score > 5:
            return jsonify({"error": "score deve ser 1 a 5"}), 400

    now = utcnow()
    survey = SatisfactionSurvey(
        client_id=client_id,
        project_id=project_id,
        ticket_id=ticket_id,
        score=score,
        comment=comment,
        sent_at=now,
        answered_at=now if score is not None else None,
    )
    db.session.add(survey)
    db.session.commit()
    return jsonify(survey.to_dict()), 201


@bp.post("/api/satisfaction/<survey_id>/answer")
@token_required()
def answer_survey(survey_id):
    survey = SatisfactionSurvey.query.get(survey_id)
    if not survey:
        return jsonify({"error": "pesquisa nao encontrada"}), 404
    data = body_json() or {}
    if data.get("score") is not None:
        try:
            score = int(data.get("score"))
        except (TypeError, ValueError):
            return jsonify({"error": "score deve ser 1 a 5"}), 400
        if score < 1 or score > 5:
            return jsonify({"error": "score deve ser 1 a 5"}), 400
        survey.score = score
        if survey.answered_at is None:
            survey.answered_at = utcnow()
    if data.get("comment"):
        survey.comment = (survey.comment or "") + (("\n" if survey.comment else "") + str(data["comment"]).strip())
    db.session.commit()
    return jsonify(survey.to_dict())


@bp.get("/api/satisfaction/summary")
@token_required()
def satisfaction_summary():
    surveys = SatisfactionSurvey.query.order_by(SatisfactionSurvey.sent_at.asc()).all()
    total = len(surveys)
    answered = [s for s in surveys if s.answered_at is not None]
    scores = [s.score for s in answered if s.score is not None]
    media = round(sum(scores) / len(scores), 2) if scores else 0
    dist = {str(i): sum(1 for s in scores if s == i) for i in range(1, 6)}
    return jsonify({
        "total": total,
        "answered": len(answered),
        "response_rate": round(len(answered) / total * 100, 1) if total else 0,
        "average": media,
        "distribution": dist,
        "recent": [s.to_dict() for s in surveys[-8:][::-1]],
    })


def _so_digitos(valor):
    return "".join(ch for ch in str(valor or "") if ch.isdigit())


def _com_pais(telefone):
    d = _so_digitos(telefone)
    if d and not d.startswith("55"):
        d = "55" + d
    return d


# ── envio por WhatsApp (reusa o fluxo da proposta, 4.3) ────────────────
@bp.post("/api/satisfaction/<survey_id>/send-whatsapp")
@token_required()
def send_survey_whatsapp(survey_id):
    """Envia a pesquisa por WhatsApp via Evolution API, com fallback wa.me.

    Mesmo contrato da proposta: `sent=True` so quando a Evolution confirma;
    sem configuracao (ou falha), 200 com `fallback_wa_me` para o vendedor
    enviar na mao. O envio nao marca resposta — so atualiza `sent_at`.
    """
    survey = db.session.get(SatisfactionSurvey, survey_id)
    if not survey:
        return jsonify({"detail": "Pesquisa nao encontrada"}), 404
    telefone = _so_digitos(getattr(survey.client, "phone", "") if survey.client else "")
    if not telefone:
        return jsonify({"detail": "Cliente sem telefone cadastrado"}), 400
    nome = survey.client.name if survey.client else "cliente"
    projeto = f' sobre "{survey.project.title}"' if survey.project else ""
    mensagem = (
        f"Olá {nome}! Aqui é da EME Móveis. "
        f"Gostaríamos de saber como ficou{projeto} — "
        "responda com uma nota de 1 a 5 e, se quiser, um comentário. Obrigado!"
    )
    cfg = {s.key: (s.value or "") for s in db.session.query(AppSetting).all()}
    url = cfg.get("evolution_url", "").rstrip("/")
    chave = cfg.get("evolution_key", "")
    instancia = cfg.get("evolution_instance", "")

    if url and chave and instancia:
        try:
            corpo = json.dumps({"number": _com_pais(telefone), "text": mensagem}).encode()
            pedido = Request(f"{url}/message/sendText/{instancia}", data=corpo, method="POST")
            pedido.add_header("apikey", chave)
            pedido.add_header("Content-Type", "application/json")
            with urlopen(pedido, timeout=8) as resp:
                status = getattr(resp, "status", 200)
            if status < 300:
                survey.sent_at = utcnow()
                db.session.commit()
                return jsonify({"sent": True, "channel": "WHATSAPP", "detail": "",
                                "fallback_wa_me": None, "survey": survey.to_dict()})
            erro = f"Evolution API respondeu {status}"
        except HTTPError as e:
            erro = f"Evolution API respondeu {e.code}"
        except (URLError, OSError, ValueError) as e:
            erro = f"falha ao falar com a Evolution API ({type(e).__name__})"
    else:
        erro = "Evolution API nao configurada"

    return jsonify({
        "sent": False, "channel": None, "detail": erro,
        "fallback_wa_me": f"https://wa.me/{_com_pais(telefone)}?text={quote(mensagem)}",
        "survey": survey.to_dict(),
    })