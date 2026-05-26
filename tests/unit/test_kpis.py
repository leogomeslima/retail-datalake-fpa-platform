"""Testes unitários de KPIs de vendas e relatórios gerenciais."""

from __future__ import annotations

import pandas as pd

from scripts.dre import calcular_dre
from scripts.fpa import calcular_indicadores_fpa
from scripts.kpis import calcular_kpis
from scripts.transform import transformar_dataframe


class TestKPIs:
    """Valida indicadores de negócio agregados."""

    def test_faturamento_total_soma_correta(self, bronze_frame: pd.DataFrame) -> None:
        silver, _, _ = transformar_dataframe(bronze_frame)
        summary, _, _ = calcular_kpis(silver)
        assert summary.iloc[0]["faturamento_total"] == 3675.00

    def test_ticket_medio_calculado(self, bronze_frame: pd.DataFrame) -> None:
        silver, _, _ = transformar_dataframe(bronze_frame)
        summary, _, _ = calcular_kpis(silver)
        assert summary.iloc[0]["ticket_medio"] == 1837.50

    def test_ranking_lojas_ordenado(self, bronze_frame: pd.DataFrame) -> None:
        other_store = bronze_frame.iloc[[1]].assign(
            id_venda="VND-2026-002-0000004", loja_id=2, loja_nome="Loja Norte"
        )
        silver, _, _ = transformar_dataframe(pd.concat([bronze_frame, other_store]))
        _, stores, _ = calcular_kpis(silver)
        assert stores.sort_values("ranking_receita").iloc[0]["loja_id"] == 1

    def test_market_share_soma_100pct(self, bronze_frame: pd.DataFrame) -> None:
        silver, _, _ = transformar_dataframe(bronze_frame)
        _, stores, _ = calcular_kpis(silver)
        assert round(stores["market_share_pct"].sum(), 2) == 100.00


class TestFinanceiro:
    """Valida cálculos de DRE, orçamento e forecast."""

    def test_dre_receita_liquida_desconta_imposto(self, bronze_frame: pd.DataFrame) -> None:
        silver, _, _ = transformar_dataframe(bronze_frame)
        dre = calcular_dre(silver)
        assert dre.iloc[0]["receita_liquida"] == 3213.00

    def test_fpa_calcula_forecast_e_status(self, bronze_frame: pd.DataFrame) -> None:
        silver, _, _ = transformar_dataframe(bronze_frame)
        indicators = calcular_indicadores_fpa(1, 2026, silver)
        store = indicators[indicators["loja_id"] == 1].iloc[0]
        assert store["forecast_mes"] == 113925.00
        assert store["status_semaforo"] == "VERMELHO"
