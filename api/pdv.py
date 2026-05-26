"""Endpoints da operação PDV sustentados pelo pipeline real de Raw até o DW."""

from __future__ import annotations

from collections import Counter
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app_vendas.datalake_service import DataLakeService
from app_vendas.venda_service import SHIFT_SEQUENCE_OFFSET, VendaService
from scripts.run_pipeline import execute_daily_pipeline
from scripts.utils import raw_store_partition, read_config_json

router = APIRouter(prefix="/api/pdv", tags=["PDV"])


class TurnoRequest(BaseModel):
    """Entrada utilizada por um terminal PDV ao fechar um turno de vendas."""

    loja_id: int = Field(ge=1, le=5)
    data: date
    turno: str = Field(pattern=r"^(MANHA|TARDE|NOITE)$")
    quantidade: int = Field(ge=1, le=150)
    seed: int = Field(default=20260525, ge=1)


class ProcessamentoRequest(BaseModel):
    """Data de referência solicitada para execução imediata do pipeline."""

    data: date


class FechamentoGeralRequest(BaseModel):
    """Entrada utilizada para fechar todos os turnos de uma data operacional."""

    data: date
    quantidade_por_turno: int = Field(ge=1, le=150)
    seed: int = Field(default=20260525, ge=1)


def totals(sales: list[dict[str, Any]]) -> dict[str, object]:
    """Consolida transações emitidas para retorno imediato ao terminal."""
    gross = sum(
        (Decimal(str(sale["valor_unitario"])) * int(sale["quantidade"]) for sale in sales),
        Decimal("0"),
    )
    discount = sum((Decimal(str(sale["desconto_valor"])) for sale in sales), Decimal("0"))
    statuses = Counter(str(sale["status"]) for sale in sales)
    return {
        "valor_bruto": float(gross.quantize(Decimal("0.01"))),
        "descontos": float(discount.quantize(Decimal("0.01"))),
        "valor_liquido": float((gross - discount).quantize(Decimal("0.01"))),
        "concluidas": statuses["CONCLUIDA"],
        "pendentes": statuses["PENDENTE"],
        "canceladas": statuses["CANCELADA"],
    }


def shift_destination(loja_id: int, sale_date: date, turno: str) -> Path:
    """Retorna o destino Raw imutável de um turno de loja."""
    return (
        raw_store_partition(loja_id, sale_date.isoformat())
        / f"vendas_{loja_id}_{sale_date:%Y%m%d}_{turno.lower()}.json"
    )


def process_raw_date(sale_date: date) -> dict[str, object]:
    """Executa o pipeline de Raw até o DW para uma data com arquivos de origem."""
    raw_files = [
        source
        for loja_id in range(1, 6)
        for source in raw_store_partition(loja_id, sale_date.isoformat()).glob("*.json")
    ]
    if not raw_files:
        raise HTTPException(status_code=404, detail="Nenhum fechamento Raw emitido nesta data.")
    run_id = f"pdv_api_{sale_date:%Y%m%d}_{datetime.now(UTC):%Y%m%dT%H%M%S}"
    summary = execute_daily_pipeline(sale_date.isoformat(), load_database=True, run_id=run_id)
    results = [
        summary["extracao"],
        summary["validacao"],
        summary["transformacao"],
        summary["carga_dw"],
    ]
    if not all(isinstance(item, dict) for item in results):
        raise HTTPException(status_code=500, detail="Resumo inesperado produzido pelo pipeline.")
    extraction = cast(dict[str, Any], results[0])
    validation = cast(dict[str, Any], results[1])
    transformation = cast(dict[str, Any], results[2])
    loaded = cast(dict[str, Any], results[3])
    return {
        "status": "PROCESSADO",
        "run_id": run_id,
        "data": sale_date.isoformat(),
        "arquivos_raw": len(raw_files),
        "registros_extraidos": extraction["total_registros"],
        "registros_validos": validation["registros_validos"],
        "registros_invalidos": validation["registros_invalidos"],
        "registros_silver": transformation["registros_saida"],
        "registros_cancelados": transformation["registros_cancelados"],
        "registros_inseridos": loaded["registros_inseridos"],
        "registros_atualizados": loaded["registros_atualizados"],
    }


@router.get("/config")
def pdv_config() -> dict[str, object]:
    """Retorna opções operacionais apresentadas nos terminais PDV."""
    return {
        "lojas": read_config_json("lojas_config.json"),
        "produtos": read_config_json("produtos_config.json"),
        "turnos": list(SHIFT_SEQUENCE_OFFSET),
    }


@router.post("/turnos", status_code=status.HTTP_201_CREATED)
def emit_shift(request: TurnoRequest) -> dict[str, object]:
    """Gera e persiste um documento Raw imutável de loja e turno."""
    shift_file = VendaService(request.seed).generate_shift(
        request.loja_id, request.data, request.turno, request.quantidade
    )
    try:
        destination = DataLakeService().save_shift(shift_file, request.data)
    except FileExistsError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {
        "status": "RAW_EMITIDO",
        "arquivo": str(destination),
        "pipeline_id": shift_file.pipeline_id,
        "loja_id": shift_file.loja_id,
        "loja_nome": shift_file.loja_nome,
        "turno": shift_file.turno,
        "data": request.data.isoformat(),
        "quantidade": len(shift_file.vendas),
        "totais": totals(shift_file.vendas),
        "vendas": shift_file.vendas,
    }


@router.post("/fechamentos-gerais", status_code=status.HTTP_201_CREATED)
def emit_all_shifts(request: FechamentoGeralRequest) -> dict[str, object]:
    """Gera documentos Raw de todas as lojas e turnos para um dia completo."""
    stores = read_config_json("lojas_config.json")
    turns = list(SHIFT_SEQUENCE_OFFSET)
    conflicts = [
        str(shift_destination(store["loja_id"], request.data, turno))
        for store in stores
        for turno in turns
        if shift_destination(store["loja_id"], request.data, turno).exists()
    ]
    if conflicts:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Fechamento geral não emitido: {len(conflicts)} arquivo(s) Raw já "
                "existem para a data. Utilize uma data sem fechamentos anteriores."
            ),
        )

    service = VendaService(request.seed)
    storage = DataLakeService()
    all_sales: list[dict[str, Any]] = []
    emissions: list[dict[str, object]] = []
    for store in stores:
        for turno in turns:
            shift_file = service.generate_shift(
                store["loja_id"],
                request.data,
                turno,
                request.quantidade_por_turno,
            )
            destination = storage.save_shift(shift_file, request.data)
            all_sales.extend(shift_file.vendas)
            shift_totals = totals(shift_file.vendas)
            emissions.append(
                {
                    "loja_id": store["loja_id"],
                    "loja_nome": store["loja_nome"],
                    "turno": turno,
                    "arquivo": str(destination),
                    "quantidade": len(shift_file.vendas),
                    "valor_liquido": shift_totals["valor_liquido"],
                }
            )
    return {
        "status": "RAW_DIA_EMITIDO",
        "data": request.data.isoformat(),
        "lojas": len(stores),
        "turnos_por_loja": len(turns),
        "arquivos_raw": len(emissions),
        "quantidade": len(all_sales),
        "totais": totals(all_sales),
        "emissoes": emissions,
        "processamento": process_raw_date(request.data),
    }


@router.post("/processamentos")
def process_date(request: ProcessamentoRequest) -> dict[str, object]:
    """Executa imediatamente o pipeline existente para uma data emitida pelo PDV."""
    return process_raw_date(request.data)
