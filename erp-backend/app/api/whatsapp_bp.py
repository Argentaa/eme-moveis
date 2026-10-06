"""Chat interno de WhatsApp via Evolution API (v2.3.7).

O que este blueprint faz, em ordem de uso:

1. `POST /api/whatsapp/setup` (ADMIN): guarda evolution_url + chave global +
   nome da instancia em app_settings e cria a instancia na Evolution com o
   webhook apontando para o ERP. Auto-config: ninguem digita hash na mao.
2. `GET /api/whatsapp/status`: configurado? estado real (open/close/...) e
   numero conectado. A tela consulta para mostrar desconectada/QR/conectada.
3. `GET /api/whatsapp/qr`: QR novo a cada chamada (vale ~3 min, por isso
   nunca e persistido) + pairing code.
4. `POST /api/whatsapp/webhook?token=...` (SEM login): recebe MESSAGES_UPSERT
   e grava conversa+mensagem. Token derivado via hmac da chave global —
   nada guardado no banco. fromMe=True (enviado pelo celular pareado) entra
   como direction=out — sem isso o ERP nunca mostra o que o dono mandou pelo
   celular. Ignora evento que nao seja messages.upsert, dedupa pelo id da
   Evolution (o eco do envio do ERP cai no mesmo dedupe, pois o send grava o
   provider_id retornado pela Evolution).
5. `GET /api/whatsapp/conversations` + `.../<id>/messages`: o chat le daqui.
6. `POST /api/whatsapp/conversations/<id>/send`: texto (JSON) ou midia
   (multipart file + caption). Sai via sendText/sendMedia e grava como out
   (com o provider_id da Evolution, p/ o eco do webhook dedupar).
   Arquivo respeita o mesmo teto de upload do ERP (413 honesto acima).
7. `POST /api/whatsapp/conversations/<id>/sync`: puxa o historico da
   Evolution (findMessages) e grava o que falta — e o botao "Sincronizar" da
   tela, p/ usar celular e ERP juntos sem perder mensagem.

Contrato v2 real (nao o da doc v1): connect e GET, hash vem no create,
fetchInstances usa name/connectionStatus/ownerJid. Envio de midia tenta o
formato primario e cai para o variante em 400 (builds divergem).
"""
import base64
import hashlib
import hmac
import io
import json
import os
import uuid
from datetime import datetime, timezone

from flask import Blueprint, current_app, g, jsonify, request, send_file
from werkzeug.utils import secure_filename

from app.helpers import body_json
from app.auth import token_required
from app.extensions import db
from app.models.models import (
    AppSetting, Client, WhatsappConversation, WhatsappInstance,
    WhatsappMessage, utcnow,
)

# urllib (stdlib): a imagem do container nao tem requests, mesma decisao das
# propostas. Importado como modulo para os testes mockarem urlopen.
import urllib.request as _urlreq
import urllib.error as _urlerr

bp = Blueprint("whatsapp", __name__)

DEFAULT_INSTANCE = "eme-moveis"
DEFAULT_WEBHOOK_BASE = "https://erp.ememoveis.com.br"
MEDIA_KINDS = ("image", "audio", "video", "document")
TEXT_KEYS = ("conversation",)


def _cfg():
    return {s.key: (s.value or "") for s in db.session.query(AppSetting).all()}


def _get_setting(key, default=""):
    s = db.session.query(AppSetting).filter_by(key=key).first()
    return (s.value or "") if s else default


def _set_setting(key, value):
    s = db.session.query(AppSetting).filter_by(key=key).first()
    if not s:
        s = AppSetting(key=key, updated_at=utcnow())
        db.session.add(s)
    s.value = value
    s.updated_at = utcnow()


def webhook_token(global_key, instance):
    """Token do webhook: hmac(chave_global, instancia), 32 hex. Nada no banco."""
    return hmac.new(
        (global_key or "").encode(), (instance or "").encode(), hashlib.sha256,
    ).hexdigest()[:32]


def _webhook_url(instance, global_key, base=None):
    base = (base or _get_setting("whatsapp_webhook_base", "") or DEFAULT_WEBHOOK_BASE).rstrip("/")
    return f"{base}/api/whatsapp/webhook?token={webhook_token(global_key, instance)}"


