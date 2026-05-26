"""Teste de integração PostgreSQL da carga idempotente de fatos por UPSERT."""

from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
import pytest
from sqlalchemy import create_engine, text

from scripts.load import carregar_fato_vendas
from scripts.transform import transformar_dataframe


@pytest.mark.skipif(
    "TEST_DATABASE_URL" not in os.environ,
    reason="Defina TEST_DATABASE_URL para executar integracao PostgreSQL real.",
)
def test_load_twice_keeps_one_fact_per_business_key(bronze_frame: pd.DataFrame) -> None:
    """Carrega os mesmos registros Silver duas vezes e verifica ausência de duplicação."""
    engine = create_engine(os.environ["TEST_DATABASE_URL"])
    project = Path(__file__).resolve().parents[2]
    with engine.begin() as connection:
        for filename in ("schema.sql", "seed_lojas.sql", "seed_produtos.sql", "seed_dim_tempo.sql"):
            connection.exec_driver_sql(
                (project / "database" / filename).read_text(encoding="utf-8")
            )
    silver, _, _ = transformar_dataframe(bronze_frame.iloc[[0]])
    carregar_fato_vendas(silver, engine, "2026-01-08")
    carregar_fato_vendas(silver, engine, "2026-01-08")
    with engine.begin() as connection:
        count = connection.execute(
            text("SELECT COUNT(*) FROM fato_vendas WHERE id_venda = :id"),
            {"id": silver.iloc[0]["id_venda"]},
        ).scalar_one()
    assert count == 1
