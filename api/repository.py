"""Consultas somente leitura do painel sobre o Data Warehouse RetailCo."""

from __future__ import annotations

import math
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


def linear_regression(values: list[float]) -> dict[str, float]:
    """Ajusta uma regressão linear simples para uma série temporal mensal."""
    if not values:
        raise ValueError("A série de treino precisa possuir ao menos uma observação.")
    if len(values) == 1:
        return {
            "intercept": values[0],
            "slope": 0.0,
            "rmse": 0.0,
            "r2": 1.0,
        }

    positions = list(range(len(values)))
    x_average = sum(positions) / len(positions)
    y_average = sum(values) / len(values)
    denominator = sum((position - x_average) ** 2 for position in positions)
    slope = (
        sum(
            (position - x_average) * (value - y_average)
            for position, value in zip(positions, values, strict=True)
        )
        / denominator
        if denominator
        else 0.0
    )
    intercept = y_average - slope * x_average
    residuals = [
        value - (intercept + slope * position)
        for position, value in zip(positions, values, strict=True)
    ]
    rmse = math.sqrt(sum(residual**2 for residual in residuals) / len(residuals))
    total_variation = sum((value - y_average) ** 2 for value in values)
    residual_variation = sum(residual**2 for residual in residuals)
    r2 = 1 - residual_variation / total_variation if total_variation else 1.0
    return {
        "intercept": intercept,
        "slope": slope,
        "rmse": rmse,
        "r2": max(0.0, min(1.0, r2)),
    }


def regression_prediction(
    history: list[dict[str, Any]],
    value_key: str,
    months: int,
    latest_competence_value: str,
) -> dict[str, Any]:
    """Gera previsão mensal por regressão linear com backtest simples."""
    values = [float(row[value_key] or 0) for row in history]
    model = linear_regression(values)
    last_value = values[-1] if values else 0.0
    trend_pct = model["slope"] / last_value * 100 if last_value else 0.0

    backtest = None
    if len(values) >= 3:
        train = values[:-1]
        backtest_model = linear_regression(train)
        predicted = max(0.0, backtest_model["intercept"] + backtest_model["slope"] * len(train))
        actual = values[-1]
        error = predicted - actual
        absolute_pct = abs(error) / actual * 100 if actual else None
        backtest = {
            "competencia": history[-1]["competencia"],
            "realizado": round(actual, 2),
            "previsto": round(predicted, 2),
            "erro_absoluto": round(error, 2),
            "erro_percentual_abs": round(absolute_pct, 2) if absolute_pct is not None else None,
        }

    projection = []
    for position in range(1, months + 1):
        model_position = len(values) - 1 + position
        forecast_value = max(0.0, model["intercept"] + model["slope"] * model_position)
        error_margin = 1.96 * model["rmse"] * math.sqrt(1 + position / max(len(values), 1))
        projection.append(
            {
                "competencia": next_competence(latest_competence_value, position),
                "previsao": round(forecast_value, 2),
                "limite_inferior": round(max(0.0, forecast_value - error_margin), 2),
                "limite_superior": round(forecast_value + error_margin, 2),
            }
        )

    return {
        "model": {
            "tipo": "Regressão linear simples",
            "intercepto": round(model["intercept"], 2),
            "coeficiente_mensal": round(model["slope"], 2),
            "tendencia_mensal_pct": round(trend_pct, 2),
            "rmse": round(model["rmse"], 2),
            "r2": round(model["r2"], 4),
            "observacoes_treino": len(values),
        },
        "backtest": backtest,
        "projection": projection,
    }


def approval_rate(read_records: int | float, invalid_records: int | float) -> float:
    """Calcula a taxa de aprovação de registros lidos pelo pipeline."""
    read = float(read_records or 0)
    invalid = float(invalid_records or 0)
    if read <= 0:
        return 100.0
    return round(max(0.0, (read - invalid) / read * 100), 2)


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