def _evo_call(method, path, global_key, body=None, timeout=15):
    """Chamada a Evolution. Devolve (status, dict). Erro de rede vira (0, {...})."""
    cfg = _cfg()
    base = (cfg.get("evolution_url") or "").rstrip("/")
    if not base or not global_key:
        return 0, {"error": "Evolution API nao configurada"}
    data = json.dumps(body).encode() if body is not None else None
    req = _urlreq.Request(base + path, data=data, method=method,
                          headers={"apikey": global_key, "Content-Type": "application/json"})
    try:
        with _urlreq.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode()
            status = getattr(resp, "status", 200)
    except _urlerr.HTTPError as e:
        try:
            raw = e.read().decode()
        except Exception:
            raw = ""
        return e.code, {"error": f"Evolution API respondeu {e.code}", "raw": raw[:300]}
    except (OSError, ValueError) as e:
        return 0, {"error": f"falha ao falar com a Evolution API ({type(e).__name__})"}
    try:
        return status, (json.loads(raw) if raw.strip() else {})
    except (ValueError, AttributeError):
        return status, {"raw": (raw or "")[:300]}


def _digits(value):
    return "".join(ch for ch in str(value or "") if ch.isdigit())


def _tail_digits(digits, n=11):
    d = _digits(digits)
    return d[-n:] if len(d) >= n else d


def _match_client_id(digits):
    """Um unico Client com este telefone -> id; zero ou >1 -> None (ambiguo)."""
    if not digits:
        return None
    tail = _tail_digits(digits)
    if not tail:
        return None
    candidatos = []
    for c in db.session.query(Client).all():
        fone = _digits(getattr(c, "phone", ""))
        if fone and (fone == digits or _tail_digits(fone) == tail or tail.endswith(_tail_digits(fone))):
            candidatos.append(c.id)
    return candidatos[0] if len(candidatos) == 1 else None


def _get_conversation(instance, digits, name=""):
    conv = (
        db.session.query(WhatsappConversation)
        .filter_by(instance=instance, phone=digits)
        .first()
    )
    if conv:
        if name and not conv.name:
            conv.name = name[:160]
        if conv.client_id is None:
            conv.client_id = _match_client_id(digits)
        return conv
    conv = WhatsappConversation(
        instance=instance, phone=digits, name=(name or "")[:160],
        client_id=_match_client_id(digits),
    )
    db.session.add(conv)
    db.session.flush()
    return conv


def _sender_digits(key, participant=None):
    raw = (key or {}).get("remoteJid", "") or (participant or "")
    local = raw.split("@")[0]
    if raw.endswith("@g.us"):
        return ""  # grupo: fora do escopo v1
    return _digits(local)


def _extract_text(message):
    """Texto da mensagem; midia devolve (kind, caption)."""
    if not isinstance(message, dict):
        return "text", ""
    if message.get("conversation"):
        return "text", str(message.get("conversation") or "")
    ext = message.get("extendedTextMessage") or {}
    if ext.get("text"):
        return "text", str(ext.get("text"))
    for kind, mkey in (("image", "imageMessage"), ("video", "videoMessage"),
                       ("audio", "audioMessage"), ("audio", "pttMessage"),
                       ("document", "documentMessage")):
        node = message.get(mkey)
        if isinstance(node, dict):
            return kind, str(node.get("caption") or "")
    return "text", ""


def _msg_time(item):
    """Data da mensagem (p/ o histórico sincronizado manter a ordem real).

    Webhook e findMessages trazem `messageTimestamp` em segundos (int, float
    ou string de dígitos). Ausente/inválido = agora.
    """
    raw = (item or {}).get("messageTimestamp")
    try:
        ts = float(raw)
    except (TypeError, ValueError):
        return utcnow()
    if ts <= 0:
        return utcnow()
    try:
        return datetime.fromtimestamp(ts, tz=timezone.utc)
    except (OverflowError, OSError, ValueError):
        return utcnow()


