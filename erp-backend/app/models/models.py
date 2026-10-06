"""Modelos ERP EME Moveis. Todos os IDs sao String(36) UUID."""
import uuid
from datetime import date, datetime, timezone

DEADLINE_WARNING_DAYS = 7

from sqlalchemy import JSON, Boolean, Date, DateTime, Integer, Numeric, String, Text, Time
from sqlalchemy import ForeignKey, UniqueConstraint
import sqlalchemy as sa

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
    funnel_status = db.Column(String(60), nullable=False, default="PROSPECCAO")  # recebe column_key do funil (ate 60)
    lost_reason = db.Column(Text, nullable=True)
    estimated_value = db.Column(Numeric(14, 2), nullable=True)
    lead_source = db.Column(String(120), nullable=True)
    campaign = db.Column(String(120), nullable=True)
    funnel_id = db.Column(String(36), ForeignKey("funnels.id", ondelete="SET NULL"), nullable=True, index=True)
    partner_id = db.Column(String(36), ForeignKey("partners.id", ondelete="SET NULL"), nullable=True, index=True)
    partner = db.relationship("Partner")
    # Venda concluida pelo botao "Concluir venda" do Comercial. Explicito, pelo
    # mesmo motivo do Project.concluded_at: as colunas do funil sao renomeadas
    # pelo cliente, entao nao da para deduzir "ganhou" do nome da coluna.
    # Preenchido = o card sai do funil de vendas e o projeto nasce na Producao.
    sale_concluded_at = db.Column(DateTime, nullable=True, index=True)

    # Campos de fornecedor (cadastro central: cliente tambem pode ser fornecedor)
    is_supplier = db.Column(Boolean, nullable=False, default=False, server_default=sa.false(), index=True)
    contact = db.Column(String(160), nullable=True, default="", server_default="")
    category = db.Column(String(80), nullable=True, default="", server_default="")
    payment_terms = db.Column(String(120), nullable=True, default="", server_default="")
    avg_delivery_days = db.Column(Integer, nullable=True)
    # Gravado quando o cliente entra na ultima etapa do funil (venda fechada).
    # Necessario para meta comercial e comissao por periodo; dados antigos ficam NULL.
    closed_at = db.Column(DateTime, nullable=True, index=True)
    # Quem vendeu: base da comissao de vendedor. NULL = sem atribuicao, e o
    # relatorio mostra como "sem vendedor" em vez de ratear entre todos.
    seller_id = db.Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    seller = db.relationship("User")

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
            "sale_concluded_at": iso(self.sale_concluded_at),
            "partner_id": self.partner_id,
            "partner_name": self.partner.name if getattr(self, "partner", None) else None,
            "seller_id": self.seller_id,
            "seller_name": self.seller.username if getattr(self, "seller", None) else None,
            "is_supplier": bool(self.is_supplier),
            "contact": self.contact or "",
            "category": self.category or "",
            "payment_terms": self.payment_terms or "",
            "avg_delivery_days": self.avg_delivery_days,
            "closed_at": iso(self.closed_at) if self.closed_at else None,
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
    # Espelho de cliente-fornecedor: quando um cliente e marcado como
    # fornecedor, uma linha espelho e mantida aqui (preserva as FKs de
    # purchase_orders.supplier_id e financial_records.supplier_id).
    client_id = db.Column(String(36), ForeignKey("clients.id", ondelete="SET NULL"), nullable=True, index=True)

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
            "client_id": self.client_id,
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
    # logistico: com quem vem e codigo de rastreio (calendario logistico)
    carrier = db.Column(String(120), nullable=True)
    tracking = db.Column(String(120), nullable=True)
    created_by = db.Column(String(80), nullable=True, default="")
    created_at = db.Column(DateTime, nullable=False, default=utcnow)
    supplier = db.relationship("Supplier")
    items = db.relationship("PurchaseItem", cascade="all, delete-orphan", passive_deletes=False, order_by="PurchaseItem.position", overlaps="purchase_items,order")
    quotations = db.relationship("PurchaseQuotation", cascade="all, delete-orphan",
                                 passive_deletes=False, backref="order")

    @property
    def saving_real(self):
        """Economia MEDIDA pelas cotacoes, no formato da planilha do cliente.

        Por item: (maior preco cotado entre os fornecedores) - (preco escolhido).
        So conta item que tem cotacao; pedido sem cotacao devolve 0 e o
        dashboard cai no proxy de catalogo, que e estimativa.

        Devolve (economia, itens_com_cotacao) para o frontend saber se o numero
        e medido ou estimado.
        """
        cotacoes = list(self.quotations or [])
        if not cotacoes:
            return 0.0, 0

        vencedora = next((q for q in cotacoes if q.is_winner), None)
        economia = 0.0
        com_cotacao = 0
        for item in self.items:
            precos = [
                num(qi.unit_price) or 0
                for q in cotacoes
                for qi in q.items
                if qi.purchase_item_id == item.id
            ]
            if not precos:
                continue
            com_cotacao += 1
            escolhido = num(item.unit_price) or 0
            if vencedora:
                preco_venc = next(
                    (num(qi.unit_price) or 0 for qi in vencedora.items
                     if qi.purchase_item_id == item.id), None,
                )
                if preco_venc is not None:
                    escolhido = preco_venc
            diff = (max(precos) - escolhido) * (num(item.quantity) or 0)
            if diff > 0:
                economia += diff
        return round(economia, 2), com_cotacao

    def to_dict(self):
        items = [i.to_dict() for i in self.items]
        economia, itens_cotados = self.saving_real
        return {"id": self.id, "number": self.number, "status": self.status,
                "supplier_id": self.supplier_id, "supplier_name": self.supplier.name if self.supplier else None,
                "request_date": iso(self.request_date), "expected_date": iso(self.expected_date),
                "received_at": iso(self.received_at),
                "notes": self.notes or "", "created_by": self.created_by or "",
                "carrier": self.carrier, "tracking": self.tracking,
                "quotations_count": len(self.quotations or []),
                "saving_real": economia,
                "saving_real_items": itens_cotados,
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


class PurchaseQuotation(db.Model):
    """Cotacao de UM fornecedor para UM pedido de compra.

    Varias por pedido: e o que permite o comparativo lado a lado que a spec
    pede. `is_winner` marca a escolhida — aprovar uma zera as outras, porque a
    vencedora e unica (senao a economia medida contaria duas vezes).
    """
    __tablename__ = "purchase_quotations"
    id = db.Column(String(36), primary_key=True, default=new_uuid)
    order_id = db.Column(String(36), ForeignKey("purchase_orders.id", ondelete="CASCADE"),
                         nullable=False, index=True)
    supplier_id = db.Column(String(36), ForeignKey("suppliers.id", ondelete="SET NULL"),
                            nullable=True, index=True)
    delivery_days = db.Column(Integer, nullable=True)
    payment_terms = db.Column(String(120), nullable=True)
    is_winner = db.Column(Boolean, nullable=False, default=False)
    notes = db.Column(Text, nullable=True)
    created_at = db.Column(DateTime, nullable=False, default=utcnow)

    supplier = db.relationship("Supplier")
    items = db.relationship("PurchaseQuotationItem", cascade="all, delete-orphan",
                            passive_deletes=False, backref="quotation")

    @property
    def total(self):
        """Valor da cotacao = soma(preco unitario x quantidade do item do pedido)."""
        total = 0.0
        for qi in self.items:
            qtd = num(qi.purchase_item.quantity) if qi.purchase_item else 0
            total += (num(qi.unit_price) or 0) * (qtd or 0)
        return round(total, 2)

    def to_dict(self):
        return {
            "id": self.id,
            "order_id": self.order_id,
            "supplier_id": self.supplier_id,
            "supplier_name": self.supplier.name if self.supplier else None,
            "delivery_days": self.delivery_days,
            "payment_terms": self.payment_terms or "",
            "is_winner": bool(self.is_winner),
            "notes": self.notes or "",
            "created_at": iso(self.created_at),
            "items": [i.to_dict() for i in self.items],
            "total": self.total,
        }


class PurchaseQuotationItem(db.Model):
    """Preco de UM item do pedido nesta cotacao."""
    __tablename__ = "purchase_quotation_items"
    id = db.Column(String(36), primary_key=True, default=new_uuid)
    quotation_id = db.Column(String(36), ForeignKey("purchase_quotations.id", ondelete="CASCADE"),
                             nullable=False, index=True)
    purchase_item_id = db.Column(String(36), ForeignKey("purchase_items.id", ondelete="CASCADE"),
                                 nullable=False, index=True)
    unit_price = db.Column(Numeric(14, 2), nullable=False, default=0)
    created_at = db.Column(DateTime, nullable=False, default=utcnow)

    purchase_item = db.relationship("PurchaseItem")

    def to_dict(self):
        return {
            "id": self.id,
            "quotation_id": self.quotation_id,
            "purchase_item_id": self.purchase_item_id,
            "purchase_item_name": self.purchase_item.material_name if self.purchase_item else None,
            "unit_price": num(self.unit_price),
        }


class Project(db.Model):
    __tablename__ = "projects"
    id = db.Column(String(36), primary_key=True, default=new_uuid)
    title = db.Column(String(200), nullable=False)
    client_id = db.Column(
        String(36), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True
    )
    description = db.Column(Text, nullable=True, default="")
    status = db.Column(String(60), nullable=False, default="ORCAMENTO")  # recebe column_key do funil (ate 60)
    value = db.Column(Numeric(14, 2), nullable=True, default=0)
    deadline = db.Column(Date, nullable=True)
    start_date = db.Column(Date, nullable=True)
    planned_end_date = db.Column(Date, nullable=True)
    actual_end_date = db.Column(Date, nullable=True)
    steps = db.Column(JSON, nullable=True, default=list)
    created_at = db.Column(DateTime, nullable=False, default=utcnow)
    funnel_id = db.Column(String(36), ForeignKey("funnels.id", ondelete="SET NULL"), nullable=True, index=True)
    # Conclusao explicita (botao "Concluir projeto"), independente da coluna do
    # funil. NAO usar a chave da coluna para isso: o cliente renomeia as colunas
    # e neste funil de Producao a chave "CONCLUIDO" esta numa coluna do MEIO
    # (rotulo "Medicao In Loco") — olhar a chave marcava projeto em medicao
    # como finalizado. NULL = em producao; preenchido = foi para Pos-venda.
    concluded_at = db.Column(DateTime, nullable=True, index=True)
    # Garantia (Fase 8): prazo em meses e a data-limite derivada na conclusao.
    # A derivacao calcula warranty_until = concluded_at + warranty_months;
    # deixar o cliente editar os meses sem mexer na data final.
    warranty_months = db.Column(Integer, nullable=True, default=0)
    warranty_until = db.Column(Date, nullable=True)
    # Venda que originou os cards de producao (um Project por ambiente vendido).
    # A FK fica apenas no modelo — no banco a coluna e adicionada sem constraint
    # na migracao 0035 (padrao 0011), o ORM cuida da integridade.
    sale_id = db.Column(String(36), ForeignKey("sales.id", ondelete="SET NULL"), nullable=True, index=True)
    sale = db.relationship("Sale", backref=db.backref("projects", order_by="Project.created_at"))

    client = db.relationship("Client", backref=db.backref("projects", cascade="all, delete-orphan", passive_deletes=True))

    @property
    def is_concluded(self):
        return self.concluded_at is not None

    @property
    def deadline_status(self):
        if self.concluded_at is not None:
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
            "concluded_at": iso(self.concluded_at),
            "is_concluded": self.is_concluded,
            "warranty_months": self.warranty_months,
            "warranty_until": iso(self.warranty_until),
            "in_warranty": self.warranty_until is not None and self.warranty_until >= date.today(),
            "sale_id": self.sale_id,
            "sale_code": self.sale.code if self.sale else None,
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


class AccountCategory(db.Model):
    """Categoria do plano de contas (grupo do DRE) — importada do sistema legado.

    `code` e o numero oficial (1-14); `indicator` CREDITO|DEBITO; `dre_range`
    a faixa no DRE ("Nao listar no DRE" = conta gerencial/transferencia).
    """

    __tablename__ = "account_categories"
    id = db.Column(String(36), primary_key=True, default=new_uuid)
    code = db.Column(Integer, nullable=False, unique=True)
    description = db.Column(String(120), nullable=False)
    indicator = db.Column(String(10), nullable=False, default="DEBITO")
    dre_range = db.Column(String(60), nullable=True, default="")

    def to_dict(self):
        return {
            "id": self.id,
            "code": self.code,
            "description": self.description,
            "indicator": self.indicator,
            "dre_range": self.dre_range or "",
            "plan_count": len(self.plans) if "plans" in self.__dict__ else None,
        }


class AccountPlan(db.Model):
    """Conta do plano de contas — `structured_code` e o X.Y oficial ("4.2").

    `code` e o numero sequencial do legado (1-54). O vinculo com a categoria
    segue o prefixo do codigo estruturado (4.2 -> categoria 4).
    """

    __tablename__ = "account_plans"
    id = db.Column(String(36), primary_key=True, default=new_uuid)
    code = db.Column(Integer, nullable=False, unique=True)
    structured_code = db.Column(String(20), nullable=False, unique=True)
    description = db.Column(String(160), nullable=False)
    category_id = db.Column(
        String(36), ForeignKey("account_categories.id", ondelete="RESTRICT"),
        nullable=False, index=True,
    )

    category = db.relationship("AccountCategory", backref="plans")

    def to_dict(self):
        cat = self.category
        return {
            "id": self.id,
            "code": self.code,
            "structured_code": self.structured_code,
            "description": self.description,
            "label": "%s - %s" % (self.structured_code, self.description),
            "category_id": self.category_id,
            "category_code": cat.code if cat else None,
            "category_description": cat.description if cat else None,
        }


# (codigo, descricao, indicador, faixa DRE) — espelho do sistema legado.
DEFAULT_ACCOUNT_CATEGORIES = [
    (1, "Receita com Vendas", "CREDITO", "Receitas"),
    (2, "Impostos Sobre Vendas", "DEBITO", "Deducoes sobre vendas"),
    (3, "Outras Deducoes", "DEBITO", "Deducoes sobre vendas"),
    (4, "Custos Variaveis", "DEBITO", "Custos variaveis"),
    (5, "Gastos com Pessoal", "DEBITO", "Custos fixos"),
    (6, "Gastos com Ocupacao", "DEBITO", "Custos fixos"),
    (7, "Gastos com Servicos de Terceiros", "DEBITO", "Custos fixos"),
    (8, "Gastos com Marketing", "DEBITO", "Custos fixos"),
    (9, "Receitas nao Operacionais", "CREDITO", "Resultado nao operacional"),
    (10, "Gastos nao Operacionais", "DEBITO", "Resultado nao operacional"),
    (11, "Imposto de Renda e CSLL", "DEBITO", "Impostos diretos"),
    (12, "Investimentos", "DEBITO", "Nao listar no DRE"),
    (13, "Transferencias e Ajustes de Saldo", "DEBITO", "Nao listar no DRE"),
    (14, "Transferencias e Ajustes de Saldo", "CREDITO", "Nao listar no DRE"),
]

# (codigo, codigo estruturado, descricao) — categoria deducida do prefixo X de "X.Y".
DEFAULT_ACCOUNT_PLANS = [
    (1, "1.1", "Venda de produtos"),
    (2, "1.2", "Prestacao de servicos"),
    (3, "2.1", "DAS - Simples Nacional"),
    (4, "2.2", "PIS"),
    (5, "2.3", "COFINS"),
    (6, "2.4", "ISS"),
    (7, "2.5", "IPI"),
    (8, "2.6", "ICMS"),
    (9, "3.1", "Devolucoes de clientes"),
    (10, "3.2", "Taxa de maquina de cartao"),
    (11, "3.3", "Taxa de aplicativos"),
    (12, "3.4", "Comissoes para vendedores"),
    (13, "4.1", "Mercadoria para revenda"),
    (14, "4.2", "Materia-prima"),
    (15, "4.3", "Insumos"),
    (16, "4.4", "Mao de obra variavel"),
    (17, "5.1", "Pro-Labore"),
    (18, "5.2", "Encargos sociais e trabalhistas"),
    (19, "5.3", "Salario"),
    (20, "5.4", "Transporte"),
    (21, "5.5", "Alimentacao"),
    (22, "5.6", "Saude"),
    (23, "6.1", "Agua"),
    (24, "6.2", "Aluguel, condominio, IPTU"),
    (25, "6.3", "Telefone + internet"),
    (26, "6.4", "Limpeza e conservacao"),
    (27, "6.5", "Energia eletrica"),
    (28, "7.1", "Contabilidade"),
    (29, "7.2", "Servicos juridicos"),
    (30, "7.3", "Consultoria"),
    (31, "8.1", "Anuncios"),
    (32, "8.2", "Propaganda"),
    (33, "8.3", "Campanhas"),
    (34, "9.1", "Juros de aplicacao"),
    (35, "9.2", "Outras receitas nao operacionais"),
    (36, "10.1", "Juros por atraso"),
    (37, "10.2", "Tarifas bancarias"),
    (38, "10.3", "Outros gastos nao operacionais"),
    (39, "11.1", "IRPJ"),
    (40, "11.2", "CSLL"),
    (41, "12.1", "Investimentos gerais"),
    (42, "13.1", "Transferencia entre contas proprias - efetuadas"),
    (43, "13.2", "Ajuste de saldo"),
    (44, "14.1", "Transferencia entre contas proprias - recebidas"),
    (45, "14.2", "Ajuste de saldo"),
    (46, "4.5", "Manutencao de maquinas e equipamentos"),
    (47, "4.6", "Frete"),
    (48, "12.2", "Sistemas de Gestao"),
    (49, "4.7", "Combustivel"),
    (50, "4.8", "Materiais de escritorio"),
    (51, "4.9", "Manutencao de veiculos"),
    (52, "6.6", "Manutencao do pavilhao"),
    (53, "3.5", "Sistemas de gestao"),
    (54, "5.7", "Uniformes"),
]


def ensure_default_account_plan():
    """Semeia categorias + contas do legado. Idempotente: so insere o que falta
    (chave: `code` / `structured_code`). Nunca altera nem apaga edicao do usuario."""
    for code, description, indicator, dre_range in DEFAULT_ACCOUNT_CATEGORIES:
        if not db.session.query(AccountCategory).filter_by(code=code).first():
            db.session.add(AccountCategory(
                code=code, description=description,
                indicator=indicator, dre_range=dre_range,
            ))
    db.session.flush()
    by_code = {c.code: c for c in db.session.query(AccountCategory).all()}
    for code, structured, description in DEFAULT_ACCOUNT_PLANS:
        if db.session.query(AccountPlan).filter_by(structured_code=structured).first():
            continue
        if db.session.query(AccountPlan).filter_by(code=code).first():
            continue
        try:
            parent_code = int(str(structured).split(".")[0])
        except (ValueError, IndexError):
            continue
        parent = by_code.get(parent_code)
        if not parent:
            continue
        db.session.add(AccountPlan(
            code=code, structured_code=structured,
            description=description, category_id=parent.id,
        ))
    db.session.commit()


class Sale(db.Model):
    """Venda gerada no Comercial (botao "Gerar venda").

    Nasce concluida: grava `clients.sale_concluded_at`/`closed_at`, cria as
    contas a receber (entrada + parcelas) e os cards de producao (um por
    ambiente vendido). `code` e o numero visivel V-0001, V-0002...
    """

    __tablename__ = "sales"
    id = db.Column(String(36), primary_key=True, default=new_uuid)
    code = db.Column(String(20), nullable=False, unique=True)
    client_id = db.Column(
        String(36), ForeignKey("clients.id", ondelete="SET NULL"), nullable=False, index=True
    )
    seller_id = db.Column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    partner_id = db.Column(
        String(36), ForeignKey("partners.id", ondelete="SET NULL"), nullable=True, index=True
    )
    lead_source = db.Column(String(120), nullable=True, default="")
    sale_date = db.Column(Date, nullable=False)
    total_value = db.Column(Numeric(14, 2), nullable=False, default=0)
    down_payment = db.Column(Numeric(14, 2), nullable=False, default=0)
    installments = db.Column(Integer, nullable=False, default=0)
    installment_value = db.Column(Numeric(14, 2), nullable=False, default=0)
    bank_account_id = db.Column(
        String(36), ForeignKey("bank_accounts.id", ondelete="SET NULL"), nullable=True, index=True
    )
    address = db.Column(Text, nullable=True, default="")
    delivery_date = db.Column(Date, nullable=True)
    concluded_at = db.Column(DateTime, nullable=False, default=utcnow, index=True)
    created_by = db.Column(String(80), nullable=True, default="")

    client = db.relationship("Client")
    seller = db.relationship("User", foreign_keys=[seller_id])
    partner = db.relationship("Partner")
    bank = db.relationship("BankAccount")

    def to_dict(self):
        return {
            "id": self.id,
            "code": self.code,
            "client_id": self.client_id,
            "client_name": self.client.name if self.client else None,
            "seller_id": self.seller_id,
            "seller_name": self.seller.username if self.seller else None,
            "partner_id": self.partner_id,
            "partner_name": self.partner.name if self.partner else None,
            "lead_source": self.lead_source or "",
            "sale_date": iso(self.sale_date),
            "total_value": num(self.total_value),
            "down_payment": num(self.down_payment),
            "installments": self.installments,
            "installment_value": num(self.installment_value),
            "bank_account_id": self.bank_account_id,
            "bank_account_name": self.bank.name if self.bank else None,
            "address": self.address or "",
            "delivery_date": iso(self.delivery_date),
            "concluded_at": iso(self.concluded_at),
            "created_by": self.created_by or "",
            "environments": [{"id": e.id, "name": e.name} for e in self.environments],
            "items": [i.to_dict() for i in self.items],
            "installments_list": [
                {
                    "id": si.id,
                    "due_date": iso(si.due_date),
                    "value": num(si.value),
                    "status": si.status,
                    "financial_record_id": si.financial_record_id,
                }
                for si in self.installments_list
            ],
        }


class SaleInstallment(db.Model):
    """Parcela da venda, com vencimento explicito e vinculo ao contas a receber."""

    __tablename__ = "sale_installments"
    id = db.Column(String(36), primary_key=True, default=new_uuid)
    sale_id = db.Column(
        String(36), ForeignKey("sales.id", ondelete="CASCADE"), nullable=False, index=True
    )
    due_date = db.Column(Date, nullable=False)
    value = db.Column(Numeric(14, 2), nullable=False, default=0)
    status = db.Column(String(10), nullable=False, default="PENDENTE")  # PENDENTE | PAGO
    financial_record_id = db.Column(
        String(36), ForeignKey("financial_records.id", ondelete="SET NULL"), nullable=True, index=True
    )

    sale = db.relationship(
        "Sale",
        backref=db.backref("installments_list", cascade="all, delete-orphan", passive_deletes=False),
    )


class SaleEnvironment(db.Model):
    """Ambiente vendido (Sala, Cozinha...) — vira um card de producao."""

    __tablename__ = "sale_environments"
    id = db.Column(String(36), primary_key=True, default=new_uuid)
    sale_id = db.Column(
        String(36), ForeignKey("sales.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name = db.Column(String(120), nullable=False)

    sale = db.relationship(
        "Sale",
        backref=db.backref("environments", cascade="all, delete-orphan", passive_deletes=False),
    )


class SaleItem(db.Model):
    """Produto vendido na venda — snapshot de nome/preco para nao quebrar historico."""

    __tablename__ = "sale_items"
    id = db.Column(String(36), primary_key=True, default=new_uuid)
    sale_id = db.Column(
        String(36), ForeignKey("sales.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_id = db.Column(
        String(36), ForeignKey("products.id", ondelete="SET NULL"), nullable=True, index=True
    )
    name = db.Column(String(200), nullable=False)
    quantity = db.Column(Numeric(14, 3), nullable=False, default=1)
    unit_price = db.Column(Numeric(14, 2), nullable=False, default=0)

    sale = db.relationship(
        "Sale",
        backref=db.backref("items", cascade="all, delete-orphan", passive_deletes=False),
    )

    @property
    def subtotal(self):
        return (num(self.quantity) or 0) * (num(self.unit_price) or 0)

    def to_dict(self):
        return {
            "id": self.id,
            "sale_id": self.sale_id,
            "product_id": self.product_id,
            "name": self.name,
            "quantity": num(self.quantity),
            "unit_price": num(self.unit_price),
            "subtotal": self.subtotal,
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


class StockLoss(db.Model):
    """Perda ou avaria de estoque.

    Registrar uma perda SEMPRE decrementa `StockItem.quantity` e grava um
    `StockMovement` tipo PERDA na MESMA transacao (ver stock_bp.create_loss):
    o historico de movimentacoes continua sendo a fonte unica do que aconteceu
    com o estoque, e a perda guarda o motivo e o custo para o relatorio.
    """

    __tablename__ = "stock_losses"
    id = db.Column(String(36), primary_key=True, default=new_uuid)
    stock_item_id = db.Column(
        String(36), ForeignKey("stock_items.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    quantity = db.Column(Numeric(14, 3), nullable=False)
    kind = db.Column(String(10), nullable=False)  # PERDA | AVARIA
    reason = db.Column(Text, nullable=True, default="")
    cost = db.Column(Numeric(14, 2), nullable=True, default=0)
    loss_date = db.Column(Date, nullable=False, default=date.today)
    created_by = db.Column(String(80), nullable=True, default="")
    created_at = db.Column(DateTime, nullable=False, default=utcnow)

    item = db.relationship("StockItem")

    def to_dict(self):
        return {
            "id": self.id,
            "stock_item_id": self.stock_item_id,
            "item_name": self.item.name if self.item else None,
            "item_sku": self.item.sku if self.item else None,
            "unit": self.item.unit if self.item else None,
            "quantity": num(self.quantity),
            "kind": self.kind,
            "reason": self.reason,
            "cost": num(self.cost),
            "loss_date": iso(self.loss_date),
            "created_by": self.created_by,
            "created_at": iso(self.created_at),
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
    # Campos de montagem (tipo MONTAGEM): qual equipe vai e onde. Texto livre
    # por decisao do plano — equipe nao e usuario do sistema.
    team = db.Column(String(120), nullable=True)
    location = db.Column(String(200), nullable=True)
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
            "team": self.team,
            "location": self.location,
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


# ── Convencao de ganho/perdido no funil ──────────────────────────────
# O funil nao tem flag de ganho/perdido: as colunas so trazem column_key e
# position. E a ultima coluna por posicao pode ser a de PERDA (o funil CRM
# padrao termina em "PERDIDO"), entao "ultima coluna" NAO significa "venda
# fechada". Tratar posicao como venda contava negocio perdido como venda
# realizada e criava projeto para cliente perdido.
WON_FUNNEL_KEYS = {"FECHAMENTO", "FECHADO", "GANHO", "VENDIDO", "CLIENTE", "CONCLUIDO"}
LOST_FUNNEL_KEYS = {"PERDIDO", "PERDA", "CANCELADO", "DESISTIU", "DESISTENCIA"}


def is_won_status(column_key, last_key=None):
    """True se a etapa do funil representa venda ganha.

    Perda explicita nunca conta como ganho. Chave conhecida de ganho conta.
    Qualquer outra so conta se for a ultima coluna do funil — comportamento
    antigo, preservado para funis com nomes proprios.
    """
    if not column_key:
        return False
    key = str(column_key).upper()
    if key in LOST_FUNNEL_KEYS:
        return False
    if key in WON_FUNNEL_KEYS:
        return True
    return bool(last_key) and key == str(last_key).upper()


def is_lost_status(column_key):
    """True se a etapa do funil representa perda explicita."""
    return bool(column_key) and str(column_key).upper() in LOST_FUNNEL_KEYS


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


class SalesGoal(db.Model):
    """Meta de vendas do planejamento comercial.

    Diferente de BudgetGoal, que e orcamento de DESPESA por categoria — aqui e
    meta de RECEITA, com escopo geral/vendedor/parceiro.
    month=None significa meta do ano inteiro.
    """
    __tablename__ = "sales_goals"
    id = db.Column(String(36), primary_key=True, default=new_uuid)
    year = db.Column(Integer, nullable=False)
    month = db.Column(Integer, nullable=True)
    scope = db.Column(String(20), nullable=False, default="GERAL")  # GERAL|VENDEDOR|PARCEIRO
    user_id = db.Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    partner_id = db.Column(String(36), ForeignKey("partners.id", ondelete="CASCADE"), nullable=True, index=True)
    target_value = db.Column(Numeric(14, 2), nullable=False, default=0)
    created_at = db.Column(DateTime, nullable=False, default=utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "year": self.year,
            "month": self.month,
            "scope": self.scope,
            "user_id": self.user_id,
            "partner_id": self.partner_id,
            "target_value": num(self.target_value),
            "created_at": iso(self.created_at),
        }


class Proposal(db.Model):
    """Proposta comercial enviada ao cliente.

    Nasce antes do projeto: `project_id` so e preenchido quando o cliente aceita
    e o projeto e criado. `sent_channel` diz por onde saiu de verdade (WHATSAPP
    pela Evolution API, WA_ME pelo link, ou MANUAL) — nunca fica implicito.
    """
    __tablename__ = "proposals"
    id = db.Column(String(36), primary_key=True, default=new_uuid)
    number = db.Column(String(40), nullable=False)
    client_id = db.Column(String(36), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id = db.Column(String(36), ForeignKey("projects.id", ondelete="SET NULL"), nullable=True, index=True)
    status = db.Column(String(20), nullable=False, default="RASCUNHO", index=True)
    total_value = db.Column(Numeric(14, 2), nullable=False, default=0)
    valid_until = db.Column(Date, nullable=True)
    notes = db.Column(Text, nullable=True, default="")
    sent_at = db.Column(DateTime, nullable=True)
    sent_channel = db.Column(String(20), nullable=True)
    created_by = db.Column(String(80), nullable=True, default="")
    created_at = db.Column(DateTime, nullable=False, default=utcnow)

    client = db.relationship("Client")
    items = db.relationship("ProposalItem", cascade="all, delete-orphan",
                            passive_deletes=False, order_by="ProposalItem.position",
                            backref="proposal")

    @property
    def computed_total(self):
        """Total somado dos itens — a fonte da verdade do valor da proposta."""
        return round(sum((num(i.quantity) or 0) * (num(i.unit_price) or 0)
                         for i in self.items), 2)

    def to_dict(self):
        return {
            "id": self.id, "number": self.number,
            "client_id": self.client_id,
            "client_name": self.client.name if self.client else None,
            "project_id": self.project_id,
            "status": self.status,
            "total_value": num(self.total_value),
            "items_total": self.computed_total,
            "valid_until": self.valid_until.isoformat() if self.valid_until else None,
            "notes": self.notes or "",
            "sent_at": iso(self.sent_at),
            "sent_channel": self.sent_channel or "",
            "created_by": self.created_by or "",
            "created_at": iso(self.created_at),
            "items": [i.to_dict() for i in self.items],
        }


class ProposalItem(db.Model):
    __tablename__ = "proposal_items"
    id = db.Column(String(36), primary_key=True, default=new_uuid)
    proposal_id = db.Column(String(36), ForeignKey("proposals.id", ondelete="CASCADE"), nullable=False, index=True)
    description = db.Column(String(255), nullable=False)
    quantity = db.Column(Numeric(14, 2), nullable=False, default=0)
    unit_price = db.Column(Numeric(14, 2), nullable=False, default=0)
    position = db.Column(Integer, nullable=False, default=0)
    created_at = db.Column(DateTime, nullable=False, default=utcnow)

    @property
    def subtotal(self):
        return round((num(self.quantity) or 0) * (num(self.unit_price) or 0), 2)

    def to_dict(self):
        return {"id": self.id, "proposal_id": self.proposal_id,
                "description": self.description,
                "quantity": num(self.quantity), "unit_price": num(self.unit_price),
                "position": self.position, "subtotal": self.subtotal}


class AppSetting(db.Model):
    """Chave/valor de configuracao editavel pelo ADMIN (ex.: Evolution API).

    Fica em tabela e nao em variavel de ambiente porque o cliente troca a
    instancia do WhatsApp sem deploy. Leitura devolve mascarado (ver blueprint).
    """
    __tablename__ = "app_settings"
    id = db.Column(String(36), primary_key=True, default=new_uuid)
    key = db.Column(String(80), nullable=False, unique=True, index=True)
    value = db.Column(Text, nullable=True)
    updated_at = db.Column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    def to_dict(self):
        return {"id": self.id, "key": self.key, "value": self.value or "",
                "updated_at": iso(self.updated_at)}


class CommissionRule(db.Model):
    """Regra de comissao: percentual com vigencia, para vendedor OU parceiro.

    E regra, nao valor congelado: mudar o percentual no mes que vem nao reescreve
    o que ja foi pago nos meses anteriores.
    """
    __tablename__ = "commission_rules"
    id = db.Column(String(36), primary_key=True, default=new_uuid)
    seller_id = db.Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    partner_id = db.Column(String(36), ForeignKey("partners.id", ondelete="SET NULL"), nullable=True, index=True)
    percent = db.Column(Numeric(6, 2), nullable=False, default=0)
    valid_from = db.Column(Date, nullable=True)
    valid_until = db.Column(Date, nullable=True)
    active = db.Column(Boolean, nullable=False, default=True)
    notes = db.Column(Text, nullable=True, default="")
    created_at = db.Column(DateTime, nullable=False, default=utcnow)

    seller = db.relationship("User")
    partner = db.relationship("Partner")

    def to_dict(self):
        return {
            "id": self.id,
            "seller_id": self.seller_id,
            "seller_name": self.seller.username if self.seller else None,
            "partner_id": self.partner_id,
            "partner_name": self.partner.name if self.partner else None,
            "percent": num(self.percent),
            "valid_from": self.valid_from.isoformat() if self.valid_from else None,
            "valid_until": self.valid_until.isoformat() if self.valid_until else None,
            "active": bool(self.active),
            "notes": self.notes or "",
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


class SatisfactionSurvey(db.Model):
    """Pesquisa de satisfacao pos-entrega (Fase 8).

    Uma linha por envio. O envio pode ser por WhatsApp (o botao reusa o fluxo
    da proposta) ou direto; a resposta chega com `score`/`comment` preenchidos
    e `answered_at` gravado. Sem resposta = `answered_at` NULL.
    """
    __tablename__ = "satisfaction_surveys"
    id = db.Column(String(36), primary_key=True, default=new_uuid)
    client_id = db.Column(String(36), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id = db.Column(String(36), ForeignKey("projects.id", ondelete="SET NULL"), nullable=True, index=True)
    ticket_id = db.Column(String(36), ForeignKey("service_tickets.id", ondelete="SET NULL"), nullable=True)
    score = db.Column(Integer, nullable=True)  # 1 a 5
    comment = db.Column(Text, nullable=True, default="")
    sent_at = db.Column(DateTime, nullable=False, default=utcnow)
    answered_at = db.Column(DateTime, nullable=True)
    created_at = db.Column(DateTime, nullable=False, default=utcnow)
    client = db.relationship("Client", backref=db.backref("satisfaction_surveys", cascade="all, delete-orphan", passive_deletes=False))
    project = db.relationship("Project")
    ticket = db.relationship("ServiceTicket")

    def to_dict(self):
        return {
            "id": self.id,
            "client_id": self.client_id,
            "client_name": self.client.name if self.client else None,
            "project_id": self.project_id,
            "project_title": self.project.title if self.project else None,
            "ticket_id": self.ticket_id,
            "ticket_number": self.ticket.number if self.ticket else None,
            "score": self.score,
            "comment": self.comment or "",
            "sent_at": iso(self.sent_at),
            "answered_at": iso(self.answered_at),
            "answered": self.answered_at is not None,
            "created_at": iso(self.created_at),
        }


class WhatsappInstance(db.Model):
    """Instancia do WhatsApp na Evolution API (uma por tenant; aqui: eme-moveis).

    Guarda o `hash` devolvido no create (chave propria da instancia) e o
    estado conhecido. O QR code NUNCA e persistido: vale ~3 min, entao o
    endpoint /qr busca um novo a cada chamada (GET /instance/connect).
    """
    __tablename__ = "whatsapp_instances"
    id = db.Column(String(36), primary_key=True, default=new_uuid)
    name = db.Column(String(80), nullable=False, unique=True, index=True)
    api_key = db.Column(Text, nullable=True, default="")  # hash da instancia
    status = db.Column(String(20), nullable=False, default="desconectada")
    phone = db.Column(String(30), nullable=True, default="")
    created_at = db.Column(DateTime, nullable=False, default=utcnow)
    updated_at = db.Column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)

    def to_dict(self, include_key=False):
        d = {
            "id": self.id,
            "name": self.name,
            "status": self.status,
            "phone": self.phone or "",
            "created_at": iso(self.created_at),
            "updated_at": iso(self.updated_at),
        }
        if include_key:
            d["has_key"] = bool(self.api_key)
        return d


class WhatsappConversation(db.Model):
    """Conversa com um numero de WhatsApp (uma linha por telefone+instancia).

    NAO cria Client sozinho a partir do trafego (regra do produto): quando o
    telefone normalizado bate com UM unico cliente, `client_id` aponta para
    ele (link de leitura); se bater com mais de um, fica NULL (ambiguo).
    """
    __tablename__ = "whatsapp_conversations"
    id = db.Column(String(36), primary_key=True, default=new_uuid)
    instance = db.Column(String(80), nullable=False, default="eme-moveis", index=True)
    phone = db.Column(String(30), nullable=False, index=True)  # so digitos
    name = db.Column(String(160), nullable=True, default="")  # pushName / perfil
    client_id = db.Column(String(36), ForeignKey("clients.id", ondelete="SET NULL"), nullable=True, index=True)
    last_message_at = db.Column(DateTime, nullable=True)
    created_at = db.Column(DateTime, nullable=False, default=utcnow)
    client = db.relationship("Client")
    __table_args__ = (UniqueConstraint("instance", "phone", name="uq_waconv_instance_phone"),)

    def to_dict(self, last=None, unread=0):
        return {
            "id": self.id,
            "instance": self.instance,
            "phone": self.phone,
            "name": self.name or "",
            "client_id": self.client_id,
            "client_name": self.client.name if self.client else None,
            "last_message_at": iso(self.last_message_at),
            "last_body": (last.body if last else "") or "",
            "last_direction": last.direction if last else "",
            "unread": unread,
            "created_at": iso(self.created_at),
        }


class WhatsappMessage(db.Model):
    """Mensagem de uma conversa (in = recebida, out = enviada pelo ERP).

    `provider_id` e o id da Evolution: unique = dedupe de redelivery do
    webhook. Midia de SAIDA fica em disco (UPLOAD_DIR, mesmo padrao dos
    anexos); midia de ENTRADA guarda kind/caption/mimetype — os bytes sao
    buscados sob demanda (fase 2), nunca inventados.
    """
    __tablename__ = "whatsapp_messages"
    id = db.Column(String(36), primary_key=True, default=new_uuid)
    conversation_id = db.Column(String(36), ForeignKey("whatsapp_conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    provider_id = db.Column(String(120), nullable=True, unique=True, index=True)
    remote_jid = db.Column(String(120), nullable=True)  # chave p/ buscar midia na Evolution sob demanda
    direction = db.Column(String(8), nullable=False, default="in")  # in | out
    kind = db.Column(String(16), nullable=False, default="text")  # text|image|audio|video|document
    body = db.Column(Text, nullable=True, default="")
    media_stored = db.Column(String(255), nullable=True)  # arquivo em UPLOAD_DIR (saida)
    media_filename = db.Column(String(255), nullable=True)
    media_mime = db.Column(String(120), nullable=True)
    media_size = db.Column(Integer, nullable=True)
    status = db.Column(String(20), nullable=False, default="stored")  # stored|sent|failed
    created_by = db.Column(String(80), nullable=True, default="")
    created_at = db.Column(DateTime, nullable=False, default=utcnow)
    conversation = db.relationship(
        "WhatsappConversation",
        backref=db.backref("messages", cascade="all, delete-orphan", passive_deletes=False),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "conversation_id": self.conversation_id,
            "provider_id": self.provider_id,
            "direction": self.direction,
            "kind": self.kind,
            "body": self.body or "",
            "has_media": bool(self.media_stored),
            "media_pending": bool(self.direction == "in" and self.kind != "text"
                                 and not self.media_stored),
            "media_filename": self.media_filename or "",
            "media_mime": self.media_mime or "",
            "media_size": self.media_size,
            "status": self.status,
            "created_by": self.created_by or "",
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
    ("WhatsApp sincronizado com o celular",
     "Correção (pedido do dono): o que você manda pelo celular agora aparece no ERP — antes só a resposta do cliente entrava, porque a mensagem enviada pelo aparelho pareado era descartada. Também entrou o botão Sincronizar na conversa: ele puxa o histórico da Evolution (até 200 mensagens) para trazer o que foi falado antes de conectar ou com o sistema fora — dá para usar o celular e o ERP juntos sem perder mensagem, e o que já está no banco não duplica.",
     "CORRECAO", "2026-10-06"),
    ("WhatsApp com cara de WhatsApp Web",
     "A aba Conversas foi redesenhada: lista com avatar de iniciais, hora/data da última mensagem, prévia com 'Você:' e bolinha de não-lidas; conversa com bolhas verdes (suas) e cinzas (recebidas), divisores de dia (Hoje/Ontem/data), hora com duplo-tique nas enviadas e barra de digitação arredondada — tudo no tema escuro do sistema. A conversa mais recente abre sozinha.",
     "NOVIDADE", "2026-10-06"),
    ("Dashboard abre no mês e período mensal/trimestral/semestral/anual",
     "Correção + novidade (pedido do vídeo): o Dashboard Executivo mostrava no mês números do ano inteiro — no dia 1º, sem vender nada, apareciam 2 vendas. Agora o painel abre no mês corrente e o que aparece é só do período: dá para trocar entre mensal, trimestral, semestral e anual. O Fluxo de Caixa do Financeiro ganhou o mesmo seletor (antes só filtrava por ano). Venda fechada sem data de fechamento (cadastro antigo) aparece separada, fora da conta do período, para o número não enganar.",
     "MELHORIA", "2026-10-06"),
    ("Cards clicáveis: ver quais vendas e quais contas",
     "Novidade (pedido do vídeo): no Dashboard Executivo, clicar em Vendas realizadas abre a lista de quais vendas fecharam no período e de qual cliente (com valor, data e origem — Gerar venda ou CRM). No Dashboard comercial, os cards Vendas do mês e Vendas do ano abrem a mesma lista. No Financeiro, clicar numa faixa do aging (Vencidas, Vence em até 7 dias etc.) filtra a lista abaixo para mostrar exatamente quais contas estão naquela faixa; clicar de novo limpa o filtro.",
     "NOVIDADE", "2026-10-06"),
    ("Comercial: vendas do mês/ano, orçamentos e pizza por origem",
     "O Dashboard comercial ganhou 3 cards novos: Vendas do mês (total vendido no mês), Vendas do ano (total no ano) e Orçamentos enviados (quantidade, valor total e quantos foram aceitos — conta proposta enviada ou aceita da aba Propostas). Também entraram dois gráficos: a evolução das vendas mês a mês no ano e uma pizza de vendas por origem em valor (indicação, arquiteto, Instagram etc. — agora pelo valor vendido, não só pela quantidade de leads). Dá para trocar o ano e ver mensal, trimestral, semestral ou anual.",
     "NOVIDADE", "2026-10-05"),
    ("Financeiro e Produção: novos indicadores e período em todo o sistema",
     "No relatório Financeiro entraram Faturamento (tudo que foi vendido/faturado), Recebimentos (o que efetivamente entrou em caixa), Margem de contribuição (recebido menos custos variáveis pagos — conta do plano com código 4 ou categoria Custos Variáveis) e Inadimplência (valores em aberto com vencimento passado, com quantidade de títulos). Os mesmos 4 aparecem como cards no Dashboard financeiro. Na Produção saíram do resumo o Total de horas e as Horas improdutivas; entraram Projetos em produção, Projetos atrasados (quantidade + valor), Entregas previstas (próximas 5 com cliente e prazo), Retrabalho com horas perdidas, Desperdício com material perdido, Perdas financeiras em R$, Pendências de produção (checklist em aberto) e o total produzido no mês e no ano com gráfico de evolução da capacidade. O seletor de período mensal/trimestral/semestral/anual, que só existia no DRE, agora está nos dashboards comercial, produção e financeiro e no filtro rápido da Central de Relatórios.",
     "NOVIDADE", "2026-10-05"),
    ("Gerar venda no Comercial com automações",
     "O botão Concluir venda virou Gerar venda: ao fechar uma negociação, uma tela completa cadastra a venda — cliente, vendedor, arquiteto/parceiro, origem, data, valor total, condições de pagamento (entrada, parcelas com vencimento próprio e conta bancária de destino), produtos vendidos, ambientes, endereço da obra e data prevista de entrega. Ao concluir, o sistema cria na hora as contas a receber no Financeiro (entrada + parcelas) e um card de produção para cada ambiente vendido (apartamento com cozinha, sala, banheiro e quarto vira 4 cards, para acompanhar a produção de cada móvel separado). Os relatórios passam a atualizar só nessa conclusão: arrastar o card para a etapa de ganho no funil não muda mais meta, comissão e CRM. Também entrou a aba Produtos/Móveis no Comercial (cadastro do catálogo que a venda usa), o gráfico de Produtos mais vendidos no Dashboard comercial e o relatório Produtos vendidos em Relatórios.",
     "NOVIDADE", "2026-10-01"),
    ("Plano de contas importado para o Financeiro",
     "As categorias do DRE e o plano de contas oficial agora fazem parte do sistema: 14 categorias (Receita com Vendas, Impostos Sobre Vendas, Custos Variáveis, Gastos com Pessoal etc.) e 54 contas no formato X.Y (ex.: 4.2 – Matéria-prima). No lançamento financeiro, o campo Plano de Contas virou uma lista organizada por categoria. A nova aba Plano de contas no Financeiro mostra tudo com a faixa de cada categoria no DRE (inclusive as que não entram no demonstrativo), e ADMIN/GERENTE podem ajustar ou restaurar o padrão — contas já usadas em lançamentos não podem ser excluídas.",
     "NOVIDADE", "2026-10-01"),
    ("Gráficos legíveis no escuro e DRE com despesas por mês",
     "Correção: nos gráficos de categorias, nomes longos eram cortados no eixo e o valor no tooltip saía em preto no modo escuro, impossível de ler — agora o nome encurta com reticências (o completo aparece ao passar o mouse) e todo o texto do tooltip é claro. No DRE, a coluna de despesas por categoria saiu da tabela: agora dá para clicar no período e abrir o detalhamento das despesas daquele mês aninhado na linha.",
     "CORRECAO", "2026-09-30"),
    ("Dashboards com mais gráficos e DRE detalhado",
     "Dashboard Executivo: o demonstrativo mensal virou o resultado dos últimos 12 meses em barras, com receitas, despesas e resultado — passe o mouse em qualquer barra e veja o valor. Financeiro: o gráfico do fluxo de caixa ganhou linha de saldo acumulado e tooltip completo por mês (entradas, saídas, saldo, acumulado e o que está em aberto), mais dois gráficos novos de receitas e despesas por categoria com participação. DRE: agora mostra de onde veio cada real (categorias de receita), para onde foi cada real (categorias de despesa), margem líquida, principal receita e principal despesa, com gráfico por período e barras por categoria. Produção: saíram as horas produtivas e o total de m² — a casa não mensura por eles; entraram gráficos de ocorrências por tipo e custo das ocorrências, e a tabela detalha o valor de cada projeto.",
     "MELHORIA", "2026-09-30"),
    ("Ticket médio corrigido no Comercial",
     "O ticket médio estava zerado porque contava apenas projetos com o status literal CONCLUIDO — e a conclusão real pelo botão usa um marcador próprio do projeto. Agora o ticket usa as vendas realmente concluídas pelo botão; quando ainda não há projeto concluído, usa as vendas fechadas no funil de vendas. O card mostra quantas vendas entraram, o total faturado e a base usada.",
     "CORRECAO", "2026-09-30"),
    ("Pós-venda completo: dashboard, agenda, check-ins e pendências",
     "Fase 8 entregue. O Pós-venda agora tem 8 abas: Projetos entregues, Dashboard (satisfação, garantias, follow-ups, chamados), Agenda de pós-venda (concluir um projeto agenda os contatos de 7 e 30 dias sozinho; dá para gerar, concluir e configurar os dias), Check-ins (ligação, visita ou WhatsApp, feitos × programados), Pesquisa de satisfação (envio, resposta e botão WhatsApp), Solicitações, Garantias (prazo em meses por projeto, chamado coberto sozinho) e Pendências (chamados por tempo e atrasados).",
     "NOVIDADE", "2026-09-28"),
    ("Pós-venda — pesquisa de satisfação e garantia dos projetos",
     "Fase 8 (parte 1). Pesquisa de satisfação: envie por cliente/projeto, registre a resposta (nota 1 a 5 e comentário) e acompanhe o resumo — média, distribuição e % de respondentes. Garantia: ao concluir um projeto, informe os meses de garantia e a data-limite é calculada automaticamente; os chamados de um projeto em garantia são marcados como cobertos. As vendas que já tinham sido concluídas pelo botão são corrigidas automaticamente na migração.",
     "NOVIDADE", "2026-09-28"),
    ("Venda concluída conta nos dashboards + venda para fornecedor",
     "Correção: a venda fechada pelo botão Concluir venda criava o projeto na Produção mas não aparecia no Dashboard inicial nem no Dashboard comercial — agora ela entra na meta, na comissão e no relatório de CRM como qualquer venda fechada, e as vendas que já tinham passado pelo botão foram corrigidas. Novidade: no funil de vendas dá para vender para cliente ou para fornecedor, independente — o modal Vincular tem as duas abas e o fornecedor caminha no mesmo funil.",
     "CORRECAO", "2026-09-28"),
    ("Estoque completo: perdas, mínimo e dashboard",
     "Fase 7 entregue. Aba Perdas/Avarias: registrar perda ou avaria baixa o estoque e grava a movimentação na mesma operação, com motivo, custo e total de prejuízo por período e por motivo. Aba Estoque mínimo: itens abaixo do mínimo ordenados por criticidade, com quantidade sugerida e botão Gerar pedido de compra (nasce em Compras como SOLICITADA). Aba Dashboard: valor em estoque, itens críticos e prejuízo. No Comercial, o modal Vincular Cliente agora recarrega o cadastro central ao abrir: cliente recém-cadastrado aparece no select sem recarregar a tela.",
     "NOVIDADE", "2026-09-28"),
    ("Concluir venda e concluir projeto",
     "Dois botões explícitos fecham o caminho do serviço: no Comercial, \"Concluir venda\" cria o projeto e tira o card do funil de vendas; na Produção, \"Concluir projeto\" tira o card da produção e o entrega na nova aba \"Projetos entregues\", no Pós-venda — de onde dá para reabrir, se precisar. A conclusão é um estado próprio do projeto, e não o nome da coluna do funil: como as colunas podem ser renomeadas a qualquer momento, amarrar a conclusão ao nome delas daria resultado errado.",
     "NOVIDADE", "2026-09-25"),
    ("Anexos maiores no cliente e no funil",
     "O limite de anexo subiu para 50 MB. Antes, qualquer arquivo acima de 1 MB era recusado pelo servidor de arquivos estáticos, antes mesmo de chegar ao sistema — e a mensagem na tela dizia 25 MB, número que não tinha relação com o bloqueio real. Agora o limite mostrado na tela é o que vale de verdade, e a mensagem de recusa informa o número certo.",
     "CORRECAO", "2026-09-25"),
    ("Montagens com equipe e local",
     "A montagem agora registra qual equipe vai e o endereço, e ganhou uma aba própria em Produção com filtro por equipe e por mês. O que é criado ali aparece também na Agenda.",
     "NOVIDADE", "2026-09-24"),
    ("Pendências de produção num só lugar",
     "Ocorrências de todos os projetos (retrabalho, desperdício e perda) com o custo somado do período, mais os itens de checklist ainda em aberto — para saber o que está travando sem abrir projeto por projeto.",
     "NOVIDADE", "2026-09-24"),
    ("Contas a pagar e a receber com aging",
     "As duas abas mostram o que está em aberto e há quanto tempo: vencidas, vence em até 7 dias, de 8 a 30 dias e acima de 30 dias. Lançamento sem data de vencimento aparece separado, para a soma não mentir.",
     "NOVIDADE", "2026-09-24"),
    ("Cotações comparadas lado a lado",
     "Na aba Cotações, vários fornecedores para a mesma compra ficam lado a lado, com o menor preço de cada item destacado. Aprovar uma cotação leva os preços dela para o pedido — e a economia do dashboard passa a ser medida, não estimada.",
     "NOVIDADE", "2026-09-24"),
    ("Calendário logístico das compras",
     "Os pedidos aparecem pela data prevista de entrega, do mais atrasado para o mais distante, com transportadora e código de rastreio editáveis na própria linha.",
     "NOVIDADE", "2026-09-24"),
    ("Propostas com PDF e envio por WhatsApp",
     "O orçamento agora vive no sistema: itens, validade e um PDF com a cara da EME. Dá para enviar pelo WhatsApp em um clique — e quando a integração não está configurada, o botão abre o WhatsApp com a mensagem pronta em vez de dar erro.",
     "NOVIDADE", "2026-09-24"),
    ("Comissões por vendedor e parceiro",
     "Regra de percentual com vigência, aplicada sobre as vendas fechadas do mês. Mudar o percentual hoje não altera o que já foi calculado nos meses anteriores.",
     "NOVIDADE", "2026-09-24"),
    ("Planejamento comercial com meta e realizado",
     "Meta do mês ou do ano, geral ou por vendedor/parceiro, com o quanto já foi realizado. Vendas fechadas sem data de fechamento aparecem separadas, para o número não enganar.",
     "NOVIDADE", "2026-09-24"),
    ("Parceiros e arquitetos com cadastro completo",
     "Dá para cadastrar, corrigir contato e desativar quem parou de indicar — e ver o ranking de indicações do período.",
     "NOVIDADE", "2026-09-24"),
    ("Financeiro organizado em abas",
     "Dashboard, Contas a pagar, Contas a receber, Lançamentos, Movimentações, Pendências, Contas bancárias, DRE e Planejamento orçamentário — cada assunto na sua aba, sem precisar rolar uma tela só.",
     "MELHORIA", "2026-09-24"),
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
    ("Cadastro central de clientes e fornecedores",
     "O módulo Clientes/Fornecedores virou o cadastro central: um cliente pode ser marcado como fornecedor e passa a aparecer nos lançamentos de Compras e Financeiro. Nenhum cliente com histórico (projetos, lançamentos, agenda, pós-venda) pode mais ser excluído — o registro fica preservado para referência futura.",
     "NOVIDADE", "2026-09-22"),
    ("Nome dos módulos do menu atualizado",
     "O menu lateral foi renomeado e reorganizado: Dashboard Executivo, Comercial, Financeiro, Produção, Clientes/Fornecedores, Estoque, Compras, Pós-venda, Relatórios, Agenda, Novidades e Acessos & TI.",
     "MELHORIA", "2026-09-22"),
    ("Módulos organizados em abas",
     "Cada módulo agora tem as suas próprias abas internas. No Financeiro: Dashboard financeiro, Contas a pagar, Contas a receber, Lançamentos, Movimentações, Pendências, Contas bancárias, DRE e Planejamento orçamentário. No Comercial: Dashboard comercial, Funil de vendas, Orçamentos/Propostas, Comissões, Parceiros/Arquitetos e Planejamento comercial. O mesmo vale para Produção, Compras, Estoque e Pós-venda. As abas que ainda estão sendo construídas aparecem identificadas — nada ali mostra dado inventado.",
     "MELHORIA", "2026-09-23"),
    ("Painel inicial completo",
     "O Painel Geral agora traz: resumo principal (saldo bancário, contas a receber e a pagar em aberto, faturamento do mês e projetos em produção), fluxo de caixa do mês por semana, meta comercial com percentual atingido, resumo comercial, resumo da produção, o bloco \"O que precisa da minha atenção\" e a Agenda do Dia.",
     "NOVIDADE", "2026-09-23"),
    ("Chat interno de WhatsApp",
     "Nova aba WhatsApp: configure a Evolution uma vez (a instância é criada sozinha), conecte o número pelo QR code e converse com clientes sem sair do ERP — dá para enviar texto, foto e arquivo direto pelo chat. Foto e áudio recebidos mostram preview na conversa e podem ser baixados; mensagem recebida aparece na hora e nada cria cliente sozinho.",
     "NOVIDADE", "2026-09-28"),
    ("Fluxo de caixa por semana",
     "O fluxo de caixa do mês agora pode ser visto semana a semana, com entradas, saídas, saldo de cada semana e saldo acumulado — tanto em Realizado quanto em Projetado.",
     "NOVIDADE", "2026-09-23"),
    ("O que precisa da minha atenção",
     "Um bloco no Painel reúne o que está pendente: contas vencidas, contas vencendo nos próximos dias, chamados de pós-venda em aberto, projetos atrasados e orçamentos sem retorno. Cada item mostra quantos são, o valor envolvido e em qual módulo resolver.",
     "NOVIDADE", "2026-09-23"),
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
