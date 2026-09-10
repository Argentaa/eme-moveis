from datetime import datetime, date

import aiomysql

from repo.connection import get_pool
from schemas.reports import (
    FinancialReportFilters,
    ClientsReportFilters,
    ProjectsReportFilters,
    StockReportFilters,
    ReportResponse,
    ReportColumn,
    ReportSummaryItem,
)

_STATUS_LABELS_PROJECT = {
    "ORCAMENTO": "Orçamento",
    "PROJETADO": "Projetado",
    "PRODUCAO": "Produção",
    "MONTAGEM": "Montagem",
    "CONCLUIDO": "Concluído",
}


def _fmt_brl(value: float) -> str:
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _now_iso() -> str:
    return datetime.now().strftime("%d/%m/%Y %H:%M")


class ReportService:
    """Monta relatórios filtrados a partir das tabelas do sistema."""

    # ── Financeiro ───────────────────────────────────────────────

    async def build_financial_report(self, filters: FinancialReportFilters) -> ReportResponse:
        conditions: list[str] = []
        params: list[object] = []

        if filters.date_from:
            conditions.append("f.date >= %s")
            params.append(filters.date_from)
        if filters.date_to:
            conditions.append("f.date <= %s")
            params.append(filters.date_to)
        if filters.type:
            conditions.append("f.type = %s")
            params.append(filters.type)
        if filters.category:
            conditions.append("f.category = %s")
            params.append(filters.category)
        if filters.status:
            conditions.append("f.status = %s")
            params.append(filters.status)
        if filters.project_id:
            conditions.append("f.project_id = %s")
            params.append(filters.project_id)

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        query = f"""
            SELECT f.id, f.description, f.type, f.category, f.amount, f.date,
                   f.status, f.project_id, p.title AS project_title
            FROM financial_records f
            LEFT JOIN projects p ON f.project_id = p.id
            {where_clause}
            ORDER BY f.date DESC
        """

        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(query, tuple(params))
                rows = await cur.fetchall()

        rows = [dict(r) for r in rows]

        total_entrada = sum(float(r["amount"]) for r in rows if r["type"] == "ENTRADA")
        total_saida = sum(float(r["amount"]) for r in rows if r["type"] == "SAIDA")
        pendente_entrada = sum(float(r["amount"]) for r in rows if r["type"] == "ENTRADA" and r["status"] == "PENDENTE")
        pendente_saida = sum(float(r["amount"]) for r in rows if r["type"] == "SAIDA" and r["status"] == "PENDENTE")
        saldo = total_entrada - total_saida

        summary = [
            ReportSummaryItem(label="Total de Entradas", value=_fmt_brl(total_entrada), tone="positive"),
            ReportSummaryItem(label="Total de Saídas", value=_fmt_brl(total_saida), tone="negative"),
            ReportSummaryItem(label="Saldo do Período", value=_fmt_brl(saldo), tone="positive" if saldo >= 0 else "negative"),
            ReportSummaryItem(label="Pendente a Receber", value=_fmt_brl(pendente_entrada), tone="neutral"),
            ReportSummaryItem(label="Pendente a Pagar", value=_fmt_brl(pendente_saida), tone="neutral"),
            ReportSummaryItem(label="Quantidade de Lançamentos", value=str(len(rows)), tone="neutral"),
        ]

        formatted_rows = []
        for r in rows:
            formatted_rows.append({
                "date": r["date"].strftime("%d/%m/%Y") if isinstance(r["date"], date) else str(r["date"]),
                "description": r["description"],
                "type": "Entrada" if r["type"] == "ENTRADA" else "Saída",
                "category": r["category"],
                "project_title": r.get("project_title") or "-",
                "amount": _fmt_brl(float(r["amount"])),
                "status": "Pago" if r["status"] == "PAGO" else "Pendente",
            })

        columns = [
            ReportColumn(key="date", label="Data"),
            ReportColumn(key="description", label="Descrição"),
            ReportColumn(key="type", label="Tipo"),
            ReportColumn(key="category", label="Categoria"),
            ReportColumn(key="project_title", label="Projeto"),
            ReportColumn(key="amount", label="Valor"),
            ReportColumn(key="status", label="Status"),
        ]

        return ReportResponse(
            title="Relatório Financeiro",
            generated_at=_now_iso(),
            filters_applied=filters.model_dump(exclude_none=True, mode="json"),
            summary=summary,
            columns=columns,
            rows=formatted_rows,
        )

    # ── Clientes ─────────────────────────────────────────────────

    async def build_clients_report(self, filters: ClientsReportFilters) -> ReportResponse:
        conditions: list[str] = []
        params: list[object] = []

        if filters.created_from:
            conditions.append("c.created_at >= %s")
            params.append(filters.created_from)
        if filters.created_to:
            conditions.append("c.created_at <= %s")
            params.append(filters.created_to)
        if filters.search:
            conditions.append("(c.name LIKE %s OR c.email LIKE %s OR c.cpf_cnpj LIKE %s)")
            like = f"%{filters.search}%"
            params.extend([like, like, like])

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        query = f"""
            SELECT c.id, c.name, c.email, c.phone, c.cpf_cnpj, c.address, c.created_at,
                   COUNT(p.id) AS project_count,
                   COALESCE(SUM(p.value), 0) AS total_project_value
            FROM clients c
            LEFT JOIN projects p ON p.client_id = c.id
            {where_clause}
            GROUP BY c.id, c.name, c.email, c.phone, c.cpf_cnpj, c.address, c.created_at
            ORDER BY c.created_at DESC
        """

        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(query, tuple(params))
                rows = await cur.fetchall()

        rows = [dict(r) for r in rows]

        total_clientes = len(rows)
        com_projetos = sum(1 for r in rows if r["project_count"] > 0)
        valor_total = sum(float(r["total_project_value"]) for r in rows)

        summary = [
            ReportSummaryItem(label="Total de Clientes", value=str(total_clientes), tone="neutral"),
            ReportSummaryItem(label="Clientes com Projetos", value=str(com_projetos), tone="positive"),
            ReportSummaryItem(label="Valor Total em Projetos", value=_fmt_brl(valor_total), tone="positive"),
        ]

        formatted_rows = []
        for r in rows:
            created = r["created_at"]
            formatted_rows.append({
                "name": r["name"],
                "email": r["email"],
                "phone": r["phone"],
                "cpf_cnpj": r["cpf_cnpj"],
                "address": r["address"],
                "created_at": created.strftime("%d/%m/%Y") if hasattr(created, "strftime") else str(created),
                "project_count": str(r["project_count"]),
                "total_project_value": _fmt_brl(float(r["total_project_value"])),
            })

        columns = [
            ReportColumn(key="name", label="Nome"),
            ReportColumn(key="email", label="Email"),
            ReportColumn(key="phone", label="Telefone"),
            ReportColumn(key="cpf_cnpj", label="CPF/CNPJ"),
            ReportColumn(key="address", label="Endereço"),
            ReportColumn(key="created_at", label="Cadastrado em"),
            ReportColumn(key="project_count", label="Projetos"),
            ReportColumn(key="total_project_value", label="Valor em Projetos"),
        ]

        return ReportResponse(
            title="Relatório de Clientes",
            generated_at=_now_iso(),
            filters_applied=filters.model_dump(exclude_none=True, mode="json"),
            summary=summary,
            columns=columns,
            rows=formatted_rows,
        )

    # ── Projetos ─────────────────────────────────────────────────

    async def build_projects_report(self, filters: ProjectsReportFilters) -> ReportResponse:
        conditions: list[str] = []
        params: list[object] = []

        if filters.status:
            conditions.append("p.status = %s")
            params.append(filters.status)
        if filters.client_id:
            conditions.append("p.client_id = %s")
            params.append(filters.client_id)
        if filters.deadline_from:
            conditions.append("p.deadline >= %s")
            params.append(filters.deadline_from)
        if filters.deadline_to:
            conditions.append("p.deadline <= %s")
            params.append(filters.deadline_to)

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        query = f"""
            SELECT p.id, p.title, p.client_id, c.name AS client_name, p.description,
                   p.status, p.value, p.deadline, p.created_at
            FROM projects p
            LEFT JOIN clients c ON p.client_id = c.id
            {where_clause}
            ORDER BY p.deadline ASC
        """

        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(query, tuple(params))
                rows = await cur.fetchall()

        rows = [dict(r) for r in rows]

        total_valor = sum(float(r["value"]) for r in rows)
        concluidos = sum(1 for r in rows if r["status"] == "CONCLUIDO")
        em_andamento = sum(1 for r in rows if r["status"] not in ("CONCLUIDO",))
        hoje = date.today()
        atrasados = sum(
            1 for r in rows
            if r["status"] != "CONCLUIDO" and isinstance(r["deadline"], date) and r["deadline"] < hoje
        )

        summary = [
            ReportSummaryItem(label="Total de Projetos", value=str(len(rows)), tone="neutral"),
            ReportSummaryItem(label="Valor Total dos Projetos", value=_fmt_brl(total_valor), tone="positive"),
            ReportSummaryItem(label="Concluídos", value=str(concluidos), tone="positive"),
            ReportSummaryItem(label="Em Andamento", value=str(em_andamento), tone="neutral"),
            ReportSummaryItem(label="Atrasados (prazo vencido)", value=str(atrasados), tone="negative" if atrasados else "neutral"),
        ]

        formatted_rows = []
        for r in rows:
            deadline = r["deadline"]
            formatted_rows.append({
                "title": r["title"],
                "client_name": r["client_name"] or "-",
                "status": _STATUS_LABELS_PROJECT.get(r["status"], r["status"]),
                "value": _fmt_brl(float(r["value"])),
                "deadline": deadline.strftime("%d/%m/%Y") if isinstance(deadline, date) else str(deadline),
            })

        columns = [
            ReportColumn(key="title", label="Projeto/Ambiente"),
            ReportColumn(key="client_name", label="Cliente"),
            ReportColumn(key="status", label="Status"),
            ReportColumn(key="value", label="Valor"),
            ReportColumn(key="deadline", label="Prazo"),
        ]

        return ReportResponse(
            title="Relatório de Projetos",
            generated_at=_now_iso(),
            filters_applied=filters.model_dump(exclude_none=True, mode="json"),
            summary=summary,
            columns=columns,
            rows=formatted_rows,
        )

    # ── Estoque ──────────────────────────────────────────────────

    async def build_stock_report(self, filters: StockReportFilters) -> ReportResponse:
        if filters.report_mode == "movements":
            return await self._build_stock_movements_report(filters)
        return await self._build_stock_items_report(filters)

    async def _build_stock_items_report(self, filters: StockReportFilters) -> ReportResponse:
        conditions: list[str] = []
        params: list[object] = []

        if filters.category_id:
            conditions.append("s.category_id = %s")
            params.append(filters.category_id)
        if filters.low_stock_only:
            conditions.append("s.quantity <= s.min_quantity")

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        query = f"""
            SELECT s.id, s.name, s.sku, s.category_id, c.name AS category_name,
                   s.quantity, s.min_quantity, s.unit, s.price, s.supplier
            FROM stock_items s
            LEFT JOIN categories c ON s.category_id = c.id
            {where_clause}
            ORDER BY s.name
        """

        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(query, tuple(params))
                item_rows = await cur.fetchall()

        item_rows = [dict(r) for r in item_rows]

        total_itens = len(item_rows)
        valor_total_estoque = sum(float(r["quantity"]) * float(r["price"]) for r in item_rows)
        abaixo_minimo = sum(1 for r in item_rows if float(r["quantity"]) <= float(r["min_quantity"]))

        summary = [
            ReportSummaryItem(label="Total de Itens", value=str(total_itens), tone="neutral"),
            ReportSummaryItem(label="Valor Total em Estoque", value=_fmt_brl(valor_total_estoque), tone="positive"),
            ReportSummaryItem(label="Itens Abaixo do Mínimo", value=str(abaixo_minimo), tone="negative" if abaixo_minimo else "neutral"),
        ]

        formatted_rows = []
        for r in item_rows:
            formatted_rows.append({
                "name": r["name"],
                "sku": r["sku"],
                "category_name": r["category_name"] or "-",
                "quantity": f"{float(r['quantity']):.2f} {r['unit']}",
                "min_quantity": f"{float(r['min_quantity']):.2f} {r['unit']}",
                "price": _fmt_brl(float(r["price"])),
                "total_value": _fmt_brl(float(r["quantity"]) * float(r["price"])),
                "supplier": r["supplier"],
                "low_stock": "Sim" if float(r["quantity"]) <= float(r["min_quantity"]) else "Não",
            })

        columns = [
            ReportColumn(key="name", label="Item"),
            ReportColumn(key="sku", label="SKU"),
            ReportColumn(key="category_name", label="Categoria"),
            ReportColumn(key="quantity", label="Quantidade"),
            ReportColumn(key="min_quantity", label="Mínimo"),
            ReportColumn(key="price", label="Preço Unit."),
            ReportColumn(key="total_value", label="Valor em Estoque"),
            ReportColumn(key="supplier", label="Fornecedor"),
            ReportColumn(key="low_stock", label="Abaixo do Mínimo"),
        ]

        return ReportResponse(
            title="Relatório de Estoque — Itens",
            generated_at=_now_iso(),
            filters_applied=filters.model_dump(exclude_none=True, mode="json"),
            summary=summary,
            columns=columns,
            rows=formatted_rows,
        )

    async def _build_stock_movements_report(self, filters: StockReportFilters) -> ReportResponse:
        conditions: list[str] = []
        params: list[object] = []

        if filters.movement_type:
            conditions.append("m.type = %s")
            params.append(filters.movement_type)
        if filters.date_from:
            conditions.append("m.date >= %s")
            params.append(filters.date_from)
        if filters.date_to:
            conditions.append("m.date <= %s")
            params.append(filters.date_to)
        if filters.category_id:
            conditions.append("s.category_id = %s")
            params.append(filters.category_id)

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        query = f"""
            SELECT m.id, m.item_id, s.name AS item_name, m.type, m.quantity,
                   m.reason, m.created_by, m.date
            FROM stock_movements m
            LEFT JOIN stock_items s ON m.item_id = s.id
            {where_clause}
            ORDER BY m.date DESC
        """

        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(query, tuple(params))
                mov_rows = await cur.fetchall()

        mov_rows = [dict(r) for r in mov_rows]

        total_entradas = sum(float(r["quantity"]) for r in mov_rows if r["type"] == "ENTRADA")
        total_saidas = sum(float(r["quantity"]) for r in mov_rows if r["type"] == "SAIDA")

        summary = [
            ReportSummaryItem(label="Movimentações no Período", value=str(len(mov_rows)), tone="neutral"),
            ReportSummaryItem(label="Total Movimentado (Entradas)", value=f"{total_entradas:.2f}", tone="positive"),
            ReportSummaryItem(label="Total Movimentado (Saídas)", value=f"{total_saidas:.2f}", tone="negative"),
        ]

        formatted_rows = []
        for r in mov_rows:
            mov_date = r["date"]
            formatted_rows.append({
                "date": mov_date.strftime("%d/%m/%Y %H:%M") if hasattr(mov_date, "strftime") else str(mov_date),
                "item_name": r["item_name"] or "-",
                "type": "Entrada" if r["type"] == "ENTRADA" else "Saída",
                "quantity": f"{float(r['quantity']):.2f}",
                "reason": r["reason"],
                "created_by": r["created_by"],
            })

        columns = [
            ReportColumn(key="date", label="Data"),
            ReportColumn(key="item_name", label="Item"),
            ReportColumn(key="type", label="Tipo"),
            ReportColumn(key="quantity", label="Quantidade"),
            ReportColumn(key="reason", label="Motivo"),
            ReportColumn(key="created_by", label="Responsável"),
        ]

        return ReportResponse(
            title="Relatório de Estoque — Movimentações",
            generated_at=_now_iso(),
            filters_applied=filters.model_dump(exclude_none=True, mode="json"),
            summary=summary,
            columns=columns,
            rows=formatted_rows,
        )


    async def build_dre(self, month: int = None, year: int = None) -> dict:
        """Demonstrativo de Resultado do Exercício."""
        from repo.connection import get_pool
        import aiomysql
        from datetime import date

        today = date.today()
        m = month or today.month
        y = year or today.year

        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                # Receitas brutas (ENTRADA PAGO) no mês
                await cur.execute(
                    """SELECT category, SUM(amount) as total
                       FROM financial_records
                       WHERE type = 'ENTRADA' AND status = 'PAGO'
                         AND MONTH(date) = %s AND YEAR(date) = %s
                       GROUP BY category ORDER BY total DESC""",
                    (m, y)
                )
                receitas = [dict(r) for r in await cur.fetchall()]

                # Despesas (SAIDA PAGO) no mês
                await cur.execute(
                    """SELECT category, SUM(amount) as total
                       FROM financial_records
                       WHERE type = 'SAIDA' AND status = 'PAGO'
                         AND MONTH(date) = %s AND YEAR(date) = %s
                       GROUP BY category ORDER BY total DESC""",
                    (m, y)
                )
                despesas = [dict(r) for r in await cur.fetchall()]

                # Receitas e despesas pendentes
                await cur.execute(
                    """SELECT
                         SUM(CASE WHEN type = 'ENTRADA' THEN amount ELSE 0 END) as receitas_pendentes,
                         SUM(CASE WHEN type = 'SAIDA' THEN amount ELSE 0 END) as despesas_pendentes
                       FROM financial_records
                       WHERE status = 'PENDENTE'
                         AND MONTH(due_date) = %s AND YEAR(due_date) = %s""",
                    (m, y)
                )
                pendentes = dict(await cur.fetchone())

        total_receitas = sum(float(r["total"]) for r in receitas)
        total_despesas = sum(float(d["total"]) for d in despesas)
        resultado = total_receitas - total_despesas

        return {
            "periodo": {"mes": m, "ano": y},
            "receitas": {
                "itens": [{"categoria": r["category"], "valor": float(r["total"])} for r in receitas],
                "total": total_receitas,
            },
            "despesas": {
                "itens": [{"categoria": d["category"], "valor": float(d["total"])} for d in despesas],
                "total": total_despesas,
            },
            "resultado_liquido": resultado,
            "margem_liquida": round((resultado / total_receitas * 100), 2) if total_receitas > 0 else 0,
            "pendentes": {
                "receitas": float(pendentes.get("receitas_pendentes") or 0),
                "despesas": float(pendentes.get("despesas_pendentes") or 0),
            },
        }


    async def build_crm_report(self, date_from: str = None, date_to: str = None) -> dict:
        """Relatório CRM completo: negociações, perdas, conversão, ticket médio e fluxo de caixa."""
        from repo.connection import get_pool
        import aiomysql
        from datetime import date

        pool = await get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cur:

                # Monta filtro de período por created_at dos clientes
                date_filter = ""
                params_period: list = []
                if date_from:
                    date_filter += " AND c.created_at >= %s"
                    params_period.append(date_from)
                if date_to:
                    date_filter += " AND c.created_at <= %s"
                    params_period.append(date_to + " 23:59:59")

                # 1. Total de negociações por etapa do funil
                await cur.execute(
                    f"""SELECT funnel_status, COUNT(*) as total
                        FROM clients c
                        WHERE 1=1 {date_filter}
                        GROUP BY funnel_status""",
                    params_period
                )
                by_stage = [dict(r) for r in await cur.fetchall()]

                # 2. Negociações perdidas com motivo
                await cur.execute(
                    f"""SELECT name, lost_reason, created_at
                        FROM clients c
                        WHERE funnel_status = 'PERDIDO' {date_filter}
                        ORDER BY created_at DESC""",
                    params_period
                )
                lost = [dict(r) for r in await cur.fetchall()]
                for r in lost:
                    if r.get("created_at"):
                        r["created_at"] = str(r["created_at"])

                # 3. Total geral e em fechamento para taxa de conversão
                await cur.execute(
                    f"SELECT COUNT(*) as total FROM clients c WHERE 1=1 {date_filter}",
                    params_period
                )
                total_clients = (await cur.fetchone())["total"]

                await cur.execute(
                    f"SELECT COUNT(*) as total FROM clients c WHERE funnel_status = 'FECHAMENTO' {date_filter}",
                    params_period
                )
                total_closed = (await cur.fetchone())["total"]

                # 4. Ticket médio — valor médio dos projetos concluídos
                await cur.execute(
                    """SELECT AVG(value) as avg_value, MAX(value) as max_value,
                              MIN(value) as min_value, COUNT(*) as total_projects,
                              SUM(value) as total_value
                       FROM projects WHERE status = 'CONCLUIDO'"""
                )
                ticket = dict(await cur.fetchone())

                # 5. Fluxo de caixa consolidado por mês (últimos 12 meses)
                await cur.execute(
                    """SELECT DATE_FORMAT(date, '%Y-%m') as mes,
                              SUM(CASE WHEN type = 'ENTRADA' AND status = 'PAGO' THEN amount ELSE 0 END) as receitas,
                              SUM(CASE WHEN type = 'SAIDA' AND status = 'PAGO' THEN amount ELSE 0 END) as despesas
                       FROM financial_records
                       WHERE date >= DATE_SUB(CURDATE(), INTERVAL 12 MONTH)
                       GROUP BY mes ORDER BY mes ASC"""
                )
                cash_flow = [dict(r) for r in await cur.fetchall()]
                for r in cash_flow:
                    r["receitas"] = float(r["receitas"] or 0)
                    r["despesas"] = float(r["despesas"] or 0)
                    r["resultado"] = r["receitas"] - r["despesas"]

                # 6. Fonte do lead
                await cur.execute(
                    f"""SELECT COALESCE(lead_source, 'Não informado') as fonte, COUNT(*) as total
                        FROM clients c
                        WHERE 1=1 {date_filter}
                        GROUP BY fonte ORDER BY total DESC""",
                    params_period
                )
                lead_sources = [dict(r) for r in await cur.fetchall()]

        conversion_rate = round((total_closed / total_clients * 100), 1) if total_clients > 0 else 0

        return {
            "periodo": {"date_from": date_from, "date_to": date_to},
            "negociacoes": {
                "total": total_clients,
                "por_etapa": by_stage,
                "perdidas": lost,
                "total_perdidas": len(lost),
            },
            "conversao": {
                "total_clientes": total_clients,
                "total_fechamentos": total_closed,
                "taxa": conversion_rate,
            },
            "ticket_medio": {
                "media": float(ticket["avg_value"] or 0),
                "maximo": float(ticket["max_value"] or 0),
                "minimo": float(ticket["min_value"] or 0),
                "total_projetos": ticket["total_projects"],
                "total_faturado": float(ticket["total_value"] or 0),
            },
            "fluxo_caixa": cash_flow,
            "fontes_lead": lead_sources,
        }


report_service = ReportService()
