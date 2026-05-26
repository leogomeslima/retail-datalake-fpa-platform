"""Testes do comportamento real de emissão de turnos do PDV."""

from __future__ import annotations

from datetime import date

import pytest

from app_vendas.datalake_service import DataLakeService
from app_vendas.venda_service import VendaService


def test_store_shifts_generate_distinct_sales_and_customers() -> None:
    """Permite fechar todos os turnos de uma loja sem colisão de chaves."""
    service = VendaService(seed=77)
    morning = service.generate_shift(1, date(2026, 5, 25), "MANHA", 3)
    afternoon = service.generate_shift(1, date(2026, 5, 25), "TARDE", 3)

    morning_sales = {sale["id_venda"] for sale in morning.vendas}
    afternoon_sales = {sale["id_venda"] for sale in afternoon.vendas}
    morning_customers = {sale["cliente_id"] for sale in morning.vendas}
    afternoon_customers = {sale["cliente_id"] for sale in afternoon.vendas}

    assert morning_sales.isdisjoint(afternoon_sales)
    assert morning_customers.isdisjoint(afternoon_customers)


def test_shift_document_is_immutable_after_emission() -> None:
    """Recusa um segundo fechamento para a mesma loja, data e turno."""
    shift = VendaService(seed=81).generate_shift(2, date(2026, 5, 25), "NOITE", 2)
    storage = DataLakeService()
    storage.save_shift(shift, date(2026, 5, 25))

    with pytest.raises(FileExistsError, match="não será sobrescrito"):
        storage.save_shift(shift, date(2026, 5, 25))
