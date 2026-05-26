"""Consultas somente leitura do painel sobre o Data Warehouse RetailCo."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Engine


def next_competence(competence: str, offset: int = 1) -> str:
    """Avança uma competência YYYY-MM pela quantidade solicitada de meses."""
    year, month = (int(part) for part in competence.split("-"))
    position = year * 12 + month - 1 + offset
    return f"{position // 12:04d}-{position % 12 + 1:02d}"


def competence_distance(start: str, end: str) -> int:
    """Retorna a distância, em meses, entre duas competências YYYY-MM."""
    start_year, start_month = (int(part) for part in start.split("-"))
    end_year, end_month = (int(part) for part in end.split("-"))
    return (end_year - start_year) * 12 + end_month - start_month


def forecast_trend(history: list[dict[str, Any]], latest_competence_value: str) -> float:
    """Calcula uma tendência mensal recente conservadora de receita para uma loja."""
    completed = history[:-1] if history[-1]["competencia"] == latest_competence_value else history
    revenues = [float(row["receita"]) for row in completed if float(row["receita"]) > 0]
    changes = [
        revenues[index] / revenues[index - 1] - 1
        for index in range(1, len(revenues))
        if revenues[index - 1] > 0
    ]
    recent_changes = changes[-3:]
    if not recent_changes:
        return 0.0
    average = sum(recent_changes) / len(recent_changes)
    return max(-0.15, min(0.15, average))


def serialize(value: Any) -> Any:
    """Converte valores do banco em valores escalares serializáveis em JSON."""
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, date | datetime):
        return value.isoformat()
    return value


def fetch_all(
    engine: Engine,
    query: str,
    parameters: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Executa uma consulta somente leitura e retorna mapeamentos compatíveis com JSON."""
    with engine.connect() as connection:
        result = connection.execute(text(query), parameters or {})
        return [
            {key: serialize(value) for key, value in row.items()} for row in result.mappings().all()
        ]


