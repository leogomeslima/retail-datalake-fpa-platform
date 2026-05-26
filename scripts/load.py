"""Serviços idempotentes de carga do Data Warehouse PostgreSQL."""

from __future__ import annotations

import argparse
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from config.settings import get_settings
from scripts.logger_config import audit_json_path, get_pipeline_logger, log_metrics
from scripts.utils import (
    append_json_line,
    dataframe_records,
    date_partition_path,
    load_json,
    raw_store_partition,
    read_config_json,
)


@dataclass
class LoadResult:
    """Contagens produzidas por uma execução idempotente de carga de fatos."""

    registros_recebidos: int
    registros_inseridos: int
    registros_atualizados: int
    arquivos_processados: int
    duracao_segundos: float


FACT_UPSERT = text(
    """
    INSERT INTO fato_vendas (
        id_venda, loja_sk, produto_sk, cliente_sk, data_sk, loja_id, produto_id, cliente_id,
        data_venda, canal_venda, forma_pagamento, parcelas, vendedor_id, quantidade,
        valor_unitario, custo_unitario, desconto_valor, desconto_pct, valor_bruto,
        valor_liquido, custo_total, margem_bruta, margem_bruta_pct, status,
        motivo_cancelamento, ano, mes, dia, trimestre, periodo, arquivo_origem, pipeline_id,
        processed_at
    )
    SELECT
        :id_venda, l.loja_sk, p.produto_sk, c.cliente_sk, :data_sk, :loja_id, :produto_id,
        :cliente_id, :data_venda, :canal_venda, :forma_pagamento, :parcelas, :vendedor_id,
        :quantidade, :valor_unitario, :custo_unitario, :desconto_valor, :desconto_pct_calc,
        :valor_bruto, :valor_liquido, :custo_total, :margem_bruta, :margem_bruta_pct,
        :status, :motivo_cancelamento, :ano, :mes, :dia, :trimestre, :periodo,
        :arquivo_origem, CAST(:pipeline_id AS UUID), CURRENT_TIMESTAMP
    FROM dim_loja l
    JOIN dim_produto p ON p.produto_id = :produto_id
    JOIN dim_cliente c ON c.cliente_id = :cliente_id
    WHERE l.loja_id = :loja_id
    ON CONFLICT (id_venda, loja_id) DO UPDATE SET
        produto_sk = EXCLUDED.produto_sk,
        cliente_sk = EXCLUDED.cliente_sk,
        valor_unitario = EXCLUDED.valor_unitario,
        desconto_valor = EXCLUDED.desconto_valor,
        desconto_pct = EXCLUDED.desconto_pct,
        valor_bruto = EXCLUDED.valor_bruto,
        valor_liquido = EXCLUDED.valor_liquido,
        custo_total = EXCLUDED.custo_total,
        margem_bruta = EXCLUDED.margem_bruta,
        margem_bruta_pct = EXCLUDED.margem_bruta_pct,
        status = EXCLUDED.status,
        motivo_cancelamento = EXCLUDED.motivo_cancelamento,
        arquivo_origem = EXCLUDED.arquivo_origem,
        pipeline_id = EXCLUDED.pipeline_id,
        processed_at = CURRENT_TIMESTAMP
    """
)


def create_dw_engine() -> Engine:
    """Cria uma conexão SQLAlchemy agrupada para o Data Warehouse."""
    settings = get_settings()
    return create_engine(
        settings.database_url,
        pool_size=settings.postgres_pool_size,
        max_overflow=settings.postgres_max_overflow,
        pool_pre_ping=True,
    )


def upsert_customers(frame: pd.DataFrame, connection: Any) -> None:
    """Sincroniza a dimensão simplificada de clientes a partir dos registros Silver."""
    statement = text(
        """
        INSERT INTO dim_cliente (cliente_id, cliente_nome, segmento)
        VALUES (:cliente_id, :cliente_nome, :cliente_segmento)
        ON CONFLICT (cliente_id) DO UPDATE SET
            cliente_nome = EXCLUDED.cliente_nome,
            segmento = EXCLUDED.segmento
        """
    )
    customers = frame[["cliente_id", "cliente_nome", "cliente_segmento"]].drop_duplicates(
        subset=["cliente_id"], keep="last"
    )
    connection.execute(statement, list(dataframe_records(customers)))


