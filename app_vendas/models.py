"""Modelos da aplicação para emissão de arquivos de vendas."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from scripts.utils import sha256_json


@dataclass(frozen=True)
class SaleItem:
    """Um item vendido, correspondente ao grão do contrato de dados Raw."""

    id_venda: str
    loja_id: int
    loja_nome: str
    cliente_id: int
    cliente_nome: str
    cliente_segmento: str
    produto_id: int
    produto_nome: str
    categoria: str
    subcategoria: str
    quantidade: int
    valor_unitario: float
    custo_unitario: float
    desconto_percentual: float
    desconto_valor: float
    canal_venda: str
    forma_pagamento: str
    parcelas: int
    vendedor_id: str
    data_venda: str
    status: str
    motivo_cancelamento: str | None

    def to_dict(self) -> dict[str, Any]:
        """Converte o item imutável em conteúdo compatível com JSON."""
        return asdict(self)


@dataclass(frozen=True)
class ShiftFile:
    """Envelope enviado por uma loja após um turno operacional."""

    schema_version: str
    origem: str
    loja_id: int
    loja_nome: str
    cidade: str
    estado: str
    turno: str
    data_geracao: str
    pipeline_id: str
    vendas: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        """Monta metadados, contagem e checksum de integridade do envelope."""
        return {
            "schema_version": self.schema_version,
            "origem": self.origem,
            "loja_id": self.loja_id,
            "loja_nome": self.loja_nome,
            "cidade": self.cidade,
            "estado": self.estado,
            "turno": self.turno,
            "data_geracao": self.data_geracao,
            "pipeline_id": self.pipeline_id,
            "quantidade_registros": len(self.vendas),
            "checksum": sha256_json(self.vendas),
            "vendas": self.vendas,
        }