def _store_inbound(instance, item):
    """Grava UM messages.upsert. Devolve 'stored'|'duplicate'|'ignored'.

    fromMe=True (enviado pelo celular pareado ou eco do envio do ERP) entra
    como direction=out — sem isso, o que o dono manda pelo celular nunca
    aparece no ERP, só a resposta do cliente (bug real). O eco do envio feito
    pelo próprio ERP não duplica: o send grava o provider_id da Evolution e o
    dedupe abaixo cobre os dois sentidos. pushName do fromMe NÃO renomeia a
    conversa (é o nome do próprio dono).
    """
    key = (item or {}).get("key") or {}
    from_me = bool(key.get("fromMe"))
    digits = _sender_digits(key, (item or {}).get("participant"))
    if not digits:
        return "ignored"
    message = (item or {}).get("message") or {}
    kind, texto = _extract_text(message)
    push = "" if from_me else str((item or {}).get("pushName") or "")
    provider_id = str(key.get("id") or "")
    if provider_id:
        dup = db.session.query(WhatsappMessage).filter_by(provider_id=provider_id).first()
        if dup:
            return "duplicate"
    conv = _get_conversation(instance, digits, push)
    media_node = None
    for mkey in ("imageMessage", "videoMessage", "audioMessage", "pttMessage", "documentMessage"):
        if isinstance(message.get(mkey), dict):
            media_node = message.get(mkey)
            break
    remote_jid = str(key.get("remoteJid") or "")[:120] or None
    try:
        media_len = int((media_node or {}).get("fileLength") or 0) or None
    except (TypeError, ValueError):
        media_len = None
    row = WhatsappMessage(
        conversation_id=conv.id,
        provider_id=provider_id or None,
        remote_jid=remote_jid,
        direction="out" if from_me else "in",
        kind=kind if kind in MEDIA_KINDS or kind == "text" else "text",
        body=(texto or "")[:4000],
        media_filename=(str(media_node.get("fileName") or "")[:255] if media_node else None),
        media_mime=(str(media_node.get("mimetype") or "")[:120] if media_node else None),
        media_size=media_len,
        status="stored",
        created_at=_msg_time(item),
    )
    db.session.add(row)
    # last_message_at acompanha a mensagem mais nova. Normaliza tz: o SQLite
    # devolve naive e o utcnow/fromtimestamp gera aware — comparar direto
    # estoura TypeError.
    def _naive(dt):
        try:
            return dt.replace(tzinfo=None) if dt and dt.tzinfo else dt
        except Exception:
            return None
    if not _naive(conv.last_message_at) or (
            _naive(row.created_at) and _naive(row.created_at) >= _naive(conv.last_message_at)):
        conv.last_message_at = row.created_at
    db.session.flush()
    return "stored"


# ── setup / status / qr (ADMIN) ──────────────────────────────────────


@bp.post("/api/whatsapp/setup")
@token_required(roles=["ADMIN"])
def setup_instance():
    """Auto-config: guarda URL+chave+instancia e cria a instancia na Evolution."""
    data = body_json()
    url = (data.get("url") or "").strip().rstrip("/")
    global_key = (data.get("global_key") or "").strip()
    instance = (data.get("instance") or DEFAULT_INSTANCE).strip() or DEFAULT_INSTANCE
    webhook_base = (data.get("webhook_base") or "").strip()
    if not url or not global_key:
        return jsonify({"detail": "url e global_key obrigatorios"}), 400
    _set_setting("evolution_url", url)
    _set_setting("evolution_key", global_key)
    _set_setting("evolution_instance", instance)
    if webhook_base:
        _set_setting("whatsapp_webhook_base", webhook_base)
    db.session.commit()

    token = webhook_token(global_key, instance)
    base = (webhook_base or _get_setting("whatsapp_webhook_base", "") or DEFAULT_WEBHOOK_BASE).rstrip("/")
    hook = f"{base}/api/whatsapp/webhook?token={token}"
    status, resp = _evo_call("POST", "/instance/create", global_key, {
        "instanceName": instance,
        "qrcode": True,
        "integration": "WHATSAPP-BAILEYS",
        "webhook": {
            "url": hook,
            "byEvents": False,
            "webhookByEvents": False,
            "webhookBase64": False,
            "events": ["MESSAGES_UPSERT", "CONNECTION_UPDATE"],
            "enabled": True,
        },
    }, timeout=20)
    if status not in (200, 201):
        # 403/422 = instancia ja existe: segue o baile (reaproveita).
        if status not in (403, 422, 409):
            return jsonify({"detail": (resp or {}).get("error") or "falha ao criar instancia",
                            "status": status, "saved": True}), 502
    inst = (resp or {}).get("instance") or {}
    inst_key = (resp or {}).get("hash") or inst.get("apikey") or (resp or {}).get("apikey") or ""
    row = db.session.query(WhatsappInstance).filter_by(name=instance).first()
    if not row:
        row = WhatsappInstance(name=instance)
        db.session.add(row)
    if inst_key:
        row.api_key = inst_key
    row.status = "aguardando_qr"
    row.updated_at = utcnow()
    db.session.commit()
    return jsonify({"saved": True, "instance": row.to_dict(), "webhook": hook,
                    "create_status": status})


