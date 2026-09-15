"""Modelos ERP EME Moveis. Todos os IDs sao String(36) UUID."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, Date, DateTime, Numeric, String, Text, Time
from sqlalchemy import ForeignKey, UniqueConstraint

from app.helpers import iso, num
from app.extensions import db


def new_uuid():
    return str(uuid.uuid4())


def utcnow():
    return datetime.now(timezone.utc)


class User(db.Model):
    __tablename__ = "users"
    id = db.Column(String(36), primary_key=True, default=new_uuid)
    username = db.Column(String(80), unique=True, nullable=False, index=True)
    name = db.Column(String(160), nullable=False, default="")
    email = db.Column(String(160), unique=True, nullable=False, index=True)
    role = db.Column(String(20), nullable=False, default="ESTOQUE")
    password = db.Column(String(255), nullable=False)
    avatar = db.Column(Text, nullable=True)
    created_at = db.Column(DateTime, nullable=False, default=utcnow)

    def to_dict(self, include_password=False):
        d = {
            "id": self.id,
            "username": self.username,
            "name": self.name,
            "email": self.email,
            "role": self.role,
            "avatar": self.avatar,
            "created_at": iso(self.created_at),
        }
        if include_password:
            d["password"] = self.password
        return d


class Client(db.Model):
    __tablename__ = "clients"
    id = db.Column(String(36), primary_key=True, default=new_uuid)
    name = db.Column(String(200), nullable=False)
    email = db.Column(String(160), nullable=True, default="")
    phone = db.Column(String(60), nullable=True, default="")
    cpf_cnpj = db.Column(String(30), unique=True, nullable=True, index=True)
    address = db.Column(Text, nullable=True, default="")
    created_at = db.Column(DateTime, nullable=False, default=utcnow)
    funnel_status = db.Column(String(20), nullable=False, default="PROSPECCAO")
    lost_reason = db.Column(Text, nullable=True)
    estimated_value = db.Column(Numeric(14, 2), nullable=True)
    lead_source = db.Column(String(120), nullable=True)
    campaign = db.Column(String(120), nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email or "",
            "phone": self.phone or "",
            "cpf_cnpj": self.cpf_cnpj,
            "address": self.address or "",
            "created_at": iso(self.created_at),
            "funnel_status": self.funnel_status,
            "lost_reason": self.lost_reason,
            "estimated_value": num(self.estimated_value),
            "lead_source": self.lead_source,
            "campaign": self.campaign,
            "negotiation_value": self.negotiation_value,
        }


    @property
    def negotiation_value(self):
        total = sum(i.subtotal for i in self.items)
        return total if total > 0 else None


class Project(db.Model):
    __tablename__ = "projects"
    id = db.Column(String(36), primary_key=True, default=new_uuid)
    title = db.Column(String(200), nullable=False)
    client_id = db.Column(
        String(36), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True
    )
    description = db.Column(Text, nullable=True, default="")
    status = db.Column(String(20), nullable=False, default="ORCAMENTO")
    value = db.Column(Numeric(14, 2), nullable=True, default=0)
    deadline = db.Column(Date, nullable=True)
    steps = db.Column(JSON, nullable=True, default=list)
    created_at = db.Column(DateTime, nullable=False, default=utcnow)

    client = db.relationship("Client", backref=db.backref("projects", cascade="all, delete-orphan", passive_deletes=True))

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "client_id": self.client_id,
            "client_name": self.client.name if self.client else None,
            "description": self.description or "",
            "status": self.status,
            "value": num(self.value),
            "deadline": iso(self.deadline),
            "steps": self.steps or [],
            "created_at": iso(self.created_at),
        }


class FinancialRecord(db.Model):
    __tablename__ = "financial_records"
    id = db.Column(String(36), primary_key=True, default=new_uuid)
    description = db.Column(String(255), nullable=False)
    type = db.Column(String(10), nullable=False)  # ENTRADA | SAIDA
    category = db.Column(String(120), nullable=True, default="")
    amount = db.Column(Numeric(14, 2), nullable=False, default=0)
    date = db.Column(Date, nullable=False)
    project_id = db.Column(String(36), ForeignKey("projects.id", ondelete="SET NULL"), nullable=True, index=True)
    status = db.Column(String(10), nullable=False, default="PENDENTE")
    due_date = db.Column(Date, nullable=True)

    project = db.relationship("Project")

    def to_dict(self):
        return {
            "id": self.id,
            "description": self.description,
            "type": self.type,
            "category": self.category,
            "amount": num(self.amount),
            "date": iso(self.date),
            "project_id": self.project_id,
            "status": self.status,
            "due_date": iso(self.due_date),
        }


class Category(db.Model):
    __tablename__ = "categories"
    id = db.Column(String(36), primary_key=True, default=new_uuid)
    name = db.Column(String(120), nullable=False)
    description = db.Column(Text, nullable=True)
    category_type = db.Column(String(20), nullable=False, default="STOCK")

    __table_args__ = (UniqueConstraint("name", "category_type", name="uq_category_name_type"),)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "category_type": self.category_type,
        }


class StockItem(db.Model):
    __tablename__ = "stock_items"
    id = db.Column(String(36), primary_key=True, default=new_uuid)
    name = db.Column(String(200), nullable=False)
    sku = db.Column(String(80), unique=True, nullable=False, index=True)
    category_id = db.Column(
        String(36), ForeignKey("categories.id", ondelete="CASCADE"), nullable=False, index=True
    )
    quantity = db.Column(Numeric(14, 3), nullable=False, default=0)
    min_quantity = db.Column(Numeric(14, 3), nullable=False, default=0)
    unit = db.Column(String(20), nullable=True, default="un")
    price = db.Column(Numeric(14, 2), nullable=True, default=0)
    supplier = db.Column(String(200), nullable=True, default="")

    category = db.relationship("Category")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "sku": self.sku,
            "category_id": self.category_id,
            "category_name": self.category.name if self.category else None,
            "quantity": num(self.quantity),
            "min_quantity": num(self.min_quantity),
            "unit": self.unit,
            "price": num(self.price),
            "supplier": self.supplier,
        }


class StockMovement(db.Model):
    __tablename__ = "stock_movements"
    id = db.Column(String(36), primary_key=True, default=new_uuid)
    item_id = db.Column(
        String(36), ForeignKey("stock_items.id", ondelete="CASCADE"), nullable=False, index=True
    )
    type = db.Column(String(10), nullable=False)  # ENTRADA | SAIDA
    quantity = db.Column(Numeric(14, 3), nullable=False)
    reason = db.Column(Text, nullable=True, default="")
    created_by = db.Column(String(80), nullable=True, default="")
    date = db.Column(DateTime, nullable=False, default=utcnow)

    item = db.relationship("StockItem")

    def to_dict(self):
        return {
            "id": self.id,
            "item_id": self.item_id,
            "item_name": self.item.name if self.item else None,
            "type": self.type,
            "quantity": num(self.quantity),
            "reason": self.reason,
            "created_by": self.created_by,
            "date": iso(self.date),
        }


class CalendarEvent(db.Model):
    __tablename__ = "calendar_events"
    id = db.Column(String(36), primary_key=True, default=new_uuid)
    title = db.Column(String(200), nullable=False)
    description = db.Column(Text, nullable=True)
    type = db.Column(String(30), nullable=False, default="PERSONALIZADO")
    status = db.Column(String(20), nullable=False, default="AGENDADO")
    start_date = db.Column(Date, nullable=False)
    start_time = db.Column(Time, nullable=True)
    end_date = db.Column(Date, nullable=True)
    end_time = db.Column(Time, nullable=True)
    project_id = db.Column(String(36), ForeignKey("projects.id", ondelete="SET NULL"), nullable=True)
    client_id = db.Column(String(36), ForeignKey("clients.id", ondelete="SET NULL"), nullable=True)
    assigned_user_id = db.Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    observations = db.Column(Text, nullable=True)
    created_at = db.Column(DateTime, nullable=False, default=utcnow)

    project = db.relationship("Project")
    client = db.relationship("Client")
    assigned_user = db.relationship("User")

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "type": self.type,
            "status": self.status,
            "start_date": iso(self.start_date),
            "start_time": iso(self.start_time),
            "end_date": iso(self.end_date),
            "end_time": iso(self.end_time),
            "project_id": self.project_id,
            "project_title": self.project.title if self.project else None,
            "client_id": self.client_id,
            "client_name": self.client.name if self.client else None,
            "assigned_user_id": self.assigned_user_id,
            "assigned_user_name": self.assigned_user.name if self.assigned_user else None,
            "observations": self.observations,
            "created_at": iso(self.created_at),
        }


class Notification(db.Model):
    __tablename__ = "notifications"
    id = db.Column(String(36), primary_key=True, default=new_uuid)
    title = db.Column(String(200), nullable=False)
    message = db.Column(Text, nullable=False, default="")
    type = db.Column(String(30), nullable=False, default="GERAL")
    read_at = db.Column(DateTime, nullable=True)
    user_id = db.Column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )
    event_id = db.Column(String(36), ForeignKey("calendar_events.id", ondelete="SET NULL"), nullable=True)
    project_id = db.Column(String(36), ForeignKey("projects.id", ondelete="SET NULL"), nullable=True)
    created_at = db.Column(DateTime, nullable=False, default=utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "message": self.message,
            "type": self.type,
            "read_at": iso(self.read_at),
            "user_id": self.user_id,
            "event_id": self.event_id,
            "project_id": self.project_id,
            "created_at": iso(self.created_at),
        }


class Interaction(db.Model):
    __tablename__ = "interactions"
    id = db.Column(String(36), primary_key=True, default=new_uuid)
    client_id = db.Column(String(36), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    type = db.Column(String(30), nullable=False, default="OBSERVACAO")  # CONVERSA | PROPOSTA | ORCAMENTO | ALTERACAO_PROJETO | OBSERVACAO | SISTEMA
    content = db.Column(Text, nullable=False)
    created_by = db.Column(String(80), nullable=True, default="")
    automatic = db.Column(Boolean, nullable=False, default=False)
    created_at = db.Column(DateTime, nullable=False, default=utcnow)
    # passive_deletes=False: SQLite nao habilita FK por padrao; o ORM garante o cascade em qualquer banco
    client = db.relationship("Client", backref=db.backref("interactions", cascade="all, delete-orphan", passive_deletes=False))

    def to_dict(self):
        return {
            "id": self.id,
            "client_id": self.client_id,
            "type": self.type,
            "content": self.content,
            "created_by": self.created_by or "",
            "automatic": bool(self.automatic),
            "created_at": iso(self.created_at),
        }


class Attachment(db.Model):
    __tablename__ = "attachments"
    id = db.Column(String(36), primary_key=True, default=new_uuid)
    client_id = db.Column(String(36), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    filename = db.Column(String(255), nullable=False)
    stored_name = db.Column(String(80), nullable=False, unique=True)
    mime_type = db.Column(String(120), nullable=True, default="")
    size = db.Column(db.Integer, nullable=False, default=0)
    created_by = db.Column(String(80), nullable=True, default="")
    created_at = db.Column(DateTime, nullable=False, default=utcnow)
    # passive_deletes=False: SQLite nao habilita FK por padrao; o ORM garante o cascade em qualquer banco
    client = db.relationship("Client", backref=db.backref("attachments", cascade="all, delete-orphan", passive_deletes=False))

    def to_dict(self):
        # stored_name (nome interno do arquivo) nao e serializado propositalmente
        return {
            "id": self.id,
            "client_id": self.client_id,
            "filename": self.filename,
            "mime_type": self.mime_type or "",
            "size": self.size,
            "created_by": self.created_by or "",
            "created_at": iso(self.created_at),
        }


class LeadSource(db.Model):
    __tablename__ = "lead_sources"
    id = db.Column(String(36), primary_key=True, default=new_uuid)
    name = db.Column(String(120), nullable=False, unique=True)
    active = db.Column(Boolean, nullable=False, default=True)
    created_at = db.Column(DateTime, nullable=False, default=utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "active": bool(self.active),
            "created_at": iso(self.created_at),
        }


class Campaign(db.Model):
    __tablename__ = "campaigns"
    id = db.Column(String(36), primary_key=True, default=new_uuid)
    name = db.Column(String(120), nullable=False, unique=True)
    active = db.Column(Boolean, nullable=False, default=True)
    created_at = db.Column(DateTime, nullable=False, default=utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "active": bool(self.active),
            "created_at": iso(self.created_at),
        }


class Product(db.Model):
    __tablename__ = "products"
    id = db.Column(String(36), primary_key=True, default=new_uuid)
    name = db.Column(String(200), nullable=False, unique=True)
    description = db.Column(Text, nullable=True, default="")
    default_price = db.Column(Numeric(14, 2), nullable=True)
    unit = db.Column(String(20), nullable=True, default="un")
    active = db.Column(Boolean, nullable=False, default=True)
    created_at = db.Column(DateTime, nullable=False, default=utcnow)

    def to_dict(self):
        return {"id": self.id, "name": self.name, "description": self.description or "",
                "default_price": num(self.default_price), "unit": self.unit or "un",
                "active": bool(self.active), "created_at": iso(self.created_at)}


class NegotiationItem(db.Model):
    __tablename__ = "negotiation_items"
    id = db.Column(String(36), primary_key=True, default=new_uuid)
    client_id = db.Column(String(36), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = db.Column(String(36), ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    name = db.Column(String(200), nullable=False)
    quantity = db.Column(Numeric(14, 3), nullable=False, default=1)
    unit_price = db.Column(Numeric(14, 2), nullable=False, default=0)
    recurrence = db.Column(String(30), nullable=False, default="UNICO")  # UNICO | MENSAL | TRIMESTRAL | ANUAL
    created_at = db.Column(DateTime, nullable=False, default=utcnow)

    # ORM garante cascade (SQLite sem FK); Postgres usa FK CASCADE
    client = db.relationship("Client", backref=db.backref("items", cascade="all, delete-orphan", passive_deletes=False))

    @property
    def subtotal(self):
        return (num(self.quantity) or 0) * (num(self.unit_price) or 0)

    def to_dict(self):
        return {"id": self.id, "client_id": self.client_id, "product_id": self.product_id,
                "name": self.name, "quantity": num(self.quantity), "unit_price": num(self.unit_price),
                "recurrence": self.recurrence, "subtotal": self.subtotal,
                "created_at": iso(self.created_at)}


class FunnelColumn(db.Model):
    __tablename__ = "funnel_columns"
    id = db.Column(String(36), primary_key=True, default=new_uuid)
    column_key = db.Column(String(60), nullable=False)
    label = db.Column(String(120), nullable=False, default="")
    description = db.Column(Text, nullable=True)
    updated_at = db.Column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)
    type = db.Column(String(20), nullable=False, default="CRM")

    __table_args__ = (UniqueConstraint("column_key", "type", name="uq_funnel_key_type"),)

    def to_dict(self):
        return {
            "id": self.id,
            "column_key": self.column_key,
            "label": self.label,
            "description": self.description,
            "updated_at": iso(self.updated_at),
            "type": self.type,
        }


class RecurringFinancial(db.Model):
    __tablename__ = "recurring_financial"
    id = db.Column(String(36), primary_key=True, default=new_uuid)
    description = db.Column(String(255), nullable=False)
    type = db.Column(String(10), nullable=False)
    category = db.Column(String(120), nullable=True, default="")
    amount = db.Column(Numeric(14, 2), nullable=False, default=0)
    frequency = db.Column(String(20), nullable=False, default="MENSAL")
    start_date = db.Column(Date, nullable=False)
    next_date = db.Column(Date, nullable=False)
    project_id = db.Column(String(36), ForeignKey("projects.id", ondelete="SET NULL"), nullable=True)
    active = db.Column(Boolean, nullable=False, default=True)
    created_at = db.Column(DateTime, nullable=False, default=utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "description": self.description,
            "type": self.type,
            "category": self.category,
            "amount": num(self.amount),
            "frequency": self.frequency,
            "start_date": iso(self.start_date),
            "next_date": iso(self.next_date),
            "project_id": self.project_id,
            "active": bool(self.active),
            "created_at": iso(self.created_at),
        }


class ChangelogEntry(db.Model):
    __tablename__ = "changelog_entries"
    id = db.Column(String(36), primary_key=True, default=new_uuid)
    title = db.Column(String(200), nullable=False)
    content = db.Column(Text, nullable=False, default="")
    category = db.Column(String(40), nullable=False, default="GERAL")  # GERAL | NOVIDADE | MELHORIA | CORRECAO
    entry_date = db.Column(Date, nullable=False, default=lambda: utcnow().date())
    created_by = db.Column(String(80), nullable=True, default="")
    created_at = db.Column(DateTime, nullable=False, default=utcnow)

    def to_dict(self):
        return {"id": self.id, "title": self.title, "content": self.content or "",
                "category": self.category, "entry_date": iso(self.entry_date),
                "created_by": self.created_by or "", "created_at": iso(self.created_at)}


DEFAULT_FUNNEL_COLUMNS = [
    # CRM (keys em MAIUSCULO = formato do dump original MySQL)
    ("PROSPECCAO", "Prospecção", "CRM"),
    ("ORCAMENTO", "Orçamento", "CRM"),
    ("APRESENTACAO", "Apresentação", "CRM"),
    ("NEGOCIACAO", "Negociação", "CRM"),
    ("FECHAMENTO", "Fechamento", "CRM"),
    ("PERDIDO", "Perdido", "CRM"),
    # PROJECTS
    ("ORCAMENTO", "Orçamento", "PROJECTS"),
    ("PROJETADO", "Projetado", "PROJECTS"),
    ("PRODUCAO", "Produção", "PROJECTS"),
    ("MONTAGEM", "Montagem", "PROJECTS"),
    ("CONCLUIDO", "Concluído", "PROJECTS"),
]


def ensure_default_funnel_columns():
    for key, label, ctype in DEFAULT_FUNNEL_COLUMNS:
        exists = db.session.query(FunnelColumn).filter_by(column_key=key, type=ctype).first()
        if not exists:
            db.session.add(FunnelColumn(column_key=key, label=label, type=ctype))
    db.session.commit()


DEFAULT_LEAD_SOURCES = [
    "Indicação de Arquiteto", "Parceria com Construtora", "Imobiliária", "Indicação",
    "Instagram", "Facebook", "Google", "WhatsApp", "Site", "Visita presencial", "Outro",
]
DEFAULT_CAMPAIGNS = ["Parceria com Construtora", "Indicação", "Instagram", "Site", "Outra"]


def ensure_default_lead_sources():
    for name in DEFAULT_LEAD_SOURCES:
        if not db.session.query(LeadSource).filter_by(name=name).first():
            db.session.add(LeadSource(name=name))
    db.session.commit()


def ensure_default_campaigns():
    for name in DEFAULT_CAMPAIGNS:
        if not db.session.query(Campaign).filter_by(name=name).first():
            db.session.add(Campaign(name=name))
    db.session.commit()
