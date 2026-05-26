"""Extração de Raw para Bronze com validação de contrato e quarentena."""

from __future__ import annotations

import argparse
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd
from pydantic import ValidationError

from config.settings import get_settings
from scripts.data_quality import ArquivoVendasEntrada
from scripts.logger_config import get_pipeline_logger, log_metrics
from scripts.utils import (
    atomic_write_dataframe,
    date_partition_path,
    load_json,
    raw_store_partition,
    utc_timestamp,
)


@dataclass
class ExtractionResult:
    """Resultado de extração retornado às camadas de orquestração."""

    total_arquivos: int
    total_registros: int
    erros: list[str] = field(default_factory=list)
    caminho_bronze: Path | None = None
    registros_por_loja: dict[int, int] = field(default_factory=dict)


def flatten_file(file_path: Path, payload: ArquivoVendasEntrada) -> list[dict[str, Any]]:
    """Achata metadados válidos do envelope em cada registro de venda do PDV."""
    metadata = {
        "cidade": payload.cidade,
        "estado": payload.estado,
        "turno_origem": payload.turno.value,
        "pipeline_id": str(payload.pipeline_id),
        "arquivo_checksum": payload.checksum,
        "arquivo_origem": str(file_path),
        "timestamp_ingestao": utc_timestamp(),
        "pipeline_versao": get_settings().pipeline_version,
    }
    return [sale.model_dump(mode="json") | metadata for sale in payload.vendas]


def quarantine_file_error(data_referencia: str, path: Path, error: str) -> None:
    """Adiciona à quarentena um arquivo Raw ilegível ou inválido pelo contrato."""
    destination = (
        get_settings().quarantine_path
        / f"arquivos_invalidos_{data_referencia.replace('-', '')}.csv"
    )
    row = pd.DataFrame(
        [{"data_referencia": data_referencia, "arquivo_origem": str(path), "erro": error}]
    )
    if destination.exists():
        existing = pd.read_csv(destination)
        row = pd.concat([existing, row], ignore_index=True).drop_duplicates()
    atomic_write_dataframe(row, destination, "csv")


def extract_file(file_path: Path, data_referencia: str) -> list[dict[str, Any]]:
    """Lê e valida um arquivo JSON Raw, encaminhando falhas à quarentena."""
    try:
        payload = ArquivoVendasEntrada.model_validate(load_json(file_path))
    except (ValueError, ValidationError) as exc:
        quarantine_file_error(data_referencia, file_path, str(exc))
        raise ValueError(f"Arquivo rejeitado {file_path.name}: {exc}") from exc
    return flatten_file(file_path, payload)


def extrair_raw_para_bronze(data_referencia: str, lojas_ids: list[int]) -> ExtractionResult:
    """Extrai uma partição Raw diária, preservando o isolamento de falhas por loja."""
    started = time.perf_counter()
    logger = get_pipeline_logger("extrair_bronze", data_referencia)
    records: list[dict[str, Any]] = []
    errors: list[str] = []
    counts: dict[int, int] = {}
    files_count = 0
    for loja_id in lojas_ids:
        store_records: list[dict[str, Any]] = []
        partition = raw_store_partition(loja_id, data_referencia)
        for file_path in sorted(partition.glob("*.json")):
            files_count += 1
            try:
                store_records.extend(extract_file(file_path, data_referencia))
            except ValueError as exc:
                errors.append(str(exc))
        counts[loja_id] = len(store_records)
        records.extend(store_records)
    destination = (
        date_partition_path(get_settings().bronze_path / "vendas", data_referencia)
        / f"vendas_bronze_{data_referencia.replace('-', '')}.csv"
    )
    frame = pd.DataFrame(records)
    atomic_write_dataframe(frame, destination, "csv")
    result = ExtractionResult(files_count, len(frame), errors, destination, counts)
    log_metrics(
        logger,
        "Extração Raw para Bronze concluída",
        {
            "arquivos_lidos": files_count,
            "registros_saida": len(frame),
            "arquivos_rejeitados": len(errors),
            "duracao_ms": round((time.perf_counter() - started) * 1000),
        },
    )
    return result


def main() -> None:
    """Ponto de entrada CLI para processamento de Raw para Bronze."""
    parser = argparse.ArgumentParser(description="Extrai uma data Raw para Bronze.")
    parser.add_argument("data_referencia")
    parser.add_argument("--lojas", nargs="+", type=int, default=[1, 2, 3, 4, 5])
    args = parser.parse_args()
    result = extrair_raw_para_bronze(args.data_referencia, args.lojas)
    print(f"Bronze: {result.caminho_bronze} | registros: {result.total_registros}")


if __name__ == "__main__":
    main()
