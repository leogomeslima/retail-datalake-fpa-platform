"""Testes unitários das regras de transformação financeira Silver."""

from __future__ import annotations

import pandas as pd

from scripts.transform import (
    calcular_valores,
    enrich_time,
    standardize_types,
    transformar_dataframe,
)


class TestCalculoValores:
    """Valida fórmulas de cálculo financeiro."""

    def test_valor_bruto_calculado_corretamente(self, bronze_frame: pd.DataFrame) -> None:
        result = calcular_valores(standardize_types(bronze_frame.iloc[[0]]))
        assert result.iloc[0]["valor_bruto"] == 3500.00

    def test_valor_liquido_com_desconto(self, bronze_frame: pd.DataFrame) -> None:
        result = calcular_valores(standardize_types(bronze_frame.iloc[[0]]))
        assert result.iloc[0]["valor_liquido"] == 3325.00

    def test_valor_liquido_sem_desconto(self, bronze_frame: pd.DataFrame) -> None:
        result = calcular_valores(standardize_types(bronze_frame.iloc[[1]]))
        assert result.iloc[0]["valor_liquido"] == 350.00

    def test_margem_bruta_calculada(self, bronze_frame: pd.DataFrame) -> None:
        result = calcular_valores(standardize_types(bronze_frame.iloc[[0]]))
        assert result.iloc[0]["margem_bruta"] == 1225.00

    def test_desconto_percentual_calculado(self, bronze_frame: pd.DataFrame) -> None:
        result = calcular_valores(standardize_types(bronze_frame.iloc[[0]]))
        assert result.iloc[0]["desconto_pct_calc"] == 5.00


class TestPadronizacao:
    """Valida tipos, status e comportamento de desduplicação."""

    def test_colunas_em_snake_case(self, bronze_frame: pd.DataFrame) -> None:
        renamed = bronze_frame.rename(columns={"id_venda": " ID_VENDA "})
        assert "id_venda" in standardize_types(renamed).columns

    def test_datas_convertidas_corretamente(self, bronze_frame: pd.DataFrame) -> None:
        assert pd.api.types.is_datetime64_any_dtype(standardize_types(bronze_frame)["data_venda"])

    def test_cancelados_removidos_dataset_principal(self, bronze_frame: pd.DataFrame) -> None:
        silver, cancelled, _ = transformar_dataframe(bronze_frame)
        assert len(cancelled) == 1
        assert "CANCELADA" not in set(silver["status"])

    def test_duplicatas_removidas(self, bronze_frame: pd.DataFrame) -> None:
        duplicated = pd.concat([bronze_frame, bronze_frame.iloc[[0]]], ignore_index=True)
        silver, _, removed = transformar_dataframe(duplicated)
        assert removed == 1
        assert len(silver) == 2


class TestEnriquecimento:
    """Valida enriquecimento por calendário e período operacional."""

    def test_coluna_ano_criada(self, bronze_frame: pd.DataFrame) -> None:
        assert enrich_time(standardize_types(bronze_frame)).iloc[0]["ano"] == 2026

    def test_coluna_trimestre_criada(self, bronze_frame: pd.DataFrame) -> None:
        assert enrich_time(standardize_types(bronze_frame)).iloc[0]["trimestre"] == 1

    def test_periodo_classificado_corretamente(self, bronze_frame: pd.DataFrame) -> None:
        result = enrich_time(standardize_types(bronze_frame))
        assert result.iloc[0]["periodo"] == "MANHA"
        assert result.iloc[1]["periodo"] == "NOITE"
