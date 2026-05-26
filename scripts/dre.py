"""Cálculo da demonstração de resultado gerencial para a camada Gold."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine

from config.settings import get_settings
from scripts.kpis import read_silver_month
from scripts.logger_config import get_pipeline_logger, log_metrics
from scripts.utils import atomic_write_dataframe, dataframe_records

DRE_PARAMETERS = {
    1: {"despesas_fixas": 45000.00, "depreciacao": 2500.00},
    2: {"despesas_fixas": 28000.00, "depreciacao": 2500.00},
    3: {"despesas_fixas": 35000.00, "depreciacao": 2500.00},
    4: {"despesas_fixas": 52000.00, "depreciacao": 2500.00},
    5: {"despesas_fixas": 30000.00, "depreciacao": 2500.00},
}


@dataclass
class DREResult:
    """Artefato persistido da demonstração de resultado gerencial."""

    caminho_dre: Path
    lojas_processadas: int
    receita_liquida_total: float


def calcular_dre(frame: pd.DataFrame) -> pd.DataFrame:
    """Calcula linhas da demonstração de resultado por loja e mês."""
    settings = get_settings()
    concluded = frame[frame["status"] == "CONCLUIDA"].copy()
    concluded["ano"] = pd.to_datetime(concluded["data_venda"]).dt.year
    concluded["mes"] = pd.to_datetime(concluded["data_venda"]).dt.month
    dre = concluded.groupby(["loja_id", "ano", "mes"], as_index=False).agg(
        receita_bruta=("valor_bruto", "sum"),
        descontos=("desconto_valor", "sum"),
        cmv=("custo_total", "sum"),
    )
    dre["impostos"] = dre["receita_bruta"] * settings.taxa_imposto
    dre["receita_liquida"] = dre["receita_bruta"] - dre["descontos"] - dre["impostos"]
    dre["lucro_bruto"] = dre["receita_liquida"] - dre["cmv"]
    dre["despesas_variaveis"] = dre["receita_liquida"] * settings.taxa_despesa_variavel
    dre["despesas_fixas"] = dre["loja_id"].map(
        {store_id: values["despesas_fixas"] for store_id, values in DRE_PARAMETERS.items()}
    )
    dre["ebitda"] = dre["lucro_bruto"] - dre["despesas_variaveis"] - dre["despesas_fixas"]
    dre["depreciacao"] = dre["loja_id"].map(
        {store_id: values["depreciacao"] for store_id, values in DRE_PARAMETERS.items()}
    )
    dre["ebit"] = dre["ebitda"] - dre["depreciacao"]
    dre["despesas_financeiras"] = dre["ebit"].clip(lower=0) * 0.02
    dre["resultado_antes_ir"] = dre["ebit"] - dre["despesas_financeiras"]
    for margin, value in (
        ("margem_bruta_pct", "lucro_bruto"),
        ("margem_ebitda_pct", "ebitda"),
        ("margem_liquida_pct", "resultado_antes_ir"),
    ):
        dre[margin] = dre[value] / dre["receita_liquida"] * 100
    return dre.round(2)


def upsert_dre_datawarehouse(dre: pd.DataFrame, engine: Engine) -> None:
    """Sincroniza linhas mensais calculadas de DRE com o Data Warehouse."""
    statement = text(
        """
        INSERT INTO fato_dre (
            loja_id, ano, mes, receita_bruta, descontos, impostos, receita_liquida, cmv,
            lucro_bruto, margem_bruta_pct, despesas_variaveis, despesas_fixas, ebitda,
            margem_ebitda_pct, depreciacao, ebit, despesas_financeiras, resultado_antes_ir,
            margem_liquida_pct
        ) VALUES (
            :loja_id, :ano, :mes, :receita_bruta, :descontos, :impostos, :receita_liquida,
            :cmv, :lucro_bruto, :margem_bruta_pct, :despesas_variaveis, :despesas_fixas,
            :ebitda, :margem_ebitda_pct, :depreciacao, :ebit, :despesas_financeiras,
            :resultado_antes_ir, :margem_liquida_pct
        )
        ON CONFLICT (loja_id, ano, mes) DO UPDATE SET
            receita_bruta = EXCLUDED.receita_bruta, descontos = EXCLUDED.descontos,
            impostos = EXCLUDED.impostos, receita_liquida = EXCLUDED.receita_liquida,
            cmv = EXCLUDED.cmv, lucro_bruto = EXCLUDED.lucro_bruto,
            margem_bruta_pct = EXCLUDED.margem_bruta_pct,
            despesas_variaveis = EXCLUDED.despesas_variaveis,
            despesas_fixas = EXCLUDED.despesas_fixas, ebitda = EXCLUDED.ebitda,
            margem_ebitda_pct = EXCLUDED.margem_ebitda_pct,
            depreciacao = EXCLUDED.depreciacao, ebit = EXCLUDED.ebit,
            despesas_financeiras = EXCLUDED.despesas_financeiras,
            resultado_antes_ir = EXCLUDED.resultado_antes_ir,
            margem_liquida_pct = EXCLUDED.margem_liquida_pct,
            updated_at = CURRENT_TIMESTAMP
        """
    )
    with engine.begin() as connection:
        connection.execute(statement, list(dataframe_records(dre)))


def gerar_dre(year: int, month: int, frame: pd.DataFrame | None = None) -> DREResult:
    """Gera e persiste o CSV Gold mensal da DRE gerencial."""
    source = frame if frame is not None else read_silver_month(year, month)
    dre = calcular_dre(source)
    destination = get_settings().gold_path / "dre_gerencial" / f"dre_{year}{month:02d}.csv"
    atomic_write_dataframe(dre, destination, "csv")
    log_metrics(
        get_pipeline_logger("gerar_dre_gerencial", f"{year}-{month:02d}-01"),
        "DRE Gold gerada",
        {"lojas_processadas": len(dre), "receita_liquida_total": dre["receita_liquida"].sum()},
    )
    return DREResult(destination, len(dre), float(dre["receita_liquida"].sum()))


def main() -> None:
    """Ponto de entrada CLI para geração da DRE gerencial."""
    parser = argparse.ArgumentParser(description="Gera DRE gerencial mensal.")
    parser.add_argument("year", type=int)
    parser.add_argument("month", type=int)
    args = parser.parse_args()
    print(gerar_dre(args.year, args.month))


if __name__ == "__main__":
    main()