@bp.get("/api/whatsapp/status")
@token_required()
def whatsapp_status():
    """Estado da integracao: configurado? conexao real? numero?"""
    cfg = _cfg()
    url = cfg.get("evolution_url", "")
    global_key = cfg.get("evolution_key", "")
    instance = cfg.get("evolution_instance", "") or DEFAULT_INSTANCE
    if not url or not global_key:
        return jsonify({"configured": False, "instance": instance,
                        "connection": "unknown", "phone": ""})
    status, resp = _evo_call("GET", f"/instance/connectionState/{instance}", global_key)
    connection = "unknown"
    if status == 200 and isinstance(resp, dict):
        inst = resp.get("instance") or {}
        connection = str(inst.get("state") or resp.get("state") or "unknown")
    phone = ""
    if connection == "open":
        _, lst = _evo_call("GET", "/instance/fetchInstances", global_key)
        items = lst if isinstance(lst, list) else []
        for it in items:
            nm = it.get("name") or (it.get("instance") or {}).get("instanceName")
            if nm == instance:
                owner = it.get("ownerJid") or ""
                phone = _digits(str(owner).split("@")[0])
                break
    row = db.session.query(WhatsappInstance).filter_by(name=instance).first()
    if row:
        row.status = "conectada" if connection == "open" else (
            "aguardando_qr" if connection in ("connecting", "qr") else "desconectada")
        if phone:
            row.phone = phone
        db.session.commit()
    return jsonify({"configured": True, "instance": instance, "connection": connection,
                    "phone": phone,
                    "webhook": _webhook_url(instance, global_key)})


@bp.get("/api/whatsapp/qr")
@token_required()
def whatsapp_qr():
    """QR novo (GET /instance/connect). Nunca persistido: vale ~3 min."""
    cfg = _cfg()
    global_key = cfg.get("evolution_key", "")
    instance = cfg.get("evolution_instance", "") or DEFAULT_INSTANCE
    if not (cfg.get("evolution_url") and global_key):
        return jsonify({"detail": "WhatsApp nao configurado (rode o setup)"}), 409
    status, resp = _evo_call("GET", f"/instance/connect/{instance}", global_key, timeout=20)
    if status != 200:
        return jsonify({"detail": (resp or {}).get("error") or "falha ao gerar QR",
                        "status": status}), 502
    code = (resp or {}).get("code") or ""
    b64 = (resp or {}).get("base64") or ""
    if b64.startswith("data:image"):
        b64 = b64.split(",", 1)[-1]
    return jsonify({"base64": b64, "pairingCode": (resp or {}).get("pairingCode") or "",
                    "code": code})


@bp.post("/api/whatsapp/logout")
@token_required(roles=["ADMIN"])
def whatsapp_logout():
    """Desconecta o aparelho pareado (POST /instance/logout) sem apagar nada.

    Mantem instancia, conversas e mensagens no ERP — so derruba a sessao no
    celular, para parear outra conta gerando um QR novo em seguida. 409 sem
    config; 502 se a Evolution falhar.
    """
    cfg = _cfg()
    global_key = cfg.get("evolution_key", "")
    instance = cfg.get("evolution_instance", "") or DEFAULT_INSTANCE
    if not (cfg.get("evolution_url") and global_key):
        return jsonify({"detail": "WhatsApp nao configurado (rode o setup)"}), 409
    status, resp = _evo_call("POST", f"/instance/logout/{instance}", global_key, {}, timeout=20)
    # 404 = instancia ja sumiu na Evolution: considera desconectado mesmo
    # assim e atualiza o espelho local. 0 = sem rede (vira 502 honesto).
    if status not in (200, 201, 404):
        return jsonify({"detail": (resp or {}).get("error") or "falha ao desconectar",
                        "status": status}), 502
    row = db.session.query(WhatsappInstance).filter_by(name=instance).first()
    if row:
        row.status = "desconectada"
        row.phone = ""
        row.updated_at = utcnow()
        db.session.commit()
    return jsonify({"ok": True, "instance": instance, "logout_status": status})


# ── webhook (SEM login; token na URL) ────────────────────────────────