def ml_forecast(engine: Engine, months: int) -> dict[str, Any]:
    """Projeta receita futura com regressão linear simples sobre o realizado mensal."""
    source = evolution(engine)
    if not source["network"]:
        raise ValueError("Não há histórico realizado suficiente para previsão.")

    latest = source["network"][-1]["competencia"]
    network_history = [
        {"competencia": row["competencia"], "receita": float(row["receita_liquida"] or 0)}
        for row in source["network"]
    ]
    network_result = regression_prediction(network_history, "receita", months, latest)

    store_results = []
    for store in source["stores"]:
        history = [
            {
                "competencia": row["competencia"],
                "receita": float(row["receita"] or 0),
            }
            for row in source["store_series"]
            if row["loja_id"] == store["loja_id"]
        ]
        if not history:
            continue
        prediction = regression_prediction(history, "receita", months, latest)
        store_results.append(
            {
                "loja_id": store["loja_id"],
                "loja_nome": store["loja_nome"],
                "history": history,
                "model": prediction["model"],
                "backtest": prediction["backtest"],
                "projection": prediction["projection"],
            }
        )

    return {
        "latest_competence": latest,
        "months": months,
        "history": network_history,
        "network": network_result,
        "stores": source["stores"],
        "store_models": store_results,
        "methodology": {
            "objective": (
                "Estimar a receita futura a partir do comportamento mensal realizado, "
                "sem considerar ajustes manuais."
            ),
            "model": (
                "Regressão linear simples usando a posição temporal do mês como variável "
                "explicativa e a receita realizada como alvo."
            ),
            "validation": (
                "Backtest holdout: o último mês realizado é previsto por um modelo treinado "
                "apenas com os meses anteriores."
            ),
            "interval": "Faixa estimada por 1,96 vezes o RMSE do modelo, ampliada pelo horizonte.",
        },
    }


