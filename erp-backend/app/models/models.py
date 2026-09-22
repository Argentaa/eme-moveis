"""Modelos ERP EME Moveis. Todos os IDs sao String(36) UUID."""
import uuid
from datetime import date, datetime, timezone

DEADLINE_WARNING_DAYS = 7

from sqlalchemy import JSON, Boolean, Date, DateTime, Integer, Numeric, String, Text, Time
from sqlalchemy import ForeignKey, UniqueConstraint

from app.helpers import iso, num, parse_date
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


class Partner(db.Model):
    __tablename__ = "partners"
    id = db.Column(String(36), primary_key=True, default=new_uuid)
    name = db.Column(String(200), nullable=False)
    office = db.Column(String(160), nullable=True, default="")
    phone = db.Column(String(60), nullable=True, default="")
    email = db.Column(String(160), nullable=True, default="")
    city = db.Column(String(120), nullable=True, default="")
    notes = db.Column(Text, nullable=True, default="")
    active = db.Column(Boolean, nullable=False, default=True)
    created_at = db.Column(DateTime, nullable=False, default=utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "office": self.office or "",
            "phone": self.phone or "",
            "email": self.email or "",
            "city": self.city or "",
            "notes": self.notes or "",
            "active": bool(self.active),
            "created_at": iso(self.created_at),
        }


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
    funnel_id = db.Column(String(36), ForeignKey("funnels.id", ondelete="SET NULL"), nullable=True, index=True)
    partner_id = db.Column(String(36), ForeignKey("partners.id", ondelete="SET NULL"), nullable=True, index=True)
    partner = db.relationship("Partner")

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
            "funnel_id": self.funnel_id,
            "partner_id": self.partner_id,
            "partner_name": self.partner.name if getattr(self, "partner", None) else None,
        }

    @property
    def negotiation_value(self):
        total = sum(i.subtotal for i in self.items)
        return total if total > 0 else None


class Supplier(db.Model):
    __tablename__ = "suppliers"
    id = db.Column(String(36), primary_key=True, default=new_uuid)
    name = db.Column(String(200), nullable=False)
    cnpj = db.Column(String(30), nullable=True, default="")
    contact = db.Column(String(160), nullable=True, default="")
    phone = db.Column(String(60), nullable=True, default="")
    email = db.Column(String(160), nullable=True, default="")
    address = db.Column(Text, nullable=True, default="")
    category = db.Column(String(80), nullable=True, default="")
    payment_terms = db.Column(String(120), nullable=True, default="")
    avg_delivery_days = db.Column(Integer, nullable=True)
    created_at = db.Column(DateTime, nullable=False, default=utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "cnpj": self.cnpj or "",
            "contact": self.contact or "",
            "phone": self.phone or "",
            "email": self.email or "",
            "address": self.address or "",
            "category": self.category or "",
            "payment_terms": self.payment_terms or "",
            "avg_delivery_days": self.avg_delivery_days,
            "created_at": iso(self.created_at),
        }


class PurchaseOrder(db.Model):
    __tablename__ = "purchase_orders"
    id = db.Column(String(36), primary_key=True, default=new_uuid)
    number = db.Column(String(20), nullable=False, unique=True)
    status = db.Column(String(20), nullable=False, default="SOLICITADA")  # SOLICITADA|COTANDO|APROVADA|COMPRADA|RECEBIDA|CANCELADA
    supplier_id = db.Column(String(36), ForeignKey("suppliers.id", ondelete="SET NULL"), nullable=True, index=True)
    request_date = db.Column(Date, nullable=False)
    expected_date = db.Column(Date, nullable=True)
    received_at = db.Column(DateTime, nullable=True)
    notes = db.Column(Text, nullable=True, default="")
    created_by = db.Column(String(80), nullable=True, default="")
    created_at = db.Column(DateTime, nullable=False, default=utcnow)
    supplier = db.relationship("Supplier")
    items = db.relationship("PurchaseItem", cascade="all, delete-orphan", passive_deletes=False, order_by="PurchaseItem.position", overlaps="purchase_items,order")

    def to_dict(self):
        items = [i.to_dict() for i in self.items]
        return {"id": self.id, "number": self.number, "status": self.status,
                "supplier_id": self.supplier_id, "supplier_name": self.supplier.name if self.supplier else None,
                "request_date": iso(self.request_date), "expected_date": iso(self.expected_date),
                "received_at": iso(self.received_at),
                "notes": self.notes or "", "created_by": self.created_by or "",
                "created_at": iso(self.created_at), "items": items,
                "total": sum(i.total for i in self.items)}