@bp.post("/api/whatsapp/webhook")
def whatsapp_webhook():
    cfg = _cfg()
    global_key = cfg.get("evolution_key", "")
    if not global_key:
        return jsonify({"detail": "WhatsApp nao configurado"}), 401
    data = request.get_json(silent=True) or {}
    instance = str(data.get("instance") or cfg.get("evolution_instance") or DEFAULT_INSTANCE)
    esperado = webhook_token(global_key, instance)
    recebido = (request.args.get("token") or "").strip()
    header_key = (request.headers.get("apikey") or "").strip()
    if not (hmac.compare_digest(recebido, esperado) or
            (header_key and hmac.compare_digest(header_key, esperado))):
        return jsonify({"detail": "nao autorizado"}), 401
    event = str(data.get("event") or "")
    if event not in ("messages.upsert", "MESSAGES_UPSERT"):
        return jsonify({"ok": True, "skipped": event or "no-event"})
    payload = data.get("data") or {}
    items = payload if isinstance(payload, list) else [payload]
    stored = dup = ignored = 0
    for it in items:
        if not isinstance(it, dict):
            ignored += 1
            continue
        r = _store_inbound(instance, it)
        if r == "stored":
            stored += 1
        elif r == "duplicate":
            dup += 1
        else:
            ignored += 1
    db.session.commit()
    return jsonify({"ok": True, "stored": stored, "duplicate": dup, "ignored": ignored})


# ── chat (com login) ─────────────────────────────────────────────────


@bp.get("/api/whatsapp/conversations")
@token_required()
def list_conversations():
    cfg = _cfg()
    instance = cfg.get("evolution_instance", "") or DEFAULT_INSTANCE
    rows = (
        db.session.query(WhatsappConversation)
        .filter_by(instance=instance)
        .order_by(WhatsappConversation.last_message_at.desc().nullslast(),
                  WhatsappConversation.created_at.desc())
        .all()
    )
    out = []
    for c in rows:
        last = (
            db.session.query(WhatsappMessage)
            .filter_by(conversation_id=c.id)
            .order_by(WhatsappMessage.created_at.desc())
            .first()
        )
        out.append(c.to_dict(last=last))
    return jsonify(out)


@bp.get("/api/whatsapp/conversations/<conv_id>/messages")
@token_required()
def list_messages(conv_id):
    conv = db.session.get(WhatsappConversation, conv_id)
    if not conv:
        return jsonify({"detail": "Conversa nao encontrada"}), 404
    rows = (
        db.session.query(WhatsappMessage)
        .filter_by(conversation_id=conv.id)
        .order_by(WhatsappMessage.created_at.asc())
        .all()
    )
    return jsonify([r.to_dict() for r in rows])


def _send_text(global_key, instance, number, text):
    return _evo_call("POST", f"/message/sendText/{instance}", global_key,
                     {"number": number, "text": text}, timeout=20)


def _extract_provider_id(resp):
    """Id da mensagem no retorno do envio (p/ o eco do webhook dedupar).

    A Evolution varia o shape: {key: {id}} | {id} | {messageId} | {keyId}.
    Ausente = None (o eco, se chegar sem id, vira linha separada — raro).
    """
    if not isinstance(resp, dict):
        return None
    key = resp.get("key") or {}
    for cand in (key.get("id") if isinstance(key, dict) else None,
                 resp.get("id"), resp.get("messageId"), resp.get("keyId")):
        if cand:
            return str(cand)[:120]
    return None


def _send_media(global_key, instance, number, kind, b64, filename, caption):
    payloads = [
        {"number": number, "mediatype": kind, "media": b64,
         "caption": caption or "", "fileName": filename},
        {"number": number, "mediaType": kind, "mimetype": None, "media": b64,
         "caption": caption or "", "fileName": filename},
    ]
    last = (0, {"error": "sem tentativa"})
    for p in payloads:
        last = _evo_call("POST", f"/message/sendMedia/{instance}", global_key, p, timeout=30)
        if last[0] < 400:
            return last
    return last


