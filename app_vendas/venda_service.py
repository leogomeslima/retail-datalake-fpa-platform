"""Serviço de negócio que produz um turno de loja com transações realistas."""

from __future__ import annotations

import random
from datetime import date, datetime, time
from typing import Any
from uuid import uuid4

from faker import Faker

from app_vendas.models import ShiftFile
from scripts.data_quality import VendaEntrada
from scripts.generate_sales_data import (
    SHIFT_HOURS,
    STORE_PROFILES,
    build_customer,
    build_sale,
    choose_product,
)
from scripts.utils import read_config_json

SHIFT_SEQUENCE_OFFSET = {"MANHA": 100000, "TARDE": 200000, "NOITE": 300000}


class VendaService:
    """Cria transações do PDV segundo o perfil da loja e as regras do esquema."""

    def __init__(self, seed: int = 20260524) -> None:
        """Inicializa recursos determinísticos de geração de dados."""
        self.rng = random.Random(seed)
        self.fake = Faker("pt_BR")
        self.fake.seed_instance(seed)
        self.stores = {store["loja_id"]: store for store in read_config_json("lojas_config.json")}
        self.products = read_config_json("produtos_config.json")
        self.customers: list[dict[str, Any]] = []

    def generate_shift(self, loja_id: int, sale_date: date, turno: str, quantity: int) -> ShiftFile:
        """Gera um arquivo válido para uma loja, data e turno operacional."""
        if turno not in SHIFT_HOURS:
            raise ValueError(f"Turno inválido: {turno}")
        if loja_id not in self.stores:
            raise ValueError(f"Loja inválida: {loja_id}")
        if quantity < 0:
            raise ValueError("Quantidade de vendas deve ser não negativa")
        store = self.stores[loja_id]
        first_hour, last_hour = SHIFT_HOURS[turno]
        sales: list[dict[str, Any]] = []
        for index in range(1, quantity + 1):
            when = datetime.combine(
                sale_date,
                time(
                    self.rng.randint(first_hour, last_hour),
                    self.rng.randint(0, 59),
                    self.rng.randint(0, 59),
                ),
            )
            generated = build_sale(
                SHIFT_SEQUENCE_OFFSET[turno] + index,
                store,
                choose_product(self.products, self.rng),
                build_customer(
                    self.customers,
                    self.fake,
                    self.rng,
                    int(sale_date.strftime("%Y%m%d")) * 1_000_000
                    + loja_id * 10_000
                    + SHIFT_SEQUENCE_OFFSET[turno],
                ),
                when,
                STORE_PROFILES[loja_id],
                self.rng,
            )
            sales.append(VendaEntrada.model_validate(generated).model_dump(mode="json"))
        return ShiftFile(
            schema_version="1.0",
            origem="sistema-pdv",
            loja_id=loja_id,
            loja_nome=store["loja_nome"],
            cidade=store["cidade"],
            estado=store["estado"],
            turno=turno,
            data_geracao=datetime.combine(sale_date, time(22)).isoformat(),
            pipeline_id=str(uuid4()),
            vendas=sales,
        )
