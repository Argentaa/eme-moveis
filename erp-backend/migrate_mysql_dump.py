"""Migra backup_emebd_final.sql (MySQL dump) para o Postgres/SQLite do ERP Flask.

Uso:
  python migrate_mysql_dump.py /caminho/backup_emebd_final.sql [--dry-run]

- Idempotente: pula ids ja existentes (upsert por id).
- Preserva ids/UUIDs, senhas bcrypt, ENUMs, JSON steps, funnel original.
- Ordem FK-safe: users, categories, clients, projects, financial,
  stock_items, stock_movements, calendar, notifications, funnel, recurring.
"""
import json
import os
import re
import sys
from datetime import datetime
from decimal import Decimal

DUMP_DEFAULT = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "..", "eme-moveis", "eme-moveis", "eme-moveis",
    "gerenciamento-eme", "backup_emebd_final.sql",
)

COLUMNS = {
    "users": ["id", "username", "name", "email", "role", "password", "avatar", "created_at"],
    "categories": ["id", "name", "description", "category_type"],
    "clients": ["id", "name", "email", "phone", "cpf_cnpj", "address", "created_at",
                "funnel_status", "lost_reason", "estimated_value", "lead_source"],
    "projects": ["id", "title", "client_id", "description", "status", "value",
                 "deadline", "steps", "created_at"],
    "financial_records": ["id", "description", "type", "category", "amount", "date",
                          "project_id", "status", "due_date"],
    "funnel_columns": ["id", "column_key", "label", "description", "updated_at", "type"],
    "notifications": ["id", "title", "message", "type", "read_at", "user_id",
                      "event_id", "project_id", "created_at"],
    "recurring_financial": ["id", "description", "type", "category", "amount", "frequency",
                            "start_date", "next_date", "project_id", "active", "created_at"],
    "stock_items": ["id", "name", "sku", "category_id", "quantity", "min_quantity",
                    "unit", "price", "supplier"],
    "stock_movements": ["id", "item_id", "type", "quantity", "reason", "created_by", "date"],
    "calendar_events": ["id", "title", "description", "type", "status", "start_date",
                        "start_time", "end_date", "end_time", "project_id", "client_id",
                        "assigned_user_id", "observations", "created_at"],
}

ORDER = ["users", "categories", "clients", "projects", "financial_records",
         "stock_items", "stock_movements", "calendar_events", "notifications",
         "funnel_columns", "recurring_financial"]


def split_tuples(body):
    """Divide VALUES (...) , (...) em tuplas, respeitando strings MySQL."""
    rows, buf = [], []
    depth, in_str, esc = 0, False, False
    for ch in body:
        if in_str:
            buf.append(ch)
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == "'":
                in_str = False
            continue
        if ch == "'":
            in_str = True
            buf.append(ch)
        elif ch == "(":
            if depth == 0:
                buf = []
            else:
                buf.append(ch)
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                rows.append("".join(buf))
                buf = []
            else:
                buf.append(ch)
        elif depth >= 1:
            buf.append(ch)
    return rows


def split_cols(tup):
    cols, buf = [], []
    in_str, esc, depth = False, False, 0
    i = 0
    while i < len(tup):
        ch = tup[i]
        if in_str:
            buf.append(ch)
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == "'":
                if i + 1 < len(tup) and tup[i + 1] == "'":
                    buf.append("'")
                    i += 1
                else:
                    in_str = False
        elif ch == "'":
            in_str = True
            buf.append(ch)
        elif ch == "(":
            depth += 1
            buf.append(ch)
        elif ch == ")":
            depth -= 1
            buf.append(ch)
        elif ch == "," and depth == 0:
            cols.append("".join(buf).strip())
            buf = []
        else:
            buf.append(ch)
        i += 1
    cols.append("".join(buf).strip())
    return cols


def sql_unescape(val):
    if val == "NULL":
        return None
    if len(val) >= 2 and val[0] == "'" and val[-1] == "'":
        s = val[1:-1]
        s = (s.replace("\\\\", "\x00").replace("\\'", "'").replace('\\"', '"')
              .replace("\\n", "\n").replace("\\r", "\r").replace("\\t", "\t")
              .replace("\x00", "\\"))
        return s
    return val