def ensure_time_dimension(frame: pd.DataFrame, connection: Any) -> None:
    """Insere datas de calendário vindas da Silver ao processar meses futuros."""
    statement = text(
        """
        INSERT INTO dim_tempo (
            data_sk, data, ano, semestre, trimestre, mes, nome_mes, semana_ano,
            dia, dia_semana, nome_dia_semana, e_fim_semana
        ) VALUES (
            :data_sk, :data, :ano, :semestre, :trimestre, :mes, :nome_mes, :semana_ano,
            :dia, :dia_semana, :nome_dia_semana, :e_fim_semana
        )
        ON CONFLICT (data_sk) DO NOTHING
        """
    )
    dates = pd.to_datetime(frame["data_venda"]).dt.normalize().drop_duplicates().sort_values()
    calendar_rows = [
        {
            "data_sk": int(day.strftime("%Y%m%d")),
            "data": day.date(),
            "ano": day.year,
            "semestre": 1 if day.month <= 6 else 2,
            "trimestre": day.quarter,
            "mes": day.month,
            "nome_mes": day.strftime("%B"),
            "semana_ano": int(day.isocalendar().week),
            "dia": day.day,
            "dia_semana": day.isoweekday(),
            "nome_dia_semana": day.strftime("%A"),
            "e_fim_semana": day.isoweekday() in (6, 7),
        }
        for day in dates
    ]
    connection.execute(statement, calendar_rows)


def ensure_budgets(frame: pd.DataFrame, connection: Any) -> None:
    """Provisiona orçamentos mensais para novos anos usando crescimento configurável."""
    settings = get_settings()
    config = read_config_json("orcamento_config.json")
    base_year = int(config["ano"])
    statement = text(
        """
        INSERT INTO fato_orcamento (
            loja_sk, loja_id, ano, mes, receita_orcada, margem_bruta_orcada,
            despesas_fixas_orcadas, despesas_var_orcadas, resultado_orcado
        )
        SELECT loja_sk, :loja_id, :ano, :mes, :receita_orcada, :margem_bruta_orcada,
               :despesas_fixas_orcadas, :despesas_var_orcadas, :resultado_orcado
        FROM dim_loja WHERE loja_id = :loja_id
        ON CONFLICT (loja_id, ano, mes) DO NOTHING
        """
    )
    rows: list[dict[str, float | int]] = []
    for year in sorted(set(int(value) for value in frame["ano"])):
        factor = (1 + settings.budget_annual_growth) ** (year - base_year)
        for budget in config["orcamentos"]:
            for month in range(1, 13):
                revenue = float(budget["receita_mensal"]) * factor
                fixed = float(budget["despesas_fixas_orcadas"]) * factor
                rows.append(
                    {
                        "loja_id": int(budget["loja_id"]),
                        "ano": year,
                        "mes": month,
                        "receita_orcada": revenue,
                        "margem_bruta_orcada": float(budget["margem_bruta_orcada"]),
                        "despesas_fixas_orcadas": fixed,
                        "despesas_var_orcadas": revenue * settings.taxa_despesa_variavel,
                        "resultado_orcado": revenue * 0.22,
                    }
                )
    connection.execute(statement, rows)


def existing_keys(frame: pd.DataFrame, connection: Any) -> set[tuple[str, int]]:
    """Lê chaves de fatos já presentes para os identificadores carregados no lote."""
    keys: set[tuple[str, int]] = set()
    query = text(
        "SELECT id_venda, loja_id FROM fato_vendas "
        "WHERE id_venda = :id_venda AND loja_id = :loja_id"
    )
    for record in dataframe_records(frame[["id_venda", "loja_id"]]):
        row = connection.execute(query, record).first()
        if row:
            keys.add((row.id_venda, row.loja_id))
    return keys


