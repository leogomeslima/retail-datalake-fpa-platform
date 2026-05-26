"""Execução em linha de comando do pipeline diário completo de dados."""

from __future__ import annotations

import argparse
from dataclasses import asdict

import pandas as pd

from scripts.dre import gerar_dre, upsert_dre_datawarehouse
from scripts.extract import extrair_raw_para_bronze
from scripts.fpa import gerar_fpa
from scripts.kpis import gerar_kpis, read_silver_month
from scripts.load import carregar_silver_datawarehouse, create_dw_engine
from scripts.logger_config import audit_json_path
from scripts.transform import transformar_bronze_para_silver
from scripts.utils import append_json_line, parse_reference_date
from scripts.validate import validar_bronze


def execute_daily_pipeline(
    data_referencia: str, load_database: bool = True, run_id: str = "cli_or_backfill"
) -> dict[str, object]:
    """Executa de Raw até Gold e, opcionalmente, carrega fatos e DRE no PostgreSQL."""
    reference = parse_reference_date(data_referencia)
    extraction = extrair_raw_para_bronze(data_referencia, [1, 2, 3, 4, 5])
    validation = validar_bronze(data_referencia, extraction.caminho_bronze)
    transformation = transformar_bronze_para_silver(data_referencia, validation.caminho_validos)
    silver_month = read_silver_month(reference.year, reference.month)
    kpis = gerar_kpis(reference.year, reference.month, silver_month)
    dre = gerar_dre(reference.year, reference.month, silver_month)
    fpa = gerar_fpa(reference.year, reference.month, silver_month)
    database_result = None
    if load_database:
        database_result = carregar_silver_datawarehouse(
            data_referencia, transformation.caminho_silver, run_id
        )
        upsert_dre_datawarehouse(
            pd.read_csv(dre.caminho_dre),
            create_dw_engine(),
        )
    summary: dict[str, object] = {
        "data_referencia": data_referencia,
        "extracao": asdict(extraction),
        "validacao": asdict(validation),
        "transformacao": asdict(transformation),
        "kpis": asdict(kpis),
        "dre": asdict(dre),
        "fpa": asdict(fpa),
        "carga_dw": asdict(database_result) if database_result else {"status": "nao_solicitada"},
    }
    append_json_line(audit_json_path(data_referencia), {"status": "SUCCESS", **summary})
    return summary


def main() -> None:
    """Ponto de entrada CLI para processamento diário completo."""
    parser = argparse.ArgumentParser(description="Executa pipeline diario Raw ate Gold e DW.")
    parser.add_argument("data_referencia")
    parser.add_argument("--skip-database", action="store_true")
    args = parser.parse_args()
    result = execute_daily_pipeline(args.data_referencia, not args.skip_database)
    print(result)


if __name__ == "__main__":
    main()