def parse_dump(path):
    txt = open(path, encoding="utf-8", errors="ignore").read()
    out = {}
    for m in re.finditer(r"INSERT INTO `(\w+)` VALUES\s*(.*?);\s*(?:/\*!|\nUNLOCK|\n--|\Z)",
                         txt, re.S):
        table, body = m.group(1), m.group(2).strip()
        if table not in COLUMNS:
            continue
        rows = []
        for tup in split_tuples(body):
            vals = [sql_unescape(c) for c in split_cols(tup)]
            cols = COLUMNS[table]
            if len(vals) != len(cols):
                print(f"AVISO: {table}: {len(vals)} valores vs {len(cols)} colunas — linha pulada")
                continue
            rows.append(dict(zip(cols, vals)))
        out[table] = rows
    return out


def to_decimal(v):
    if v is None or v == "":
        return None
    return Decimal(str(v))


def to_date(v):
    if not v:
        return None
    return datetime.strptime(str(v)[:10], "%Y-%m-%d").date()


def to_time(v):
    if not v:
        return None
    s = str(v).strip()
    for fmt in ("%H:%M:%S", "%H:%M"):
        try:
            return datetime.strptime(s[:8], fmt).time()
        except ValueError:
            pass
    return None


def to_dt(v):
    if not v:
        return None
    s = str(v).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(s[:19], fmt)
        except ValueError:
            pass
    return None


def to_steps(v):
    if not v:
        return []
    if isinstance(v, list):
        return v
    try:
        return json.loads(v)
    except (ValueError, TypeError):
        return []