def record_processed_files(frame: pd.DataFrame, data_referencia: str, connection: Any) -> int:
    """Registra checksum do arquivo de origem e status de reprocessamento."""
    query = text(
        """
        INSERT INTO processed_files (
            file_path, checksum, data_referencia, loja_id, camada_destino, status,
            registros_lidos, registros_validos, registros_invalidos, pipeline_version
        ) VALUES (
            :file_path, :checksum, :data_referencia, :loja_id, 'SILVER', 'PROCESSED',
            :registros, :registros, 0, :pipeline_version
        )
        ON CONFLICT (file_path) DO UPDATE SET
            checksum = EXCLUDED.checksum,
            status = CASE
                WHEN processed_files.checksum = EXCLUDED.checksum THEN 'PROCESSED'
                ELSE 'REPROCESSED'
            END,
            registros_lidos = EXCLUDED.registros_lidos,
            registros_validos = EXCLUDED.registros_validos,
            pipeline_version = EXCLUDED.pipeline_version,
            updated_at = CURRENT_TIMESTAMP
        """
    )
    grouped = frame.groupby(["arquivo_origem", "arquivo_checksum", "loja_id"], dropna=False).size()
    recorded_paths: set[str] = set()
    for (file_path, checksum, loja_id), records in grouped.items():
        recorded_paths.add(str(file_path))
        connection.execute(
            query,
            {
                "file_path": file_path,
                "checksum": checksum,
                "data_referencia": data_referencia,
                "loja_id": int(loja_id),
                "registros": int(records),
                "pipeline_version": get_settings().pipeline_version,
            },
        )
    empty_files = 0
    for loja_id in range(1, 6):
        for source in raw_store_partition(loja_id, data_referencia).glob("*.json"):
            if str(source) in recorded_paths:
                continue
            payload = load_json(source)
            if payload["quantidade_registros"] != 0:
                continue
            connection.execute(
                query,
                {
                    "file_path": str(source),
                    "checksum": payload["checksum"],
                    "data_referencia": data_referencia,
                    "loja_id": loja_id,
                    "registros": 0,
                    "pipeline_version": get_settings().pipeline_version,
                },
            )
            empty_files += 1
    return len(grouped) + empty_files


def carregar_fato_vendas(
    frame: pd.DataFrame, engine: Engine, data_referencia: str | None = None
) -> LoadResult:
    """Carrega fatos Silver com UPSERT PostgreSQL sem duplicar vendas."""
    started = time.perf_counter()
    reference = data_referencia or pd.to_datetime(frame["data_venda"]).min().date().isoformat()
    with engine.begin() as connection:
        ensure_time_dimension(frame, connection)
        ensure_budgets(frame, connection)
        upsert_customers(frame, connection)
        already_present = existing_keys(frame, connection)
        connection.execute(FACT_UPSERT, list(dataframe_records(frame)))
        file_count = record_processed_files(frame, reference, connection)
        connection.execute(text("ANALYZE fato_vendas"))
    inserted = len(frame) - len(already_present)
    result = LoadResult(
        len(frame),
        inserted,
        len(already_present),
        file_count,
        round(time.perf_counter() - started, 2),
    )
    return result


def carregar_silver_datawarehouse(
    data_referencia: str,
    silver_path: Path | None = None,
    run_id: str = "cli_or_backfill",
) -> LoadResult:
    """Carrega fatos ativos e cancelados, persistidos separadamente, no PostgreSQL."""
    logger = get_pipeline_logger("carregar_datawarehouse", data_referencia)
    source = silver_path or (
        date_partition_path(get_settings().silver_path / "vendas_tratadas", data_referencia)
        / f"vendas_silver_{data_referencia.replace('-', '')}.parquet"
    )
    frame = pd.read_parquet(source)
    cancelled_path = source.with_name(source.name.replace("vendas_silver_", "vendas_canceladas_"))
    if cancelled_path.exists():
        frame = pd.concat([frame, pd.read_parquet(cancelled_path)], ignore_index=True)
    engine = create_dw_engine()
    result = carregar_fato_vendas(frame, engine, data_referencia)
    metrics = result.__dict__
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO pipeline_audit_log (
                    dag_id, run_id, task_id, data_referencia, status, registros_lidos,
                    registros_validos, registros_invalidos, registros_inseridos,
                    registros_ignorados, duracao_segundos, mensagem
                ) VALUES (
                    'etl_vendas_fpa', :run_id, 'carregar_datawarehouse',
                    :data_referencia, 'SUCCESS', :recebidos, :recebidos, 0,
                    :inseridos, :atualizados, :duracao, 'Carga Silver concluída'
                )
                """
            ),
            {
                "data_referencia": data_referencia,
                "run_id": run_id,
                "recebidos": result.registros_recebidos,
                "inseridos": result.registros_inseridos,
                "atualizados": result.registros_atualizados,
                "duracao": result.duracao_segundos,
            },
        )
    log_metrics(logger, "Carga Data Warehouse concluída", metrics)
    append_json_line(
        audit_json_path(data_referencia),
        {"task_id": "carregar_datawarehouse", "status": "SUCCESS", **metrics},
    )
    return result


def main() -> None:
    """Ponto de entrada CLI para carga Silver no PostgreSQL."""
    parser = argparse.ArgumentParser(description="Carrega a partição Silver no PostgreSQL.")
    parser.add_argument("data_referencia")
    args = parser.parse_args()
    result = carregar_silver_datawarehouse(args.data_referencia)
    print(result)


if __name__ == "__main__":
    main()