def data_quality_status(engine: Engine, days: int) -> dict[str, Any]:
    """Consolida auditoria, qualidade e rastreabilidade dos arquivos carregados."""
    overview = fetch_one(
        engine,
        """
        WITH arquivos AS (
            SELECT
                COUNT(*) total_arquivos,
                COUNT(*) FILTER (WHERE status = 'PROCESSED') processados,
                COUNT(*) FILTER (WHERE status = 'REPROCESSED') reprocessados,
                COUNT(*) FILTER (WHERE status = 'FAILED') falhas_arquivo,
                COUNT(*) FILTER (WHERE status = 'QUARANTINED') quarentenados,
                COALESCE(SUM(registros_lidos), 0) registros_lidos,
                COALESCE(SUM(registros_validos), 0) registros_validos,
                COALESCE(SUM(registros_invalidos), 0) registros_invalidos,
                MAX(updated_at) ultima_atualizacao_arquivo,
                MAX(data_referencia) ultima_data_referencia
            FROM processed_files
        ), auditoria AS (
            SELECT
                COUNT(*) total_execucoes,
                COUNT(*) FILTER (WHERE status = 'SUCCESS') execucoes_sucesso,
                COUNT(*) FILTER (WHERE status = 'FAILED') execucoes_falha,
                COALESCE(SUM(registros_lidos), 0) registros_auditados,
                COALESCE(SUM(registros_invalidos), 0) rejeicoes_auditadas,
                COALESCE(AVG(duracao_segundos), 0) duracao_media_segundos,
                MAX(created_at) ultima_execucao
            FROM pipeline_audit_log
        )
        SELECT *
        FROM arquivos CROSS JOIN auditoria
        """,
    )
    daily_quality = fetch_all(
        engine,
        """
        SELECT
            data_referencia,
            COUNT(*) arquivos,
            COUNT(DISTINCT loja_id) lojas,
            COUNT(*) FILTER (WHERE status = 'PROCESSED') processados,
            COUNT(*) FILTER (WHERE status = 'REPROCESSED') reprocessados,
            COUNT(*) FILTER (WHERE status = 'FAILED') falhas,
            COUNT(*) FILTER (WHERE status = 'QUARANTINED') quarentenados,
            COALESCE(SUM(registros_lidos), 0) registros_lidos,
            COALESCE(SUM(registros_validos), 0) registros_validos,
            COALESCE(SUM(registros_invalidos), 0) registros_invalidos,
            MAX(updated_at) atualizado_em
        FROM processed_files
        WHERE data_referencia >= CURRENT_DATE - ((:days - 1) * INTERVAL '1 day')
        GROUP BY data_referencia
        ORDER BY data_referencia DESC
        """,
        {"days": days},
    )
    task_quality = fetch_all(
        engine,
        """
        SELECT
            task_id,
            status,
            COUNT(*) execucoes,
            COALESCE(SUM(registros_lidos), 0) registros_lidos,
            COALESCE(SUM(registros_validos), 0) registros_validos,
            COALESCE(SUM(registros_invalidos), 0) registros_invalidos,
            COALESCE(SUM(registros_inseridos), 0) registros_inseridos,
            COALESCE(SUM(registros_ignorados), 0) registros_ignorados,
            COALESCE(AVG(duracao_segundos), 0) duracao_media_segundos,
            MAX(created_at) ultima_execucao
        FROM pipeline_audit_log
        WHERE data_referencia >= CURRENT_DATE - ((:days - 1) * INTERVAL '1 day')
        GROUP BY task_id, status
        ORDER BY ultima_execucao DESC, task_id
        """,
        {"days": days},
    )
    recent_files = fetch_all(
        engine,
        """
        SELECT
            p.file_id, p.file_path, p.checksum, p.data_referencia, p.loja_id,
            COALESCE(l.loja_nome, 'Loja ' || p.loja_id::TEXT) loja_nome,
            p.camada_destino, p.status, p.registros_lidos, p.registros_validos,
            p.registros_invalidos, p.pipeline_version, p.processed_at, p.updated_at
        FROM processed_files p
        LEFT JOIN dim_loja l ON l.loja_id = p.loja_id
        ORDER BY p.updated_at DESC, p.file_id DESC
        LIMIT 30
        """,
    )
    recent_runs = fetch_all(
        engine,
        """
        SELECT
            audit_id, dag_id, run_id, task_id, data_referencia, status,
            registros_lidos, registros_validos, registros_invalidos,
            registros_inseridos, registros_ignorados, duracao_segundos,
            mensagem, created_at
        FROM pipeline_audit_log
        ORDER BY created_at DESC, audit_id DESC
        LIMIT 25
        """,
    )
    coverage = fetch_all(
        engine,
        """
        WITH ultima_data AS (
            SELECT MAX(data_referencia) data_referencia
            FROM processed_files
        )
        SELECT
            l.loja_id, l.loja_nome,
            COALESCE(COUNT(p.file_id), 0) arquivos,
            COALESCE(SUM(p.registros_lidos), 0) registros_lidos,
            COALESCE(SUM(p.registros_validos), 0) registros_validos,
            COALESCE(SUM(p.registros_invalidos), 0) registros_invalidos,
            MAX(p.updated_at) atualizado_em
        FROM dim_loja l
        CROSS JOIN ultima_data u
        LEFT JOIN processed_files p
          ON p.loja_id = l.loja_id AND p.data_referencia = u.data_referencia
        WHERE l.ativa = TRUE
        GROUP BY l.loja_id, l.loja_nome
        ORDER BY l.loja_id
        """,
    )

    for row in daily_quality:
        row["taxa_aprovacao"] = approval_rate(row["registros_lidos"], row["registros_invalidos"])
    for row in task_quality:
        row["taxa_aprovacao"] = approval_rate(row["registros_lidos"], row["registros_invalidos"])
    for row in coverage:
        row["taxa_aprovacao"] = approval_rate(row["registros_lidos"], row["registros_invalidos"])

    overview["taxa_aprovacao"] = approval_rate(
        overview.get("registros_lidos", 0),
        overview.get("registros_invalidos", 0),
    )
    overview["taxa_sucesso_execucoes"] = approval_rate(
        overview.get("total_execucoes", 0),
        overview.get("execucoes_falha", 0),
    )
    overview["total_rejeicoes"] = max(
        int(overview.get("registros_invalidos", 0) or 0),
        int(overview.get("rejeicoes_auditadas", 0) or 0),
    )
    alerts = []
    if overview.get("falhas_arquivo", 0) or overview.get("execucoes_falha", 0):
        alerts.append("Existem falhas registradas na auditoria ou no controle de arquivos.")
    if overview["total_rejeicoes"]:
        alerts.append("Há registros inválidos acumulados para investigar na quarentena.")
    latest_coverage = [row for row in coverage if int(row["arquivos"] or 0) < 3]
    if latest_coverage:
        alerts.append("A última data processada possui lojas com menos de três turnos carregados.")
    if not alerts:
        alerts.append("Nenhuma anomalia operacional detectada no período analisado.")

    return {
        "days": days,
        "overview": overview,
        "daily_quality": daily_quality,
        "task_quality": task_quality,
        "recent_files": recent_files,
        "recent_runs": recent_runs,
        "coverage": coverage,
        "alerts": alerts,
    }


