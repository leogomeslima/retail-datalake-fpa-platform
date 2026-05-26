"""Fixtures reutilizáveis de teste para transformações financeiras ETL."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd
import pytest

from config.settings import get_settings


@pytest.fixture(autouse=True)
def temporary_data_lake(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Isola cada teste em um Data Lake local novo e gravável."""
    monkeypatch.setenv("DATA_LAKE_BASE_PATH", str(tmp_path / "data"))
    get_settings.cache_clear()
    yield tmp_path / "data"
    get_settings.cache_clear()


@pytest.fixture
def bronze_frame() -> pd.DataFrame:
    """Retorna vendas equivalentes a Bronze, incluindo um item cancelado."""
    base = {
        "loja_id": 1,
        "loja_nome": "Loja Centro",
        "cidade": "São Paulo",
        "estado": "SP",
        "cliente_id": 1001,
        "cliente_nome": "Maria Souza",
        "cliente_segmento": "VAREJO",
        "produto_id": 501,
        "produto_nome": "Notebook Dell Inspiron 15",
        "categoria": "Informática",
        "subcategoria": "Notebooks",
        "quantidade": 1,
        "valor_unitario": 3500.00,
        "custo_unitario": 2100.00,
        "desconto_valor": 175.00,
        "desconto_percentual": 5.00,
        "canal_venda": "Loja Física",
        "forma_pagamento": "PIX",
        "parcelas": 1,
        "vendedor_id": "VND-001-01",
        "data_venda": datetime(2026, 1, 8, 10, 30).isoformat(),
        "status": "CONCLUIDA",
        "motivo_cancelamento": None,
        "pipeline_id": "b37e2d3f-caf2-4ab4-886d-a2bcfd083119",
        "arquivo_checksum": "a" * 64,
        "arquivo_origem": "raw/vendas_1.json",
    }
    second = base | {
        "id_venda": "VND-2026-001-0000002",
        "produto_id": 506,
        "produto_nome": "Fone JBL Bluetooth",
        "valor_unitario": 350.00,
        "custo_unitario": 140.00,
        "desconto_valor": 0.00,
        "data_venda": datetime(2026, 1, 8, 19, 45).isoformat(),
    }
    first = base | {"id_venda": "VND-2026-001-0000001"}
    cancelled = base | {
        "id_venda": "VND-2026-001-0000003",
        "status": "CANCELADA",
        "motivo_cancelamento": "Arrependimento",
    }
    return pd.DataFrame([first, second, cancelled])