def main():
    path = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("-") else DUMP_DEFAULT
    path = os.path.abspath(path)
    dry = "--dry-run" in sys.argv
    print(f"dump: {path}")
    data = parse_dump(path)
    for t in ORDER:
        print(f"  {t}: {len(data.get(t, []))} linhas no dump")

    if dry:
        print("dry-run: nada gravado.")
        return

    from app import create_app
    from app.extensions import db
    from app.models.models import (
        CalendarEvent, Category, Client, FinancialRecord, FunnelColumn,
        Notification, Project, RecurringFinancial, StockItem, StockMovement, User,
    )

    app = create_app(os.environ.get("APP_ENV", "prod"))
    MODELS = {
        "users": User, "categories": Category, "clients": Client, "projects": Project,
        "financial_records": FinancialRecord, "stock_items": StockItem,
        "stock_movements": StockMovement, "calendar_events": CalendarEvent,
        "notifications": Notification, "funnel_columns": FunnelColumn,
        "recurring_financial": RecurringFinancial,
    }

    def build(table, r):
        if table == "users":
            return User(id=r["id"], username=r["username"], name=r["name"], email=r["email"],
                        role=r["role"], password=r["password"], avatar=r["avatar"],
                        created_at=to_dt(r["created_at"]) or datetime.now())
        if table == "categories":
            return Category(id=r["id"], name=r["name"], description=r["description"],
                            category_type=r["category_type"])
        if table == "clients":
            return Client(id=r["id"], name=r["name"], email=r["email"] or "",
                          phone=r["phone"] or "", cpf_cnpj=r["cpf_cnpj"] or None,
                          address=r["address"] or "",
                          created_at=to_dt(r["created_at"]) or datetime.now(),
                          funnel_status=r["funnel_status"] or "PROSPECCAO",
                          lost_reason=r["lost_reason"],
                          estimated_value=to_decimal(r["estimated_value"]),
                          lead_source=r["lead_source"])
        if table == "projects":
            return Project(id=r["id"], title=r["title"], client_id=r["client_id"],
                           description=r["description"] or "", status=r["status"],
                           value=to_decimal(r["value"]) or 0,
                           deadline=to_date(r["deadline"]), steps=to_steps(r["steps"]),
                           created_at=to_dt(r["created_at"]) or datetime.now())
        if table == "financial_records":
            return FinancialRecord(id=r["id"], description=r["description"], type=r["type"],
                                   category=r["category"] or "",
                                   amount=to_decimal(r["amount"]) or 0,
                                   date=to_date(r["date"]), project_id=r["project_id"],
                                   status=r["status"], due_date=to_date(r["due_date"]))
        if table == "stock_items":
            return StockItem(id=r["id"], name=r["name"], sku=r["sku"],
                             category_id=r["category_id"],
                             quantity=to_decimal(r["quantity"]) or 0,
                             min_quantity=to_decimal(r["min_quantity"]) or 0,
                             unit=r["unit"] or "un", price=to_decimal(r["price"]) or 0,
                             supplier=r["supplier"] or "")
        if table == "stock_movements":
            return StockMovement(id=r["id"], item_id=r["item_id"], type=r["type"],
                                 quantity=to_decimal(r["quantity"]) or 0,
                                 reason=r["reason"] or "", created_by=r["created_by"] or "",
                                 date=to_dt(r["date"]) or datetime.now())
        if table == "calendar_events":
            return CalendarEvent(id=r["id"], title=r["title"], description=r["description"],
                                 type=r["type"], status=r["status"],
                                 start_date=to_date(r["start_date"]),
                                 start_time=to_time(r["start_time"]),
                                 end_date=to_date(r["end_date"]), end_time=to_time(r["end_time"]),
                                 project_id=r["project_id"], client_id=r["client_id"],
                                 assigned_user_id=r["assigned_user_id"],
                                 observations=r["observations"],
                                 created_at=to_dt(r["created_at"]) or datetime.now())
        if table == "notifications":
            return Notification(id=r["id"], title=r["title"], message=r["message"],
                                type=r["type"], read_at=to_dt(r["read_at"]),
                                user_id=r["user_id"], event_id=r["event_id"],
                                project_id=r["project_id"],
                                created_at=to_dt(r["created_at"]) or datetime.now())
        if table == "funnel_columns":
            return FunnelColumn(id=r["id"], column_key=r["column_key"], label=r["label"],
                                description=r["description"],
                                updated_at=to_dt(r["updated_at"]) or datetime.now(),
                                type=r["type"])
        if table == "recurring_financial":
            return RecurringFinancial(id=r["id"], description=r["description"], type=r["type"],
                                      category=r["category"] or "",
                                      amount=to_decimal(r["amount"]) or 0,
                                      frequency=r["frequency"],
                                      start_date=to_date(r["start_date"]),
                                      next_date=to_date(r["next_date"]),
                                      project_id=r["project_id"],
                                      active=str(r["active"]) == "1",
                                      created_at=to_dt(r["created_at"]) or datetime.now())
        raise ValueError(table)

    with app.app_context():
        from app.models.models import ensure_default_funnel_columns
        db.create_all()
        total_new = 0
        for table in ORDER:
            model = MODELS[table]
            new = 0
            for r in data.get(table, []):
                if table == "users":
                    # O seed do entrypoint cria um admin 'admin' com id aleatorio.
                    # O dump tambem tem um 'admin' (id original). Como username e
                    # email sao UNIQUE, remove o seedado colidente antes de
                    # inserir o do dump (preserva ids originais e FKs). Depois
                    # rode seed_admin.py: o upsert por username redefine a senha
                    # para a do Dokploy.
                    for col in ("username", "email"):
                        clash = db.session.query(model).filter_by(**{col: r[col]}).all()
                        for e in clash:
                            if e.id != r["id"]:
                                db.session.delete(e)
                    db.session.flush()
                    if db.session.get(model, r["id"]) is not None:
                        continue
                elif table == "funnel_columns":
                    # Defaults ja criados pelo create_app() colidem no unique
                    # (column_key, type): remove o default e insere o do dump.
                    existing = db.session.query(model).filter_by(
                        column_key=r["column_key"], type=r["type"]).all()
                    for e in existing:
                        if e.id != r["id"]:
                            db.session.delete(e)
                    db.session.flush()
                    if db.session.get(model, r["id"]) is not None:
                        continue
                elif db.session.get(model, r["id"]) is not None:
                    continue
                try:
                    db.session.add(build(table, r))
                    new += 1
                except Exception as exc:
                    print(f"ERRO {table} {r['id']}: {exc}")
            db.session.commit()
            print(f"  {table}: +{new} novos")
            total_new += new
        try:
            ensure_default_funnel_columns()
        except Exception as exc:
            print(f"funnel defaults: {exc}")
        print(f"OK: {total_new} registros migrados.")


if __name__ == "__main__":
    main()
