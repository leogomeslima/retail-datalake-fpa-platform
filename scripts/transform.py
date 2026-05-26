"""Transformações financeiras de Bronze para Silver."""

from __future__ import annotations

import argparse
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from config.settings import get_settings
from scripts.logger_config import get_pipeline_logger, log_metrics
from scripts.utils import atomic_write_dataframe, date_partition_path, utc_timestamp


@dataclass
class TransformationResult:
    """Artefatos de transformação e contagens do processamento de negócio."""

    registros_entrada: int
    registros_saida: int
    registros_cancelados: int
    duplicatas_removidas: int
    caminho_silver: Path
    caminho_cancelados: Path


def standardize_types(frame: pd.DataFrame) -> pd.DataFrame:
    """Normaliza nomes e converte valores Bronze em tipos analíticos."""
    result = frame.copy()
    result.columns = [column.strip().lower() for column in result.columns]
    result["data_venda"] = pd.to_datetime(result["data_venda"], errors="raise")
    numeric = [
        "loja_id",
        "cliente_id",
        "produto_id",
        "quantidade",
        "valor_unitario",
        "custo_unitario",
        "desconto_valor",
    ]
    for column in numeric:
        result[column] = pd.to_numeric(result[column], errors="raise")
    for column in ["status", "cliente_segmento"]:
        result[column] = result[column].astype(str).str.strip().str.upper()
    if "canal_venda" in result:
        result["canal_venda"] = result["canal_venda"].replace({"Loja Fisica": "Loja Física"})
    return result


def calcular_valores(frame: pd.DataFrame) -> pd.DataFrame:
    """Calcula vendas brutas, vendas líquidas, custo, desconto e margem."""
    result = frame.copy()
    result["valor_bruto"] = (result["quantidade"] * result["valor_unitario"]).round(2)
    result["valor_liquido"] = (result["valor_bruto"] - result["desconto_valor"]).round(2)
    result["custo_total"] = (result["quantidade"] * result["custo_unitario"]).round(2)
    result["margem_bruta"] = (result["valor_liquido"] - result["custo_total"]).round(2)
    result["margem_bruta_pct"] = np.where(
        result["valor_liquido"] > 0,
        (result["margem_bruta"] / result["valor_liquido"] * 100).round(2),
        0.0,
    )
    result["desconto_pct_calc"] = np.where(
        result["valor_bruto"] > 0,
        (result["desconto_valor"] / result["valor_bruto"] * 100).round(2),
        0.0,
    )
    return result


def enrich_time(frame: pd.DataFrame) -> pd.DataFrame:
    """Acrescenta atributos dimensionais de calendário e período do dia."""
    result = frame.copy()
    timestamp = result["data_venda"]
    result["data_sk"] = timestamp.dt.strftime("%Y%m%d").astype(int)
    result["ano"] = timestamp.dt.year
    result["mes"] = timestamp.dt.month
    result["dia"] = timestamp.dt.day
    result["trimestre"] = timestamp.dt.quarter
    result["semestre"] = np.where(result["mes"] <= 6, 1, 2)
    result["dia_semana"] = timestamp.dt.dayofweek + 1
    result["semana_ano"] = timestamp.dt.isocalendar().week.astype(int)
    hours = timestamp.dt.hour
    result["periodo"] = np.select(
        [hours.between(6, 11), hours.between(12, 17), hours.between(18, 22)],
        ["MANHA", "TARDE", "NOITE"],
        default="MADRUGADA",
    )
    return result


def transformar_dataframe(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, int]:
    """Executa transformações determinísticas nas linhas Bronze aceitas."""
    deduplicated = frame.drop_duplicates(subset=["id_venda", "loja_id"], keep="last")
    removed = len(frame) - len(deduplicated)
    transformed = enrich_time(calcular_valores(standardize_types(deduplicated)))
    transformed["processed_at"] = utc_timestamp()
    transformed["pipeline_version"] = get_settings().pipeline_version
    cancelled = transformed[transformed["status"] == "CANCELADA"].copy()
    silver = transformed[transformed["status"] != "CANCELADA"].copy()
    if (silver["valor_liquido"] < 0).any():
        raise ValueError("Transformação gerou valor líquido negativo")
    return silver, cancelled, removed


def transformar_bronze_para_silver(
    data_referencia: str, caminho_validos: Path | None = None
) -> TransformationResult:
    """Transforma registros Bronze diários aceitos e persiste dados Silver Parquet."""
    started = time.perf_counter()
    logger = get_pipeline_logger("transformar_silver", data_referencia)
    bronze_partition = date_partition_path(get_settings().bronze_path / "vendas", data_referencia)
    source = (
        caminho_validos
        or bronze_partition / f"vendas_validadas_{data_referencia.replace('-', '')}.csv"
    )
    frame = pd.read_csv(source)
    silver, cancelled, removed = transformar_dataframe(frame)
    partition = date_partition_path(get_settings().silver_path / "vendas_tratadas", data_referencia)
    destination = partition / f"vendas_silver_{data_referencia.replace('-', '')}.parquet"
    cancelled_path = partition / f"vendas_canceladas_{data_referencia.replace('-', '')}.parquet"
    atomic_write_dataframe(silver, destination, "parquet")
    atomic_write_dataframe(cancelled, cancelled_path, "parquet")
    result = TransformationResult(
        len(frame), len(silver), len(cancelled), removed, destination, cancelled_path
    )
    log_metrics(
        logger,
        "Transformação Silver concluída",
        {
            "registros_entrada": result.registros_entrada,
            "registros_saida": result.registros_saida,
            "registros_cancelados": result.registros_cancelados,
            "duplicatas_removidas": removed,
            "duracao_ms": round((time.perf_counter() - started) * 1000),
        },
    )
    return result


def main() -> None:
    """Ponto de entrada CLI para criação da camada Silver."""
    parser = argparse.ArgumentParser(description="Transforma Bronze validado em Silver.")
    parser.add_argument("data_referencia")
    args = parser.parse_args()
    result = transformar_bronze_para_silver(args.data_referencia)
    print(f"Silver: {result.caminho_silver} | registros: {result.registros_saida}")


if __name__ == "__main__":
    main()