def fetch_one(
    engine: Engine,
    query: str,
    parameters: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Executa uma consulta que retorna um documento de métricas."""
    rows = fetch_all(engine, query, parameters)
    return rows[0] if rows else {}


def latest_competence(engine: Engine) -> str | None:
    """Retorna a competência ano/mês mais recente carregada."""
    value = fetch_one(
        engine,
        """
        SELECT TO_CHAR(MAX(data_venda), 'YYYY-MM') AS competencia
        FROM fato_vendas
        WHERE status = 'CONCLUIDA'
        """,
    )
    return value.get("competencia")


def competences(engine: Engine) -> list[str]:
    """Retorna competências carregadas, ordenadas da mais recente para a mais antiga."""
    rows = fetch_all(
        engine,
        """
        SELECT DISTINCT TO_CHAR(data_venda, 'YYYY-MM') AS competencia
        FROM fato_vendas
        ORDER BY competencia DESC
        """,
    )
    return [row["competencia"] for row in rows]


def dashboard(engine: Engine, competence: str) -> dict[str, Any]:
    """Monta uma fotografia completa do painel para a competência selecionada."""
    year, month = (int(part) for part in competence.split("-"))
    params = {"ano": year, "mes": month}
    return {
        "competencia": competence,
        "overview": fetch_one(
            engine,
            """
            SELECT
                COALESCE(SUM(valor_liquido) FILTER (WHERE status = 'CONCLUIDA'), 0) receita_liquida,
                COALESCE(SUM(valor_bruto) FILTER (WHERE status = 'CONCLUIDA'), 0) receita_bruta,
                COALESCE(SUM(desconto_valor) FILTER (WHERE status = 'CONCLUIDA'), 0) descontos,
                COALESCE(SUM(margem_bruta) FILTER (WHERE status = 'CONCLUIDA'), 0) margem_bruta,
                COUNT(DISTINCT id_venda) FILTER (WHERE status = 'CONCLUIDA') pedidos,
                COUNT(*) FILTER (WHERE status = 'CANCELADA') canceladas,
                COUNT(*) FILTER (WHERE status = 'PENDENTE') pendentes,
                COALESCE(
                    SUM(valor_liquido) FILTER (WHERE status = 'CONCLUIDA') /
                    NULLIF(COUNT(DISTINCT id_venda) FILTER (WHERE status = 'CONCLUIDA'), 0), 0
                ) ticket_medio
            FROM fato_vendas
            WHERE ano = :ano AND mes = :mes
            """,
            params,
        ),
        "dre": fetch_one(
            engine,
            """
            SELECT
                COALESCE(SUM(receita_liquida), 0) receita_liquida,
                COALESCE(SUM(lucro_bruto), 0) lucro_bruto,
                COALESCE(SUM(ebitda), 0) ebitda,
                COALESCE(SUM(resultado_antes_ir), 0) resultado_antes_ir,
                COALESCE(SUM(ebitda) / NULLIF(SUM(receita_liquida), 0) * 100, 0) margem_ebitda_pct
            FROM fato_dre
            WHERE ano = :ano AND mes = :mes
            """,
            params,
        ),
        "trend": fetch_all(
            engine,
            """
            SELECT ano, mes, receita_liquida, ticket_medio
            FROM vw_faturamento_mensal
            ORDER BY ano, mes
            """,
        ),
        "stores": fetch_all(
            engine,
            """
            SELECT
                fat.loja_id, fat.loja_nome, fat.faturamento, fat.market_share_pct,
                fat.crescimento_mom, fat.ranking, meta.receita_orcada,
                meta.variacao_pct, meta.status_semaforo
            FROM vw_faturamento_por_loja fat
            JOIN vw_meta_vs_realizado meta
              ON meta.ano = fat.ano AND meta.mes = fat.mes AND meta.loja_id = fat.loja_id
            WHERE fat.ano = :ano AND fat.mes = :mes
            ORDER BY fat.ranking
            """,
            params,
        ),
        "products": fetch_all(
            engine,
            """
            SELECT produto_nome, categoria, receita, volume, ranking_receita
            FROM vw_top10_produtos
            WHERE ano = :ano AND mes = :mes AND ranking_receita <= 10
            ORDER BY ranking_receita
            """,
            params,
        ),
        "fpa": fetch_all(
            engine,
            """
            SELECT f.loja_id, l.loja_nome, f.realizado, f.receita_orcada,
                   f.meta_atingida_pct, f.forecast_mes, f.run_rate_anual
            FROM vw_indicadores_fpa f
            JOIN dim_loja l ON l.loja_id = f.loja_id
            WHERE f.ano = :ano AND f.mes = :mes
            ORDER BY f.realizado DESC
            """,
            params,
        ),
        "channels": fetch_all(
            engine,
            """
            SELECT canal_venda, SUM(receita) receita, SUM(pedidos) pedidos
            FROM vw_cohort_canais
            WHERE ano = :ano AND mes = :mes
            GROUP BY canal_venda
            ORDER BY receita DESC
            """,
            params,
        ),
        "pipeline": fetch_one(
            engine,
            """
            SELECT
                (SELECT COUNT(*) FROM processed_files) arquivos_processados,
                (SELECT COUNT(*) FROM fato_vendas) fatos_carregados,
                (SELECT MAX(created_at) FROM pipeline_audit_log) ultima_execucao,
                (SELECT COUNT(*) FROM pipeline_audit_log WHERE status = 'FAILED') falhas
            """,
        ),
    }


def evolution(engine: Engine) -> dict[str, Any]:
    """Retorna séries mensais de desempenho para a evolução da rede e das lojas."""
    return {
        "stores": fetch_all(
            engine,
            """
            SELECT loja_id, loja_nome
            FROM dim_loja
            WHERE ativa = TRUE
            ORDER BY loja_id
            """,
        ),
        "network": fetch_all(
            engine,
            """
            WITH status_mes AS (
                SELECT
                    ano, mes,
                    COUNT(*) FILTER (WHERE status = 'CANCELADA') canceladas,
                    COUNT(*) total_registros
                FROM fato_vendas
                GROUP BY ano, mes
            ), dre_mes AS (
                SELECT
                    ano, mes, SUM(ebitda) ebitda,
                    SUM(ebitda) / NULLIF(SUM(receita_liquida), 0) * 100 margem_ebitda_pct
                FROM fato_dre
                GROUP BY ano, mes
            )
            SELECT
                TO_CHAR(MAKE_DATE(f.ano, f.mes, 1), 'YYYY-MM') competencia,
                f.ano, f.mes, f.receita_liquida, f.ticket_medio, f.total_pedidos,
                COALESCE(d.ebitda, 0) ebitda,
                COALESCE(d.margem_ebitda_pct, 0) margem_ebitda_pct,
                COALESCE(s.canceladas / NULLIF(s.total_registros, 0)::NUMERIC * 100, 0)
                    cancelamento_pct
            FROM vw_faturamento_mensal f
            LEFT JOIN dre_mes d ON d.ano = f.ano AND d.mes = f.mes
            LEFT JOIN status_mes s ON s.ano = f.ano AND s.mes = f.mes
            ORDER BY f.ano, f.mes
            """,
        ),
        "store_series": fetch_all(
            engine,
            """
            SELECT
                TO_CHAR(MAKE_DATE(f.ano, f.mes, 1), 'YYYY-MM') competencia,
                f.ano, f.mes, f.loja_id, f.loja_nome,
                f.faturamento receita, f.market_share_pct, f.crescimento_mom,
                t.ticket_medio,
                r.margem_pct,
                m.receita_orcada,
                CASE
                    WHEN m.receita_orcada = 0 THEN 0
                    ELSE f.faturamento / m.receita_orcada * 100
                END meta_atingida_pct,
                COALESCE(i.forecast_mes, f.faturamento) forecast_mes
            FROM vw_faturamento_por_loja f
            JOIN vw_ticket_medio_por_loja t
              ON t.ano = f.ano AND t.mes = f.mes AND t.loja_id = f.loja_id
            JOIN vw_ranking_lojas r
              ON r.ano = f.ano AND r.mes = f.mes AND r.loja_id = f.loja_id
            JOIN vw_meta_vs_realizado m
              ON m.ano = f.ano AND m.mes = f.mes AND m.loja_id = f.loja_id
            LEFT JOIN vw_indicadores_fpa i
              ON i.ano = f.ano AND i.mes = f.mes AND i.loja_id = f.loja_id
            ORDER BY f.ano, f.mes, f.loja_id
            """,
        ),
    }


def forecast(engine: Engine, months: int, adjustment_pct: float) -> dict[str, Any]:
    """Projeta receitas mensais futuras a partir do realizado e do ajuste gerencial."""
    source = evolution(engine)
    latest = source["network"][-1]["competencia"]
    budget_rows = fetch_all(
        engine,
        """
        SELECT
            TO_CHAR(MAKE_DATE(ano, mes, 1), 'YYYY-MM') competencia,
            loja_id, receita_orcada
        FROM fato_orcamento
        WHERE MAKE_DATE(ano, mes, 1) > TO_DATE(:latest || '-01', 'YYYY-MM-DD')
        ORDER BY ano, mes, loja_id
        """,
        {"latest": latest},
    )
    budgets = {
        (row["competencia"], row["loja_id"]): float(row["receita_orcada"]) for row in budget_rows
    }
    store_projections: list[dict[str, Any]] = []
    adjustment = adjustment_pct / 100

    for store in source["stores"]:
        history = [row for row in source["store_series"] if row["loja_id"] == store["loja_id"]]
        if not history:
            continue
        current = history[-1]
        trend = forecast_trend(history, latest)
        base_value = float(current["forecast_mes"] or current["receita"])

        for position in range(1, months + 1):
            competence = next_competence(latest, position)
            elapsed_months = competence_distance(current["competencia"], competence)
            baseline = base_value * ((1 + trend) ** elapsed_months)
            projected = baseline * (1 + adjustment)
            budget = budgets.get((competence, store["loja_id"]))
            variance = projected - budget if budget is not None else None
            attainment = projected / budget * 100 if budget else None
            store_projections.append(
                {
                    "competencia": competence,
                    "loja_id": store["loja_id"],
                    "loja_nome": store["loja_nome"],
                    "forecast_base": round(baseline, 2),
                    "forecast_ajustado": round(projected, 2),
                    "receita_orcada": round(budget, 2) if budget is not None else None,
                    "variacao_orcamento": round(variance, 2) if variance is not None else None,
                    "meta_atingida_pct": round(attainment, 2) if attainment is not None else None,
                    "tendencia_pct": round(trend * 100, 2),
                }
            )

    recent_margins = [
        float(row["margem_ebitda_pct"])
        for row in source["network"][-3:]
        if float(row["margem_ebitda_pct"]) != 0
    ]
    ebitda_margin = sum(recent_margins) / len(recent_margins) if recent_margins else 0
    network_projections = []
    for position in range(1, months + 1):
        competence = next_competence(latest, position)
        projection = [row for row in store_projections if row["competencia"] == competence]
        base = sum(float(row["forecast_base"]) for row in projection)
        adjusted = sum(float(row["forecast_ajustado"]) for row in projection)
        budgets_available = [
            float(row["receita_orcada"]) for row in projection if row["receita_orcada"] is not None
        ]
        budget = sum(budgets_available) if budgets_available else None
        variance = adjusted - budget if budget is not None else None
        network_projections.append(
            {
                "competencia": competence,
                "forecast_base": round(base, 2),
                "forecast_ajustado": round(adjusted, 2),
                "receita_orcada": round(budget, 2) if budget is not None else None,
                "variacao_orcamento": round(variance, 2) if variance is not None else None,
                "meta_atingida_pct": round(adjusted / budget * 100, 2) if budget else None,
                "ebitda_estimado": round(adjusted * ebitda_margin / 100, 2),
                "margem_ebitda_referencia_pct": round(ebitda_margin, 2),
            }
        )

    return {
        "latest_competence": latest,
        "months": months,
        "adjustment_pct": adjustment_pct,
        "stores": source["stores"],
        "history": source["network"],
        "store_history": source["store_series"],
        "network_projection": network_projections,
        "store_projection": store_projections,
        "methodology": {
            "base": (
                "Forecast de fechamento mais recente por loja, calculado "
                "sobre vendas realizadas."
            ),
            "trend": "Média das últimas variações mensais realizadas, limitada entre -15% e 15%.",
            "adjustment": "Ajuste gerencial aplicado uniformemente sobre a projeção base.",
        },
    }
