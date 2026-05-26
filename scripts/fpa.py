"""Indicadores de planejamento e análise financeira para desempenho mensal."""

from __future__ import annotations

import argparse
import calendar
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from config.settings import get_settings
from scripts.kpis import read_silver_month
from scripts.logger_config import get_pipeline_logger, log_metrics
from scripts.utils import atomic_write_dataframe, read_config_json


@dataclass
class FPAResult:
    """Saída mensal de indicadores FP&A."""

    caminho_fpa: Path
    lojas_processadas: int
    alertas_vermelhos: int


def monthly_budget(year: int, month: int) -> pd.DataFrame:
    """Expande valores de orçamento configurados para o mês solicitado."""
    config = read_config_json("orcamento_config.json")
    budget = pd.DataFrame(config["orcamentos"])
    factor = (1 + get_settings().budget_annual_growth) ** (year - int(config["ano"]))
    budget["receita_mensal"] = budget["receita_mensal"] * factor
    budget["despesas_fixas_orcadas"] = budget["despesas_fixas_orcadas"] * factor
    budget["ano"] = year
    budget["mes"] = month
    budget = budget.rename(columns={"receita_mensal": "receita_orcada"})
    return budget


def calcular_indicadores_fpa(
    month: int, year: int, frame: pd.DataFrame | None = None
) -> pd.DataFrame:
    """Compara receita realizada com orçamento e gera previsões de ritmo anual."""
    settings = get_settings()
    source = frame if frame is not None else read_silver_month(year, month)
    concluded = source[source["status"] == "CONCLUIDA"].copy()
    concluded["data"] = pd.to_datetime(concluded["data_venda"]).dt.date
    actual = concluded.groupby("loja_id", as_index=False).agg(
        receita_realizada=("valor_liquido", "sum"),
        margem_bruta=("margem_bruta", "sum"),
        dias_com_venda=("data", "nunique"),
    )
    result = monthly_budget(year, month).merge(actual, on="loja_id", how="left").fillna(0)
    result["variacao_absoluta"] = result["receita_realizada"] - result["receita_orcada"]
    result["variacao_percentual"] = result["variacao_absoluta"] / result["receita_orcada"] * 100
    result["meta_atingida_pct"] = result["receita_realizada"] / result["receita_orcada"] * 100
    result["media_diaria"] = result["receita_realizada"] / result["dias_com_venda"].replace(0, 1)
    days_in_month = calendar.monthrange(year, month)[1]
    result["forecast_mes"] = result["media_diaria"] * days_in_month
    result["run_rate_anual"] = result["forecast_mes"] * 12
    result["margem_bruta_pct_realizada"] = (
        result["margem_bruta"] / result["receita_realizada"].replace(0, 1) * 100
    )
    result["ranking_receita"] = result["receita_realizada"].rank(ascending=False, method="dense")
    result["ranking_margem"] = result["margem_bruta_pct_realizada"].rank(
        ascending=False, method="dense"
    )
    result["ranking_meta"] = result["meta_atingida_pct"].rank(ascending=False, method="dense")
    achieved = result["receita_realizada"] / result["receita_orcada"]
    result["status_semaforo"] = "VERDE"
    result.loc[achieved < settings.alerta_meta_amarelo, "status_semaforo"] = "AMARELO"
    result.loc[achieved < settings.alerta_meta_vermelho, "status_semaforo"] = "VERMELHO"
    return result.round(2)


def gerar_fpa(year: int, month: int, frame: pd.DataFrame | None = None) -> FPAResult:
    """Persiste orçamento, forecast e indicadores de ritmo anual na camada Gold."""
    indicators = calcular_indicadores_fpa(month, year, frame)
    destination = get_settings().gold_path / "indicadores_fpa" / f"fpa_{year}{month:02d}.csv"
    atomic_write_dataframe(indicators, destination, "csv")
    red_alerts = int((indicators["status_semaforo"] == "VERMELHO").sum())
    log_metrics(
        get_pipeline_logger("gerar_fpa", f"{year}-{month:02d}-01"),
        "Indicadores FPA Gold gerados",
        {"lojas_processadas": len(indicators), "alertas_vermelhos": red_alerts},
    )
    return FPAResult(destination, len(indicators), red_alerts)


def main() -> None:
    """Ponto de entrada CLI para cálculo mensal de FP&A."""
    parser = argparse.ArgumentParser(description="Gera indicadores mensais FP&A.")
    parser.add_argument("year", type=int)
    parser.add_argument("month", type=int)
    args = parser.parse_args()
    print(gerar_fpa(args.year, args.month))


if __name__ == "__main__":
    main()
