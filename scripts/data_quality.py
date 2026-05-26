"""Contratos de entrada e regras de qualidade por registro para dados de vendas."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any
from uuid import UUID

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from scripts.utils import read_config_json, sha256_json


class StatusVenda(StrEnum):
    """Status permitidos para vendas do PDV."""

    CONCLUIDA = "CONCLUIDA"
    CANCELADA = "CANCELADA"
    PENDENTE = "PENDENTE"


class Turno(StrEnum):
    """Turnos operacionais emitidos pelas lojas."""

    MANHA = "MANHA"
    TARDE = "TARDE"
    NOITE = "NOITE"


class VendaEntrada(BaseModel):
    """Venda validada de item único emitida por um terminal PDV."""

    model_config = ConfigDict(str_strip_whitespace=True)

    id_venda: str = Field(min_length=5, max_length=50)
    loja_id: int = Field(ge=1, le=5)
    loja_nome: str = Field(min_length=3)
    cliente_id: int = Field(gt=0)
    cliente_nome: str = Field(min_length=3)
    cliente_segmento: str = Field(pattern=r"^(VAREJO|CORPORATIVO|VIP)$")
    produto_id: int = Field(gt=0)
    produto_nome: str = Field(min_length=2)
    categoria: str = Field(min_length=2)
    subcategoria: str = Field(min_length=2)
    quantidade: int = Field(gt=0)
    valor_unitario: Decimal = Field(gt=0)
    custo_unitario: Decimal = Field(gt=0)
    desconto_percentual: Decimal = Field(ge=0, le=25)
    desconto_valor: Decimal = Field(ge=0)
    canal_venda: str = Field(min_length=2)
    forma_pagamento: str = Field(min_length=2)
    parcelas: int = Field(ge=1, le=24)
    vendedor_id: str = Field(min_length=3)
    data_venda: datetime
    status: StatusVenda
    motivo_cancelamento: str | None = None

    @model_validator(mode="after")
    def validate_business_rules(self) -> VendaEntrada:
        """Garante coerência entre status e campos financeiros."""
        bruto = self.valor_unitario * self.quantidade
        if self.desconto_valor > bruto * Decimal("0.25") + Decimal("0.01"):
            raise ValueError("desconto_valor excede o limite contratual de 25 por cento")
        if self.status == StatusVenda.CANCELADA and not self.motivo_cancelamento:
            raise ValueError("venda cancelada requer motivo_cancelamento")
        if self.status != StatusVenda.CANCELADA and self.motivo_cancelamento:
            raise ValueError("motivo_cancelamento somente é permitido para venda cancelada")
        return self


class ArquivoVendasEntrada(BaseModel):
    """Envelope Raw validado contendo vendas de um turno de loja."""

    model_config = ConfigDict(str_strip_whitespace=True)

    schema_version: str = Field(pattern=r"^1\.0$")
    origem: str = Field(pattern=r"^sistema-pdv$")
    loja_id: int = Field(ge=1, le=5)
    loja_nome: str = Field(min_length=3)
    cidade: str = Field(min_length=2)
    estado: str = Field(min_length=2, max_length=2)
    turno: Turno
    data_geracao: datetime
    pipeline_id: UUID
    quantidade_registros: int = Field(ge=0)
    checksum: str = Field(min_length=64, max_length=64)
    vendas: list[VendaEntrada]

    @field_validator("estado")
    @classmethod
    def uppercase_state(cls, value: str) -> str:
        """Normaliza a sigla do estado antes do processamento posterior."""
        return value.upper()

    @model_validator(mode="after")
    def validate_envelope_integrity(self) -> ArquivoVendasEntrada:
        """Verifica contagem, pertencimento à loja e checksum da carga."""
        if self.quantidade_registros != len(self.vendas):
            raise ValueError("quantidade_registros diverge do array vendas")
        if any(venda.loja_id != self.loja_id for venda in self.vendas):
            raise ValueError("arquivo contém vendas de outra loja")
        sale_payload = [sale.model_dump(mode="json") for sale in self.vendas]
        if sha256_json(sale_payload) != self.checksum:
            raise ValueError("checksum do array vendas inválido")
        return self


@dataclass(frozen=True)
class QualityRule:
    """Descrição de uma regra observável de qualidade de dados."""

    name: str
    severity: str
    description: str


QUALITY_RULES = [
    QualityRule("id_venda_nao_nulo", "CRITICA", "id_venda não pode ser nulo"),
    QualityRule("loja_id_valido", "CRITICA", "loja_id deve estar entre 1 e 5"),
    QualityRule("quantidade_positiva", "CRITICA", "quantidade deve ser positiva"),
    QualityRule("valor_unitario_positivo", "CRITICA", "valor unitário deve ser positivo"),
    QualityRule("data_venda_valida", "CRITICA", "data_venda deve ser timestamp válido"),
    QualityRule("status_permitido", "CRITICA", "status deve pertencer ao contrato"),
    QualityRule("desconto_nao_negativo", "ERRO", "desconto não pode ser negativo"),
    QualityRule("desconto_razoavel", "AVISO", "desconto deve ser no máximo 30 por cento"),
    QualityRule("produto_id_valido", "AVISO", "produto deve existir no catálogo"),
    QualityRule("cliente_id_positivo", "AVISO", "cliente deve possuir identificador positivo"),
    QualityRule("custo_menor_que_preco", "AVISO", "custo unitário deve ser menor que preço"),
]


def evaluate_rules(record: dict[str, Any]) -> list[QualityRule]:
    """Retorna regras de qualidade violadas por um registro Bronze achatado."""
    product_ids = {product["produto_id"] for product in read_config_json("produtos_config.json")}
    failures: list[QualityRule] = []
    bruto = float(record.get("quantidade", 0)) * float(record.get("valor_unitario", 0))
    checks = {
        "id_venda_nao_nulo": bool(record.get("id_venda")) and not pd.isna(record.get("id_venda")),
        "loja_id_valido": record.get("loja_id") in range(1, 6),
        "quantidade_positiva": float(record.get("quantidade", 0)) > 0,
        "valor_unitario_positivo": float(record.get("valor_unitario", 0)) > 0,
        "data_venda_valida": not pd.isna(pd.to_datetime(record.get("data_venda"), errors="coerce")),
        "status_permitido": record.get("status") in {status.value for status in StatusVenda},
        "desconto_nao_negativo": float(record.get("desconto_valor", -1)) >= 0,
        "desconto_razoavel": bruto > 0 and float(record.get("desconto_valor", 0)) <= bruto * 0.30,
        "produto_id_valido": record.get("produto_id") in product_ids,
        "cliente_id_positivo": float(record.get("cliente_id", 0)) > 0,
        "custo_menor_que_preco": float(record.get("custo_unitario", 0))
        < float(record.get("valor_unitario", 0)),
    }
    for rule in QUALITY_RULES:
        if not checks[rule.name]:
            failures.append(rule)
    return failures


def quality_score(total_records: int, failed_records: int) -> float:
    """Calcula o percentual de aprovação de uma execução de validação."""
    if total_records == 0:
        return 0.0
    return round(((total_records - failed_records) / total_records) * 100, 2)