@bp.post("/api/whatsapp/conversations/<conv_id>/send")
@token_required()
def send_message(conv_id):
    cfg = _cfg()
    global_key = cfg.get("evolution_key", "")
    instance = cfg.get("evolution_instance", "") or DEFAULT_INSTANCE
    if not (cfg.get("evolution_url") and global_key):
        return jsonify({"detail": "WhatsApp nao configurado (rode o setup)"}), 409
    conv = db.session.get(WhatsappConversation, conv_id)
    if not conv:
        return jsonify({"detail": "Conversa nao encontrada"}), 404
    file = request.files.get("file")
    if file and file.filename:
        original = secure_filename(file.filename) or "arquivo"
        if len(original) > 255:
            stem, ext = os.path.splitext(original)
            original = (stem[: max(0, 255 - len(ext))] + ext)[:255]
        blob = file.read()
        if not blob:
            return jsonify({"detail": "Arquivo vazio"}), 400
        caption = (request.form.get("caption") or request.form.get("text") or "").strip()[:1000]
        ext = os.path.splitext(original)[1].lower()
        if ext in (".jpg", ".jpeg", ".png", ".gif", ".webp"):
            kind = "image"
        elif ext in (".mp4", ".mov", ".avi"):
            kind = "video"
        elif ext in (".mp3", ".ogg", ".oga", ".wav", ".m4a"):
            kind = "audio"
        else:
            kind = "document"
        b64 = base64.b64encode(blob).decode()
        status, resp = _send_media(global_key, instance, conv.phone, kind, b64, original, caption)
        if status >= 300 or status == 0:
            return jsonify({"detail": (resp or {}).get("error") or "falha ao enviar midia",
                            "status": status}), 502
        stored = uuid.uuid4().hex + ext
        path = os.path.join(current_app.config["UPLOAD_DIR"], stored)
        os.makedirs(current_app.config["UPLOAD_DIR"], exist_ok=True)
        with open(path, "wb") as f:
            f.write(blob)
        row = WhatsappMessage(
            conversation_id=conv.id, direction="out", kind=kind,
            body=caption, media_stored=stored, media_filename=original,
            media_mime=file.mimetype or "", media_size=len(blob),
            status="sent", provider_id=_extract_provider_id(resp),
            created_by=g.current_user.username if hasattr(g, "current_user") else "",
        )
    else:
        data = body_json()
        text = ((data.get("text") if isinstance(data, dict) else "") or "").strip()
        if not text:
            return jsonify({"detail": "text ou file obrigatorio"}), 400
        status, resp = _send_text(global_key, instance, conv.phone, text[:4000])
        if status >= 300 or status == 0:
            return jsonify({"detail": (resp or {}).get("error") or "falha ao enviar",
                            "status": status}), 502
        row = WhatsappMessage(
            conversation_id=conv.id, direction="out", kind="text",
            body=text[:4000], status="sent",
            provider_id=_extract_provider_id(resp),
            created_by=g.current_user.username if hasattr(g, "current_user") else "",
        )
    db.session.add(row)
    conv.last_message_at = utcnow()
    if conv.client_id is None:
        conv.client_id = _match_client_id(conv.phone)
    db.session.commit()
    return jsonify(row.to_dict()), 201


def _as_msg_list(resp):
    """Extrai a lista de mensagens do findMessages (o envelope varia).

    Formatos vistos: lista pura | {messages: [...]} | {messages: {records:
    [...]}} | {records|data|result: [...]}.
    """
    if isinstance(resp, list):
        return [i for i in resp if isinstance(i, dict)]
    if isinstance(resp, dict):
        for k in ("records", "data", "result"):
            v = resp.get(k)
            if isinstance(v, list):
                return [i for i in v if isinstance(i, dict)]
        mid = resp.get("messages")
        if isinstance(mid, list):
            return [i for i in mid if isinstance(i, dict)]
        if isinstance(mid, dict):
            for k in ("records", "messages", "data"):
                v = mid.get(k)
                if isinstance(v, list):
                    return [i for i in v if isinstance(i, dict)]
    return []


