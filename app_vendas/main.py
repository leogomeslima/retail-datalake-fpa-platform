"""Simulador PDV em linha de comando que grava um arquivo Raw de turno."""

from __future__ import annotations

import argparse
from datetime import date

from app_vendas.datalake_service import DataLakeService
from app_vendas.venda_service import VendaService


def main() -> None:
    """Interpreta parâmetros do PDV, gera transações e persiste o JSON Raw."""
    parser = argparse.ArgumentParser(description="Simulador PDV RetailCo por turno.")
    parser.add_argument("--loja-id", required=True, type=int)
    parser.add_argument("--data", required=True, type=date.fromisoformat)
    parser.add_argument("--turno", required=True, choices=["MANHA", "TARDE", "NOITE"])
    parser.add_argument("--quantidade", required=True, type=int)
    parser.add_argument("--seed", default=20260524, type=int)
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Substitui a partição Raw existente para uma correção controlada.",
    )
    args = parser.parse_args()
    file = VendaService(args.seed).generate_shift(
        args.loja_id, args.data, args.turno, args.quantidade
    )
    destination = DataLakeService().save_shift(file, args.data, args.overwrite)
    print(f"Arquivo Raw emitido: {destination} | vendas: {len(file.vendas)}")


if __name__ == "__main__":
    main()