class PurchaseItem(db.Model):
    __tablename__ = "purchase_items"
    id = db.Column(String(36), primary_key=True, default=new_uuid)
    order_id = db.Column(String(36), ForeignKey("purchase_orders.id", ondelete="CASCADE"), nullable=False, index=True)
    stock_item_id = db.Column(String(36), ForeignKey("stock_items.id", ondelete="SET NULL"), nullable=True)
    material_name = db.Column(String(200), nullable=False)
    quantity = db.Column(Numeric(14, 3), nullable=False, default=1)
    unit_price = db.Column(Numeric(14, 2), nullable=False, default=0)
    received_qty = db.Column(Numeric(14, 3), nullable=False, default=0)
    position = db.Column(Integer, nullable=False, default=0)
    order = db.relationship("PurchaseOrder", backref=db.backref("purchase_items", overlaps="items"), overlaps="items")

    @property
    def total(self):
        return (num(self.quantity) or 0) * (num(self.unit_price) or 0)

    def to_dict(self):
        return {"id": self.id, "order_id": self.order_id, "stock_item_id": self.stock_item_id,
                "material_name": self.material_name, "quantity": num(self.quantity),
                "unit_price": num(self.unit_price), "received_qty": num(self.received_qty),
                "position": self.position, "total": self.total}


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
    start_date = db.Column(Date, nullable=True)
    planned_end_date = db.Column(Date, nullable=True)
    actual_end_date = db.Column(Date, nullable=True)
    steps = db.Column(JSON, nullable=True, default=list)
    created_at = db.Column(DateTime, nullable=False, default=utcnow)
    funnel_id = db.Column(String(36), ForeignKey("funnels.id", ondelete="SET NULL"), nullable=True, index=True)

    client = db.relationship("Client", backref=db.backref("projects", cascade="all, delete-orphan", passive_deletes=True))

    @property
    def deadline_status(self):
        if self.status == "CONCLUIDO":
            return "CONCLUIDO"
        if not self.deadline:
            return "VERDE"
        try:
            delta = (self.deadline - date.today()).days
        except Exception:
            return "VERDE"
        if delta < 0:
            return "VERMELHO"
        if delta <= DEADLINE_WARNING_DAYS:
            return "LARANJA"
        return "VERDE"
    # NOTA: relationships Project.environments / time_entries / production_issues sao
    # criados via backref nas classes ProjectEnvironment / TimeEntry / ProductionIssue
    # definidas ao fim do arquivo. Nao duplicar aqui para nao conflitar (sqlalchemy
    # levanta erro de backref duplicado). O to_dict abaixo consome self.environments
    # que passa a existir apos o carregamento completo dos models.

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
            "start_date": iso(self.start_date),
            "planned_end_date": iso(self.planned_end_date),
            "actual_end_date": iso(self.actual_end_date),
            "deadline_status": self.deadline_status,
            "steps": self.steps or [],
            "created_at": iso(self.created_at),
            "funnel_id": self.funnel_id,
            "environments": [e.to_dict() for e in getattr(self, "environments", [])],
            "total_area_m2": float(sum((num(e.area_m2) or 0) for e in getattr(self, "environments", []))),
            "total_environments": len(getattr(self, "environments", [])),
        }