@bp.post("/api/whatsapp/conversations/<conv_id>/sync")
@token_required()
def sync_conversation(conv_id):
    """Puxa o historico da conversa na Evolution (celular + ERP juntos).

    O webhook só recebe o que chega DEPOIS da conexão: o que foi trocado
    antes (ou com o webhook fora) só aparece via este sync — é o botão
    "Sincronizar" da tela. Reaproveita `_store_inbound`, então o dedupe por
    provider_id impede duplicar o que já está no banco.
    """
    cfg = _cfg()
    global_key = cfg.get("evolution_key", "")
    instance = cfg.get("evolution_instance", "") or DEFAULT_INSTANCE
    if not (cfg.get("evolution_url") and global_key):
        return jsonify({"detail": "WhatsApp nao configurado (rode o setup)"}), 409
    conv = db.session.get(WhatsappConversation, conv_id)
    if not conv:
        return jsonify({"detail": "Conversa nao encontrada"}), 404
    jid = f"{_digits(conv.phone)}@s.whatsapp.net"
    attempts = [
        {"where": {"key": {"remoteJid": jid}}, "limit": 200},
        {"where": {"remoteJid": jid}, "limit": 200},
    ]
    items = []
    via = ""
    last_err = ""
    for body in attempts:
        status, resp = _evo_call("POST", f"/chat/findMessages/{instance}", global_key, body, timeout=30)
        if status == 0 or status >= 300:
            last_err = (resp or {}).get("error") or f"status {status}"
            continue
        items = _as_msg_list(resp)
        via = f"findMessages where={list(body['where'].keys())}"
        break
    if not via:
        return jsonify({"detail": last_err or "falha ao buscar historico"}), 502
    stored = dup = ignored = 0
    for it in items:
        r = _store_inbound(instance, it)
        if r == "stored":
            stored += 1
        elif r == "duplicate":
            dup += 1
        else:
            ignored += 1
    db.session.commit()
    return jsonify({"ok": True, "stored": stored, "duplicate": dup,
                    "ignored": ignored, "via": via})


@bp.get("/api/whatsapp/messages/<msg_id>/media")
@token_required()
def download_media(msg_id):
    row = db.session.get(WhatsappMessage, msg_id)
    if not row:
        return jsonify({"detail": "Midia nao encontrada"}), 404
    if row.media_stored:
        path = os.path.join(current_app.config["UPLOAD_DIR"], row.media_stored)
        if not os.path.exists(path):
            return jsonify({"detail": "Arquivo ausente no disco"}), 404
        return send_file(path, mimetype=row.media_mime or "application/octet-stream",
                         as_attachment=True, download_name=row.media_filename or "arquivo")
    # Entrada ainda sem bytes: busca sob demanda na Evolution e guarda em disco.
    if row.direction != "in" or not row.provider_id or not row.remote_jid:
        return jsonify({"detail": "Midia nao encontrada"}), 404
    cfg = _cfg()
    global_key = cfg.get("evolution_key", "")
    instance = cfg.get("evolution_instance", "") or DEFAULT_INSTANCE
    if not (cfg.get("evolution_url") and global_key):
        return jsonify({"detail": "WhatsApp nao configurado (rode o setup)"}), 409
    status, resp = _evo_call(
        "POST", f"/chat/getBase64FromMediaMessage/{instance}", global_key,
        {"message": {"key": {"id": row.provider_id,
                             "remoteJid": row.remote_jid,
                             "fromMe": False}}},
        timeout=30)
    b64 = (resp or {}).get("base64") or ""
    try:
        blob = base64.b64decode(b64) if b64 else b""
    except (ValueError, TypeError):
        blob = b""
    if status >= 300 or status == 0 or not blob:
        return jsonify({"detail": (resp or {}).get("error")
                        or "Midia indisponivel na Evolution (mensagem antiga?)"}), 502
    mime = str((resp or {}).get("mimetype") or row.media_mime or "")
    ext = os.path.splitext(row.media_filename or "")[1].lower() or ".bin"
    stored = uuid.uuid4().hex + ext
    path = os.path.join(current_app.config["UPLOAD_DIR"], stored)
    os.makedirs(current_app.config["UPLOAD_DIR"], exist_ok=True)
    with open(path, "wb") as f:
        f.write(blob)
    row.media_stored = stored
    row.media_mime = mime[:120]
    row.media_size = len(blob)
    db.session.commit()
    return send_file(path, mimetype=mime or "application/octet-stream",
                     as_attachment=True, download_name=row.media_filename or "arquivo")


@bp.post("/api/whatsapp/conversations")
@token_required()
def start_conversation():
    """Abre (ou reaproveita) conversa com um telefone. Nao cria Client."""
    data = body_json()
    cfg = _cfg()
    instance = cfg.get("evolution_instance", "") or DEFAULT_INSTANCE
    digits = _digits(data.get("phone"))
    if not digits:
        return jsonify({"detail": "phone obrigatorio"}), 400
    conv = _get_conversation(instance, digits, (data.get("name") or "").strip()[:160])
    db.session.commit()
    last = (
        db.session.query(WhatsappMessage)
        .filter_by(conversation_id=conv.id)
        .order_by(WhatsappMessage.created_at.desc())
        .first()
    )
    return jsonify(conv.to_dict(last=last)), 201
