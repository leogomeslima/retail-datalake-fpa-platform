"""Serviço de persistência no Data Lake Raw para a aplicação PDV."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from app_vendas.models import ShiftFile
from scripts.data_quality import ArquivoVendasEntrada
from scripts.utils import atomic_write_json, raw_store_partition


class DataLakeService:
    """Valida e grava atomicamente documentos de turno na camada Raw."""

    def save_shift(self, shift_file: ShiftFile, sale_date: date, overwrite: bool = False) -> Path:
        """Persiste uma carga Raw válida e retorna seu destino absoluto."""
        payload = shift_file.to_dict()
        ArquivoVendasEntrada.model_validate(payload)
        partition = raw_store_partition(shift_file.loja_id, sale_date.isoformat())
        destination = (
            partition
            / f"vendas_{shift_file.loja_id}_{sale_date:%Y%m%d}_{shift_file.turno.lower()}.json"
        )
        if destination.exists() and not overwrite:
            raise FileExistsError(
                f"Arquivo Raw já existe e não será sobrescrito: {destination}. "
                "Informe --overwrite somente para uma correção controlada."
            )
        atomic_write_json(destination, payload)
        return destination