class BankAccount(db.Model):
    __tablename__ = "bank_accounts"
    id = db.Column(String(36), primary_key=True, default=new_uuid)
    name = db.Column(String(120), nullable=False)
    bank = db.Column(String(80), nullable=False, default="")
    agency = db.Column(String(40), nullable=True, default="")
    account_number = db.Column(String(60), nullable=True, default="")
    account_type = db.Column(String(20), nullable=False, default="CORRENTE")  # CORRENTE|POUPANCA|APLICACAO
    opening_balance = db.Column(Numeric(14, 2), nullable=False, default=0)
    opening_date = db.Column(Date, nullable=True)
    active = db.Column(Boolean, nullable=False, default=True)
    low_balance_threshold = db.Column(Numeric(14, 2), nullable=True)
    notes = db.Column(Text, nullable=True, default="")
    created_at = db.Column(DateTime, nullable=False, default=utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "bank": self.bank or "",
            "agency": self.agency or "",
            "account_number": self.account_number or "",
            "account_type": self.account_type,
            "opening_balance": num(self.opening_balance),
            "opening_date": iso(self.opening_date),
            "active": bool(self.active),
            "low_balance_threshold": num(self.low_balance_threshold) if self.low_balance_threshold is not None else None,
            "notes": self.notes or "",
            "created_at": iso(self.created_at),
            "current_balance": self.current_balance,
        }

    @property
    def current_balance(self):
        from app.extensions import db as _db
        from sqlalchemy import func as _func

        try:
            from app.models.models import FinancialRecord as _FR
        except ImportError:
            return float(self.opening_balance or 0)
        try:
            entradas = _db.session.query(_func.coalesce(_func.sum(_FR.amount), 0)).filter(_FR.bank_account_id == self.id, _FR.type == "ENTRADA", _FR.status == "PAGO").scalar() or 0
            saidas = _db.session.query(_func.coalesce(_func.sum(_FR.amount), 0)).filter(_FR.bank_account_id == self.id, _FR.type == "SAIDA", _FR.status == "PAGO").scalar() or 0
        except Exception:
            return float(self.opening_balance or 0)
        return float(self.opening_balance or 0) + float(entradas) - float(saidas)


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
    doc_number = db.Column(String(60), nullable=True, default="")
    issue_date = db.Column(Date, nullable=True)
    doc_type = db.Column(String(20), nullable=False, default="")  # BOLETO|CHEQUE|DEBITO_AUTOMATICO|DINHEIRO|FATURA|PIX
    bank = db.Column(String(80), nullable=True, default="")
    account_plan = db.Column(String(120), nullable=True, default="")
    item_description = db.Column(Text, nullable=True, default="")
    installments = db.Column(Integer, nullable=False, default=1)
    client_id = db.Column(
        String(36), ForeignKey("clients.id", ondelete="SET NULL"), nullable=True, index=True
    )
    supplier_id = db.Column(
        String(36), ForeignKey("suppliers.id", ondelete="SET NULL"), nullable=True, index=True
    )
    is_recurring = db.Column(Boolean, nullable=False, default=False)
    bank_account_id = db.Column(String(36), ForeignKey("bank_accounts.id", ondelete="SET NULL"), nullable=True, index=True)
    bank_account = db.relationship("BankAccount")

    project = db.relationship("Project")
    supplier = db.relationship("Supplier")

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
            "doc_number": self.doc_number or "",
            "issue_date": iso(self.issue_date),
            "doc_type": self.doc_type,
            "bank": self.bank or "",
            "account_plan": self.account_plan or "",
            "item_description": self.item_description or "",
            "installments": self.installments,
            "client_id": self.client_id,
            "supplier_id": self.supplier_id,
            "is_recurring": self.is_recurring,
            "bank_account_id": self.bank_account_id,
            "bank_account_name": self.bank_account.name if self.bank_account else None,
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
    project_id = db.Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=True, index=True)
    filename = db.Column(String(255), nullable=False)
    stored_name = db.Column(String(80), nullable=False, unique=True)
    mime_type = db.Column(String(120), nullable=True, default="")
    size = db.Column(db.Integer, nullable=False, default=0)
    created_by = db.Column(String(80), nullable=True, default="")
    created_at = db.Column(DateTime, nullable=False, default=utcnow)
    # passive_deletes=False: SQLite nao habilita FK por padrao; o ORM garante o cascade em qualquer banco
    client = db.relationship("Client", backref=db.backref("attachments", cascade="all, delete-orphan", passive_deletes=False))
    project = db.relationship("Project", backref=db.backref("project_attachments", cascade="all, delete-orphan", passive_deletes=False))

    def to_dict(self):
        # stored_name (nome interno do arquivo) nao e serializado propositalmente
        return {
            "id": self.id,
            "client_id": self.client_id,
            "project_id": self.project_id,
            "project_title": self.project.title if getattr(self, "project", None) else None,
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


class Funnel(db.Model):
    __tablename__ = "funnels"
    id = db.Column(String(36), primary_key=True, default=new_uuid)
    name = db.Column(String(120), nullable=False)
    kind = db.Column(String(20), nullable=False, default="CRM")
    is_default = db.Column(Boolean, nullable=False, default=False)
    active = db.Column(Boolean, nullable=False, default=True)
    created_at = db.Column(DateTime, nullable=False, default=utcnow)
    columns = db.relationship("FunnelColumn", backref="funnel", cascade="all, delete-orphan", passive_deletes=True, order_by="FunnelColumn.position")

    def to_dict(self, include_columns=True):
        d = {
            "id": self.id,
            "name": self.name,
            "kind": self.kind,
            "is_default": bool(self.is_default),
            "active": bool(self.active),
            "created_at": iso(self.created_at),
        }
        if include_columns:
            cols = sorted(self.columns, key=lambda x: (x.position, x.label))
            d["columns"] = [c.to_dict() for c in cols]
        return d


class FunnelColumn(db.Model):
    __tablename__ = "funnel_columns"
    id = db.Column(String(36), primary_key=True, default=new_uuid)
    column_key = db.Column(String(60), nullable=False)
    label = db.Column(String(120), nullable=False, default="")
    description = db.Column(Text, nullable=True)
    updated_at = db.Column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)
    type = db.Column(String(20), nullable=False, default="CRM")
    funnel_id = db.Column(String(36), ForeignKey("funnels.id", ondelete="CASCADE"), nullable=True, index=True)
    position = db.Column(Integer, nullable=False, default=0)

    __table_args__ = (UniqueConstraint("funnel_id", "column_key", name="uq_funnel_column_key"),)

    def to_dict(self):
        return {
            "id": self.id,
            "column_key": self.column_key,
            "label": self.label,
            "description": self.description,
            "updated_at": iso(self.updated_at),
            "type": self.type,
            "funnel_id": self.funnel_id,
            "position": self.position,
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


class BudgetGoal(db.Model):
    __tablename__ = "budget_goals"
    id = db.Column(String(36), primary_key=True, default=new_uuid)
    year = db.Column(Integer, nullable=False)
    month = db.Column(Integer, nullable=True)
    category = db.Column(String(120), nullable=False)
    target_value = db.Column(Numeric(14, 2), nullable=False, default=0)
    created_at = db.Column(DateTime, nullable=False, default=utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "year": self.year,
            "month": self.month,
            "category": self.category,
            "target_value": num(self.target_value),
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


class ChangelogRead(db.Model):
    """Marcacao de leitura das novidades, por usuario (lido / nao lido).

    Uma linha por par (usuario, novidade). A ausencia de linha significa nao lida.
    """
    __tablename__ = "changelog_reads"
    id = db.Column(String(36), primary_key=True, default=new_uuid)
    user_id = db.Column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    entry_id = db.Column(
        String(36), ForeignKey("changelog_entries.id", ondelete="CASCADE"), nullable=False, index=True
    )
    read_at = db.Column(DateTime, nullable=False, default=utcnow)

    __table_args__ = (
        UniqueConstraint("user_id", "entry_id", name="uq_changelog_read_user_entry"),
    )

    def to_dict(self):
        return {"id": self.id, "user_id": self.user_id, "entry_id": self.entry_id,
                "read_at": iso(self.read_at)}


class ServiceTicket(db.Model):
    __tablename__ = "service_tickets"
    id = db.Column(String(36), primary_key=True, default=new_uuid)
    number = db.Column(String(20), nullable=False, unique=True)
    client_id = db.Column(String(36), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id = db.Column(String(36), ForeignKey("projects.id", ondelete="SET NULL"), nullable=True, index=True)
    description = db.Column(Text, nullable=False)
    status = db.Column(String(20), nullable=False, default="ABERTO")
    cost = db.Column(Numeric(14, 2), nullable=True, default=0)
    cause = db.Column(Text, nullable=True, default="")
    solution = db.Column(Text, nullable=True, default="")
    in_warranty = db.Column(Boolean, nullable=True)
    assigned_user_id = db.Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    opened_at = db.Column(DateTime, nullable=False, default=utcnow)
    scheduled_at = db.Column(Date, nullable=True)
    resolved_at = db.Column(DateTime, nullable=True)
    closed_at = db.Column(DateTime, nullable=True)
    calendar_event_id = db.Column(String(36), ForeignKey("calendar_events.id", ondelete="SET NULL"), nullable=True)
    notes = db.Column(Text, nullable=True, default="")
    created_by = db.Column(String(80), nullable=True, default="")
    client = db.relationship("Client", backref=db.backref("service_tickets", cascade="all, delete-orphan", passive_deletes=False))
    project = db.relationship("Project")
    assigned_user = db.relationship("User")
    photos = db.relationship("TicketPhoto", cascade="all, delete-orphan", passive_deletes=False, order_by="TicketPhoto.created_at.desc()", overlaps="ticket_photos,ticket")

    def to_dict(self):
        return {
            "id": self.id,
            "number": self.number,
            "client_id": self.client_id,
            "client_name": self.client.name if self.client else None,
            "project_id": self.project_id,
            "project_title": self.project.title if self.project else None,
            "description": self.description,
            "status": self.status,
            "cost": num(self.cost),
            "cause": self.cause or "",
            "solution": self.solution or "",
            "in_warranty": self.in_warranty,
            "assigned_user_id": self.assigned_user_id,
            "assigned_user_name": self.assigned_user.name if self.assigned_user else None,
            "opened_at": iso(self.opened_at),
            "scheduled_at": iso(self.scheduled_at),
            "resolved_at": iso(self.resolved_at),
            "closed_at": iso(self.closed_at),
            "calendar_event_id": self.calendar_event_id,
            "notes": self.notes or "",
            "created_by": self.created_by or "",
        }


class TicketPhoto(db.Model):
    __tablename__ = "ticket_photos"
    id = db.Column(String(36), primary_key=True, default=new_uuid)
    ticket_id = db.Column(String(36), ForeignKey("service_tickets.id", ondelete="CASCADE"), nullable=False, index=True)
    filename = db.Column(String(255), nullable=False)
    stored_name = db.Column(String(80), nullable=False, unique=True)
    mime_type = db.Column(String(120), nullable=True, default="")
    size = db.Column(Integer, nullable=False, default=0)
    created_by = db.Column(String(80), nullable=True, default="")
    created_at = db.Column(DateTime, nullable=False, default=utcnow)
    ticket = db.relationship("ServiceTicket", backref=db.backref("ticket_photos", overlaps="photos,ticket"), overlaps="photos,ticket_photos")

    def to_dict(self):
        return {
            "id": self.id,
            "ticket_id": self.ticket_id,
            "filename": self.filename,
            "mime_type": self.mime_type or "",
            "size": self.size,
            "created_by": self.created_by or "",
            "created_at": iso(self.created_at),
        }


class ChecklistItem(db.Model):
    __tablename__ = "checklist_items"
    id = db.Column(String(36), primary_key=True, default=new_uuid)
    project_id = db.Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    step_id = db.Column(String(60), nullable=False)
    label = db.Column(String(200), nullable=False)
    completed = db.Column(Boolean, nullable=False, default=False)
    assigned_user_id = db.Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    completed_at = db.Column(DateTime, nullable=True)
    notes = db.Column(Text, nullable=True, default="")
    position = db.Column(Integer, nullable=False, default=0)
    created_at = db.Column(DateTime, nullable=False, default=utcnow)
    project = db.relationship(
        "Project",
        backref=db.backref(
            "checklist_items",
            cascade="all, delete-orphan",
            passive_deletes=False,
            order_by="ChecklistItem.position",
        ),
    )
    assigned_user = db.relationship("User")

    def to_dict(self):
        return {
            "id": self.id,
            "project_id": self.project_id,
            "project_title": self.project.title if getattr(self, "project", None) and getattr(self.project, "title", None) else None,
            "label": self.label,
            "step_id": self.step_id,
            "completed": bool(self.completed),
            "assigned_user_id": self.assigned_user_id,
            "assigned_user_name": self.assigned_user.name if getattr(self, "assigned_user", None) else None,
            "completed_at": iso(self.completed_at),
            "notes": self.notes or "",
            "position": self.position,
            "created_at": iso(self.created_at),
        }


class ProjectEnvironment(db.Model):
    __tablename__ = "project_environments"
    id = db.Column(String(36), primary_key=True, default=new_uuid)
    project_id = db.Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    name = db.Column(String(120), nullable=False)
    env_type = db.Column(String(30), nullable=False, default="OUTRO")  # COZINHA|QUARTO|SALA|PAINEL|ESCRITORIO|OUTRO
    area_m2 = db.Column(Numeric(10, 2), nullable=True)
    value = db.Column(Numeric(14, 2), nullable=True)
    status = db.Column(String(20), nullable=False, default="PLANEJADO")  # PLANEJADO|EM_PRODUCAO|CONCLUIDO
    created_at = db.Column(DateTime, nullable=False, default=utcnow)
    project = db.relationship(
        "Project",
        backref=db.backref(
            "environments",
            cascade="all, delete-orphan",
            passive_deletes=False,
            order_by="ProjectEnvironment.created_at",
        ),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "project_id": self.project_id,
            "project_title": self.project.title if self.project else None,
            "name": self.name,
            "env_type": self.env_type,
            "area_m2": num(self.area_m2),
            "value": num(self.value),
            "status": self.status,
            "created_at": iso(self.created_at),
        }


class Worker(db.Model):
    __tablename__ = "workers"
    id = db.Column(String(36), primary_key=True, default=new_uuid)
    name = db.Column(String(160), nullable=False, unique=True)
    active = db.Column(Boolean, nullable=False, default=True)
    created_at = db.Column(DateTime, nullable=False, default=utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "active": bool(self.active),
            "created_at": iso(self.created_at),
        }


class Machine(db.Model):
    __tablename__ = "machines"
    id = db.Column(String(36), primary_key=True, default=new_uuid)
    name = db.Column(String(160), nullable=False, unique=True)
    active = db.Column(Boolean, nullable=False, default=True)
    created_at = db.Column(DateTime, nullable=False, default=utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "active": bool(self.active),
            "created_at": iso(self.created_at),
        }


class TimeEntry(db.Model):
    __tablename__ = "time_entries"
    id = db.Column(String(36), primary_key=True, default=new_uuid)
    project_id = db.Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    environment_id = db.Column(String(36), ForeignKey("project_environments.id", ondelete="SET NULL"), nullable=True, index=True)
    worker_id = db.Column(String(36), ForeignKey("workers.id", ondelete="SET NULL"), nullable=True, index=True)
    machine_id = db.Column(String(36), ForeignKey("machines.id", ondelete="SET NULL"), nullable=True, index=True)
    hours = db.Column(Numeric(6, 2), nullable=False, default=0)
    hours_type = db.Column(String(20), nullable=False, default="PRODUTIVA")  # PRODUTIVA|IMPRODUTIVA
    work_date = db.Column(Date, nullable=False)
    notes = db.Column(Text, nullable=True, default="")
    created_by = db.Column(String(80), nullable=True, default="")
    created_at = db.Column(DateTime, nullable=False, default=utcnow)
    project = db.relationship(
        "Project",
        backref=db.backref("time_entries", cascade="all, delete-orphan", passive_deletes=False),
    )
    environment = db.relationship("ProjectEnvironment")
    worker = db.relationship("Worker")
    machine = db.relationship("Machine")

    def to_dict(self):
        return {
            "id": self.id,
            "project_id": self.project_id,
            "project_title": self.project.title if self.project else None,
            "environment_id": self.environment_id,
            "environment_name": self.environment.name if self.environment else None,
            "worker_id": self.worker_id,
            "worker_name": self.worker.name if self.worker else None,
            "machine_id": self.machine_id,
            "machine_name": self.machine.name if self.machine else None,
            "hours": num(self.hours),
            "hours_type": self.hours_type,
            "work_date": iso(self.work_date),
            "notes": self.notes or "",
            "created_by": self.created_by or "",
            "created_at": iso(self.created_at),
        }


class ProductionIssue(db.Model):
    __tablename__ = "production_issues"
    id = db.Column(String(36), primary_key=True, default=new_uuid)
    project_id = db.Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    kind = db.Column(String(20), nullable=False)  # RETRABALHO|DESPERDICIO|PERDA
    worker_id = db.Column(String(36), ForeignKey("workers.id", ondelete="SET NULL"), nullable=True, index=True)
    material = db.Column(String(120), nullable=True, default="")
    quantity = db.Column(Numeric(14, 3), nullable=True)
    hours_spent = db.Column(Numeric(6, 2), nullable=True)
    cost = db.Column(Numeric(14, 2), nullable=True)
    reason = db.Column(Text, nullable=True, default="")
    issue_date = db.Column(Date, nullable=False, default=lambda: utcnow().date())
    notes = db.Column(Text, nullable=True, default="")
    created_at = db.Column(DateTime, nullable=False, default=utcnow)
    project = db.relationship(
        "Project",
        backref=db.backref("production_issues", cascade="all, delete-orphan", passive_deletes=False),
    )
    worker = db.relationship("Worker")

    def to_dict(self):
        return {
            "id": self.id,
            "project_id": self.project_id,
            "project_title": self.project.title if self.project else None,
            "kind": self.kind,
            "worker_id": self.worker_id,
            "worker_name": self.worker.name if self.worker else None,
            "material": self.material or "",
            "quantity": num(self.quantity),
            "hours_spent": num(self.hours_spent),
            "cost": num(self.cost),
            "reason": self.reason or "",
            "issue_date": iso(self.issue_date),
            "notes": self.notes or "",
            "created_at": iso(self.created_at),
        }


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


DEFAULT_FUNNELS = [("Funil de Vendas", "CRM"), ("Funil de Produção", "PROJECTS")]


def ensure_default_funnels():
    for name, kind in DEFAULT_FUNNELS:
        exists = db.session.query(Funnel).filter_by(kind=kind, is_default=True).first()
        if not exists:
            db.session.add(Funnel(name=name, kind=kind, is_default=True, active=True))
    db.session.commit()


def ensure_default_funnel_columns():
    counters = {}
    for key, label, ctype in DEFAULT_FUNNEL_COLUMNS:
        pos = counters.get(ctype, 0)
        counters[ctype] = pos + 1
        funil = db.session.query(Funnel).filter_by(kind=ctype, is_default=True).first()
        if not funil:
            continue
        col = db.session.query(FunnelColumn).filter_by(funnel_id=funil.id, column_key=key).first()
        if col:
            continue
        legado = db.session.query(FunnelColumn).filter_by(column_key=key, type=ctype).filter(FunnelColumn.funnel_id.is_(None)).first()
        if legado:
            legado.funnel_id = funil.id
            legado.position = pos
        else:
            db.session.add(FunnelColumn(column_key=key, label=label, type=ctype, funnel_id=funil.id, position=pos))
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


# Novidades (changelog): mantido pela equipe de desenvolvimento (Donna) a cada
# entrega — titulo eh a chave de idempotencia (nao duplica no boot).
DEFAULT_CHANGELOG_ENTRIES = [
    ("CRM: detalhamento completo do cliente",
     "Clicar em um card abre o modal do cliente com 5 abas: Visão Geral, Histórico, Tarefas, Anexos e Produtos.",
     "NOVIDADE", "2026-09-15"),
    ("Histórico de interações do cliente",
     "Conversas, propostas e mudanças de etapa ou valor ficam registradas na linha do tempo do cliente — automático quando algo muda e manual quando quiser anotar.",
     "NOVIDADE", "2026-09-15"),
    ("Tarefas e lembretes por cliente",
     "Agende retornos com assunto, responsável, tipo (Ligação, Reunião, Visita, WhatsApp) e data/hora — aparecem na Agenda e no Painel Geral para evitar esquecimentos.",
     "NOVIDADE", "2026-09-15"),
    ("Anexos do cliente",
     "Plantas, contratos e propostas em PDF anexados direto no card do cliente, com download seguro. Os arquivos persistem entre atualizações.",
     "NOVIDADE", "2026-09-15"),
    ("Produtos/serviços por negociação",
     "Adicione ambientes e itens (quantidade × valor): o total da negociação é calculado automaticamente e alimenta o card e as colunas do Kanban.",
     "NOVIDADE", "2026-09-15"),
    ("Fontes de lead e campanhas personalizáveis",
     "Cadastre de onde o cliente veio (Indicação de Arquiteto, Parceria com Construtora, Imobiliária, Instagram...) e vincule campanhas — opções novas podem ser criadas na hora.",
     "NOVIDADE", "2026-09-15"),
    ("Relatório de Origem dos Leads",
     "Leads por fonte ou campanha com taxa de conversão e valores, exportável em PDF e Excel.",
     "NOVIDADE", "2026-09-15"),
    ("Registro de Novidades",
     "Esta página: o histórico de atualizações do sistema em cards, por categoria (Novidade, Melhoria, Correção).",
     "NOVIDADE", "2026-09-15"),
    ("Fluxo de caixa mensal e DRE em tabela",
     "Visão financeira com entradas e saídas mês a mês, saldo acumulado e gráfico; DRE com análise mensal, trimestral, semestral e anual — ambos exportáveis.",
     "NOVIDADE", "2026-09-15"),
    ("Planejamento orçamentário",
     "Metas por categoria e ano/mês com comparação orçado × realizado e percentual de atingimento.",
     "NOVIDADE", "2026-09-15"),
    ("Campos contábeis nos lançamentos",
     "Número e data do documento, tipo (Boleto, Cheque, Débito Automático, Dinheiro, Fatura, PIX), banco, plano de contas, descrição detalhada, nº de parcelas e despesa recorrente.",
     "MELHORIA", "2026-09-15"),
    ("Cadastro de fornecedores",
     "Fornecedores cadastráveis e vinculáveis aos lançamentos, com criação rápida direto no formulário.",
     "MELHORIA", "2026-09-15"),
    ("Migrações de banco automáticas no deploy",
     "O sistema aplica as atualizações do banco de dados sozinho ao iniciar — novas versões entram no ar sem passos manuais.",
     "MELHORIA", "2026-09-15"),
    ("Múltiplos funis de vendas",
     "Crie quantos funis precisar (ex.: por segmento ou equipe) com etapas próprias — adicionar, renomear, reordenar e excluir etapas direto na tela; cada cliente participa de um funil específico.",
     "NOVIDADE", "2026-09-15"),
    ("Compras: solicitação, pedido e recebimento com entrada automática no estoque",
     "Solicitações com status (Solicitada → Cotando → Aprovada → Comprada → Recebida), itens com vínculo ao estoque e número automático PC-AAAA-0001. Ao marcar como Recebida, o estoque é atualizado e o movimento fica no histórico.",
     "NOVIDADE", "2026-09-15"),
    ("Fornecedores com categoria, condições e prazo médio",
     "Cadastro com endereço, categoria (MDF, Ferragens...), condições de pagamento e prazo médio de entrega — filtros por categoria e busca por nome.",
     "MELHORIA", "2026-09-15"),
    ("Pós-venda: chamados de assistência técnica",
     "Abertura de chamados com número automático CH-AAAA-0001, status completo (Aberto → Em análise → Agendado → Em atendimento → Resolvido → Encerrado), fotos, garantia, custo, causa e solução. Ao agendar, cria evento na Agenda automaticamente.",
     "NOVIDADE", "2026-09-16"),
    ("Relatório de pós-venda com indicadores",
     "Chamados por status, custo total e médio, dentro vs fora da garantia e tempo médio de resolução, com filtros e exportação em PDF/Excel.",
     "NOVIDADE", "2026-09-16"),
    ("Produção: ambientes e m² por projeto",
     "Ambientes com tipo (Cozinha, Quarto, Sala, Painel), m², valor e status — totalizadores por projeto e base para indicadores industriais.",
     "NOVIDADE", "2026-09-16"),
    ("Produção: apontamento de horas com funcionários e máquinas",
     "Registro de horas produtivas e improdutivas por projeto, ambiente, funcionário e máquina — alimenta produtividade e capacidade.",
     "NOVIDADE", "2026-09-16"),
    ("Produção: retrabalho, desperdício e perdas",
     "Ocorrências com custo, material e motivo — indicadores de eficiência e custo de não-qualidade.",
     "NOVIDADE", "2026-09-16"),
    ("Produção: prazos com semáforo e relatório industrial",
     "Datas de início, previsão e conclusão com status verde/laranja/vermelho/concluído, alertas de projeto próximo do prazo e relatório industrial (m², horas, ocorrências, tempo médio).",
     "NOVIDADE", "2026-09-16"),
    ("Contas bancárias com saldo e projeção",
     "Cadastro com agência, tipo, saldo inicial e limite de alerta — saldo atual soma entradas pagas e salda saídas; visão de saldo projetado e total consolidado no painel.",
     "NOVIDADE", "2026-09-16"),
    ("Financeiro vinculado à conta bancária",
     "Lançamentos com vínculo à conta — o saldo reflete pagamentos e recebimentos; alerta de saldo baixo na agenda.",
     "MELHORIA", "2026-09-16"),
    ("Venda fechada cria projeto automaticamente",
     "Ao mover o cliente para a etapa final do funil, o projeto correspondente é criado no kanban com valor da negociação e checklist padrão — sem duplicar se já houver projeto ativo.",
     "NOVIDADE", "2026-09-16"),
    ("Alertas financeiros de contas vencidas e a vencer",
     "Contas pendentes vencidas e próximas do vencimento (7 dias) geram alertas na agenda com dedupe e são exibidos no painel.",
     "MELHORIA", "2026-09-16"),
    ("Anexos por projeto",
     "Cada projeto tem sua aba Arquivos — plantas, fotos e PDFs vinculados ao projeto com download seguro, persistindo entre deploys.",
     "NOVIDADE", "2026-09-16"),
    ("Checklists por etapa do projeto",
     "Itens configuráveis em cada etapa do projeto (conferir medidas, conferir acabamento, etc.) com responsável, data de conclusão e observações — checkbox com atribuição automática.",
     "NOVIDADE", "2026-09-16"),
    ("Parceiros e arquitetos com relatório",
     "Cadastro de parceiros (escritório, cidade, contato) vinculado ao cliente, badge no kanban, bloqueio de exclusão em uso e relatório dedicado com ranking por indicações e valor.",
     "NOVIDADE", "2026-09-16"),
    ("Arrastar cards entre as etapas do Kanban",
     "Agora dá para arrastar o card do cliente (funil de vendas) e do projeto (produção) direto para outra coluna — a etapa é atualizada na hora e a coluna de destino fica destacada.",
     "NOVIDADE", "2026-09-22"),
    ("O sistema lembra em que tela você estava",
     "Ao recarregar a página ou abrir em outra aba, o sistema volta para a mesma tela em que você estava, sem precisar navegar tudo de novo pelo menu.",
     "MELHORIA", "2026-09-22"),
    ("Painel Geral carrega mais rápido",
     "As informações do painel são buscadas todas ao mesmo tempo, em vez de esperar uma rodada terminar para pedir a próxima — o painel abre sem a espera longa nas métricas.",
     "MELHORIA", "2026-09-22"),
    ("Correção: menus de seleção abrindo sem estilo",
     "Os campos de seleção (Tipo de Documento, Conta Bancária, categorias, datas) abriam com a lista clara e sem formatação sobre a tela escura. Agora seguem o tema do sistema.",
     "CORRECAO", "2026-09-22"),
    ("Correção: tela piscando, elementos duplicados e travamento",
     "Removido o efeito de desfoque empilhado nos painéis e janelas, que causava piscadas pretas, textos borrados/duplicados e lentidão nas animações.",
     "CORRECAO", "2026-09-22"),
    ("Correção: navegação travada no Kanban",
     "O quadro do funil não empurra mais a página inteira para o lado: a rolagem horizontal acontece apenas dentro do quadro, e o rodapé de Negócios Perdidos ficou alinhado às colunas.",
     "CORRECAO", "2026-09-22"),
    ("Correção: botão de confirmar escondido nos lançamentos",
     "No formulário de lançamento contábil o botão de confirmar ficava no fim de uma rolagem longa. Agora ele fica fixo na base da janela, sempre visível.",
     "CORRECAO", "2026-09-22"),
    ("Fluxo de caixa: visões Realizado e Projetado",
     "O demonstrativo de fluxo de caixa agora tem dois modos: Realizado, que mostra só o que já foi pago ou recebido, e Projetado, que inclui também os lançamentos em aberto. A tabela ganhou as colunas de valores ainda em aberto por mês (a receber e a pagar).",
     "NOVIDADE", "2026-09-22"),
    ("Painel Geral: fluxo de caixa mês a mês",
     "O gráfico de fluxo de caixa do Painel Geral passou a mostrar os 12 meses do ano selecionado, com o mesmo botão para alternar entre Realizado e Projetado.",
     "MELHORIA", "2026-09-22"),
    ("Novidades avisa o que você ainda não leu",
     "O menu Novidades mostra um contador com quantas atualizações você ainda não leu. Ao abrir a aba, as novidades que chegaram ganham o selo NOVA e o contador é zerado. Cada usuário tem o seu próprio controle de leitura.",
     "NOVIDADE", "2026-09-22"),
]


def ensure_default_changelog():
    for title, content, category, entry_date in DEFAULT_CHANGELOG_ENTRIES:
        exists = db.session.query(ChangelogEntry).filter_by(title=title).first()
        if not exists:
            db.session.add(ChangelogEntry(
                title=title, content=content, category=category,
                entry_date=parse_date(entry_date), created_by="Donna",
            ))
    db.session.commit()