def store_detail(engine: Engine, store_id: int, forecast_months: int) -> dict[str, Any]:
    """Monta uma visão analítica completa de uma loja específica."""
    store = fetch_one(
        engine,
        """
        SELECT loja_id, loja_nome, cidade, estado, regiao, data_abertura, tier, ativa
        FROM dim_loja
        WHERE loja_id = :store_id
        """,
        {"store_id": store_id},
    )
    if not store:
        raise ValueError(f"Loja {store_id} não encontrada.")

    source = evolution(engine)
    latest = (
        source["network"][-1]["competencia"] if source["network"] else latest_competence(engine)
    )
    if latest is None:
        raise ValueError("Não há histórico realizado para detalhar a loja.")

    year, month = (int(part) for part in latest.split("-"))
    params = {"store_id": store_id, "ano": year, "mes": month}
    history = [row for row in source["store_series"] if row["loja_id"] == store_id]
    if not history:
        raise ValueError(f"Loja {store_id} não possui movimento realizado.")

    overview = fetch_one(
        engine,
        """
        WITH vendas AS (
            SELECT
                COALESCE(SUM(valor_liquido) FILTER (WHERE status = 'CONCLUIDA'), 0) receita_liquida,
                COALESCE(SUM(valor_bruto) FILTER (WHERE status = 'CONCLUIDA'), 0) receita_bruta,
                COALESCE(SUM(margem_bruta) FILTER (WHERE status = 'CONCLUIDA'), 0) margem_bruta,
                COUNT(DISTINCT id_venda) FILTER (WHERE status = 'CONCLUIDA') pedidos,
                COUNT(*) FILTER (WHERE status = 'CANCELADA') canceladas,
                COUNT(*) FILTER (WHERE status = 'PENDENTE') pendentes,
                COALESCE(
                    SUM(valor_liquido) FILTER (WHERE status = 'CONCLUIDA') /
                    NULLIF(COUNT(DISTINCT id_venda) FILTER (WHERE status = 'CONCLUIDA'), 0), 0
                ) ticket_medio
            FROM fato_vendas
            WHERE loja_id = :store_id AND ano = :ano AND mes = :mes
        )
        SELECT
            v.*, r.ranking, r.market_share_pct, r.crescimento_mom,
            m.receita_orcada, m.variacao_absoluta, m.variacao_pct, m.status_semaforo,
            f.meta_atingida_pct, f.forecast_mes, f.run_rate_anual,
            d.ebitda, d.margem_ebitda_pct
        FROM vendas v
        LEFT JOIN vw_faturamento_por_loja r
          ON r.loja_id = :store_id AND r.ano = :ano AND r.mes = :mes
        LEFT JOIN vw_meta_vs_realizado m
          ON m.loja_id = :store_id AND m.ano = :ano AND m.mes = :mes
        LEFT JOIN vw_indicadores_fpa f
          ON f.loja_id = :store_id AND f.ano = :ano AND f.mes = :mes
        LEFT JOIN fato_dre d
          ON d.loja_id = :store_id AND d.ano = :ano AND d.mes = :mes
        """,
        params,
    )
    products = fetch_all(
        engine,
        """
        SELECT
            p.produto_id, p.produto_nome, p.categoria,
            SUM(v.valor_liquido) receita,
            SUM(v.quantidade) volume,
            SUM(v.margem_bruta) margem_bruta,
            SUM(v.margem_bruta) / NULLIF(SUM(v.valor_liquido), 0) * 100 margem_pct
        FROM fato_vendas v
        JOIN dim_produto p ON p.produto_sk = v.produto_sk
        WHERE v.loja_id = :store_id AND v.ano = :ano AND v.mes = :mes
          AND v.status = 'CONCLUIDA'
        GROUP BY p.produto_id, p.produto_nome, p.categoria
        ORDER BY receita DESC
        LIMIT 10
        """,
        params,
    )
    channels = fetch_all(
        engine,
        """
        SELECT
            canal_venda, forma_pagamento,
            COUNT(DISTINCT id_venda) pedidos,
            SUM(valor_liquido) receita,
            SUM(valor_liquido) / NULLIF(COUNT(DISTINCT id_venda), 0) ticket_medio
        FROM fato_vendas
        WHERE loja_id = :store_id AND ano = :ano AND mes = :mes
          AND status = 'CONCLUIDA'
        GROUP BY canal_venda, forma_pagamento
        ORDER BY receita DESC
        """,
        params,
    )
    status_mix = fetch_all(
        engine,
        """
        SELECT status, COUNT(*) registros, COALESCE(SUM(valor_liquido), 0) valor_liquido
        FROM fato_vendas
        WHERE loja_id = :store_id AND ano = :ano AND mes = :mes
        GROUP BY status
        ORDER BY registros DESC
        """,
        params,
    )
    quality = fetch_all(
        engine,
        """
        SELECT
            data_referencia,
            COUNT(*) arquivos,
            COUNT(*) FILTER (WHERE status = 'PROCESSED') processados,
            COUNT(*) FILTER (WHERE status = 'REPROCESSED') reprocessados,
            COUNT(*) FILTER (WHERE status = 'FAILED') falhas,
            COALESCE(SUM(registros_lidos), 0) registros_lidos,
            COALESCE(SUM(registros_validos), 0) registros_validos,
            COALESCE(SUM(registros_invalidos), 0) registros_invalidos,
            MAX(updated_at) atualizado_em
        FROM processed_files
        WHERE loja_id = :store_id
        GROUP BY data_referencia
        ORDER BY data_referencia DESC
        LIMIT 15
        """,
        {"store_id": store_id},
    )
    recent_files = fetch_all(
        engine,
        """
        SELECT
            file_id, file_path, checksum, data_referencia, camada_destino, status,
            registros_lidos, registros_validos, registros_invalidos,
            pipeline_version, processed_at, updated_at
        FROM processed_files
        WHERE loja_id = :store_id
        ORDER BY updated_at DESC, file_id DESC
        LIMIT 15
        """,
        {"store_id": store_id},
    )
    forecast_result = forecast(engine, forecast_months, 0)
    forecast_projection = [
        row for row in forecast_result["store_projection"] if row["loja_id"] == store_id
    ]
    ml_history = [
        {"competencia": row["competencia"], "receita": float(row["receita"] or 0)}
        for row in history
    ]
    ml_prediction = regression_prediction(ml_history, "receita", forecast_months, latest)

    for row in quality:
        row["taxa_aprovacao"] = approval_rate(row["registros_lidos"], row["registros_invalidos"])

    return {
        "latest_competence": latest,
        "forecast_months": forecast_months,
        "store": store,
        "overview": overview,
        "history": history,
        "products": products,
        "channels": channels,
        "status_mix": status_mix,
        "quality": quality,
        "recent_files": recent_files,
        "forecast_projection": forecast_projection,
        "ml_prediction": ml_prediction,
    }
