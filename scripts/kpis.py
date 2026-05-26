"""Cálculo de KPIs de vendas para a camada analítica Gold."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from config.settings import get_settings
from scripts.logger_config import get_pipeline_logger, log_metrics
from scripts.utils import atomic_write_dataframe


@dataclass
class KPIResult:
    """Artefatos Gold de KPIs gerados para um ano e mês."""

    resumo_path: Path
    lojas_path: Path
    produtos_path: Path
    registros_processados: int


def read_silver_month(year: int, month: int) -> pd.DataFrame:
    """Lê todas as partições Parquet Silver diárias do mês solicitado."""
    month_path = get_settings().silver_path / "vendas_tratadas" / f"ano={year}" / f"mes={month:02d}"
    sources = sorted(month_path.glob("dia=*/vendas_silver_*.parquet"))
    if not sources:
        raise FileNotFoundError(f"Nenhum arquivo Silver encontrado para {year}-{month:02d}")
    return pd.concat([pd.read_parquet(source) for source in sources], ignore_index=True)


def calcular_kpis(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Calcula indicadores de vendas consolidados, por loja e por produto."""
    concluded = frame[frame["status"] == "CONCLUIDA"].copy()
    concluded["competencia"] = pd.to_datetime(concluded["data_venda"]).dt.to_period("M").astype(str)
    summary = concluded.groupby("competencia", as_index=False).agg(
        faturamento_total=("valor_liquido", "sum"),
        receita_bruta=("valor_bruto", "sum"),
        desconto_total=("desconto_valor", "sum"),
        quantidade_total=("quantidade", "sum"),
        total_pedidos=("id_venda", "nunique"),
        margem_bruta=("margem_bruta", "sum"),
    )
    summary["ticket_medio"] = summary["faturamento_total"] / summary["total_pedidos"]
    summary["margem_bruta_pct"] = summary["margem_bruta"] / summary["faturamento_total"] * 100
    stores = concluded.groupby(["competencia", "loja_id", "loja_nome"], as_index=False).agg(
        faturamento=("valor_liquido", "sum"),
        pedidos=("id_venda", "nunique"),
        quantidade=("quantidade", "sum"),
        margem_bruta=("margem_bruta", "sum"),
    )
    stores["ticket_medio"] = stores["faturamento"] / stores["pedidos"]
    totals = stores.groupby("competencia")["faturamento"].transform("sum")
    stores["market_share_pct"] = stores["faturamento"] / totals * 100
    stores["ranking_receita"] = stores.groupby("competencia")["faturamento"].rank(
        ascending=False, method="dense"
    )
    stores["margem_bruta_pct"] = stores["margem_bruta"] / stores["faturamento"] * 100
    products = (
        concluded.groupby(["produto_id", "produto_nome", "categoria"], as_index=False)
        .agg(faturamento=("valor_liquido", "sum"), volume=("quantidade", "sum"))
        .sort_values("faturamento", ascending=False)
    )
    products["ranking_receita"] = products["faturamento"].rank(ascending=False, method="dense")
    products["ranking_volume"] = products["volume"].rank(ascending=False, method="dense")
    return summary.round(2), stores.round(2), products.round(2)


def gerar_kpis(year: int, month: int, frame: pd.DataFrame | None = None) -> KPIResult:
    """Calcula KPIs a partir da Silver e persiste saídas CSV Gold mensais."""
    source = frame if frame is not None else read_silver_month(year, month)
    summary, stores, products = calcular_kpis(source)
    competence = f"{year}{month:02d}"
    summary_path = get_settings().gold_path / "kpis_vendas" / f"kpis_vendas_{competence}.csv"
    stores_path = (
        get_settings().gold_path / "faturamento_por_loja" / f"faturamento_loja_{competence}.csv"
    )
    products_path = get_settings().gold_path / "top_produtos" / f"top_produtos_{competence}.csv"
    atomic_write_dataframe(summary, summary_path, "csv")
    atomic_write_dataframe(stores, stores_path, "csv")
    atomic_write_dataframe(products, products_path, "csv")
    log_metrics(
        get_pipeline_logger("gerar_kpis", f"{year}-{month:02d}-01"),
        "KPIs Gold gerados",
        {"registros_processados": len(source), "lojas": len(stores), "produtos": len(products)},
    )
    return KPIResult(summary_path, stores_path, products_path, len(source))


def main() -> None:
    """Ponto de entrada CLI para cálculo de KPIs."""
    parser = argparse.ArgumentParser(description="Gera KPIs mensais Gold.")
    parser.add_argument("year", type=int)
    parser.add_argument("month", type=int)
    args = parser.parse_args()
    print(gerar_kpis(args.year, args.month))


if __name__ == "__main__":
    main()
