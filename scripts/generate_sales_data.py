"""Gera dados JSON Raw determinísticos e realistas de vendas do PDV."""

from __future__ import annotations

import argparse
import calendar
import random
import time
from collections import defaultdict
from datetime import date, datetime, timedelta
from datetime import time as dt_time
from decimal import ROUND_HALF_UP, Decimal
from typing import Any
from uuid import uuid4

from faker import Faker

from scripts.data_quality import VendaEntrada
from scripts.logger_config import get_pipeline_logger, log_metrics
from scripts.utils import atomic_write_json, raw_store_partition, read_config_json, sha256_json

STORE_PROFILES = {
    1: {"min_vendas_dia": 25, "max_vendas_dia": 60, "ticket_medio": 850, "cancel": 0.035},
    2: {"min_vendas_dia": 10, "max_vendas_dia": 30, "ticket_medio": 620, "cancel": 0.075},
    3: {"min_vendas_dia": 20, "max_vendas_dia": 45, "ticket_medio": 780, "cancel": 0.045},
    4: {"min_vendas_dia": 30, "max_vendas_dia": 70, "ticket_medio": 920, "cancel": 0.030},
    5: {"min_vendas_dia": 15, "max_vendas_dia": 35, "ticket_medio": 710, "cancel": 0.060},
}
SHIFT_HOURS = {"MANHA": (8, 11), "TARDE": (12, 17), "NOITE": (18, 21)}
PAYMENT_OPTIONS = ["Cartao de Credito", "Cartao de Debito", "PIX", "Boleto"]
SALES_CHANNELS = ["Loja Física", "Retirada Loja", "Televendas"]
SEGMENTS = ["VAREJO", "VAREJO", "VAREJO", "CORPORATIVO", "VIP"]


def money(value: float) -> float:
    """Arredonda valores monetários para precisão de centavos."""
    return float(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def choose_product(products: list[dict[str, Any]], rng: random.Random) -> dict[str, Any]:
    """Seleciona produtos segundo distribuição aproximadamente ponderada por Pareto."""
    popular = products[:3]
    return rng.choice(popular if rng.random() < 0.80 else products[3:])


def sale_status(profile: dict[str, float | int], rng: random.Random) -> tuple[str, str | None]:
    """Gera status transacional e motivo de cancelamento específicos da loja."""
    chance = rng.random()
    if chance < float(profile["cancel"]):
        return "CANCELADA", rng.choice(["Arrependimento", "Pagamento recusado", "Produto avariado"])
    if chance < float(profile["cancel"]) + 0.035:
        return "PENDENTE", None
    return "CONCLUIDA", None


def build_customer(
    customers: list[dict[str, Any]], fake: Faker, rng: random.Random, customer_id_base: int = 1000
) -> dict[str, Any]:
    """Reutiliza quarenta por cento dos clientes após existir uma base conhecida."""
    if customers and rng.random() < 0.40:
        return rng.choice(customers)
    customer = {
        "cliente_id": customer_id_base + len(customers) + 1,
        "cliente_nome": fake.name(),
        "cliente_segmento": rng.choice(SEGMENTS),
    }
    customers.append(customer)
    return customer


def build_sale(
    sequence: int,
    store: dict[str, Any],
    product: dict[str, Any],
    customer: dict[str, Any],
    when: datetime,
    profile: dict[str, float | int],
    rng: random.Random,
) -> dict[str, Any]:
    """Cria um registro de venda de item único conforme o contrato de entrada."""
    quantity = rng.choices([1, 2, 3], weights=[86, 11, 3], k=1)[0]
    price_factor = rng.uniform(0.97, 1.04)
    unit_value = money(product["preco_base"] * price_factor)
    unit_cost = money(product["custo_base"])
    discount_pct = rng.choices([0, 5, 10, 15, 20, 25], [12, 56, 20, 7, 4, 1], k=1)[0]
    gross = quantity * unit_value
    discount_value = money(gross * discount_pct / 100)
    status, cancellation_reason = sale_status(profile, rng)
    return {
        "id_venda": f"VND-{when:%Y%m%d}-{store['loja_id']:03d}-{sequence:07d}",
        "loja_id": store["loja_id"],
        "loja_nome": store["loja_nome"],
        **customer,
        "produto_id": product["produto_id"],
        "produto_nome": product["produto_nome"],
        "categoria": product["categoria"],
        "subcategoria": product["subcategoria"],
        "quantidade": quantity,
        "valor_unitario": unit_value,
        "custo_unitario": unit_cost,
        "desconto_percentual": float(discount_pct),
        "desconto_valor": discount_value,
        "canal_venda": rng.choices(SALES_CHANNELS, [82, 12, 6], k=1)[0],
        "forma_pagamento": rng.choices(PAYMENT_OPTIONS, [48, 20, 29, 3], k=1)[0],
        "parcelas": rng.choice([1, 1, 1, 2, 3, 6, 10]),
        "vendedor_id": f"VND-{store['loja_id']:03d}-{rng.randint(1, 15):02d}",
        "data_venda": when.isoformat(timespec="seconds"),
        "status": status,
        "motivo_cancelamento": cancellation_reason,
    }


def generate_raw_data(
    start_date: date, days: int = 90, seed: int = 20260524, overwrite: bool = False
) -> dict[str, int | float]:
    """Preenche partições JSON Raw para todas as lojas e turnos."""
    started = time.perf_counter()
    rng = random.Random(seed)
    fake = Faker("pt_BR")
    fake.seed_instance(seed)
    stores = read_config_json("lojas_config.json")
    products = read_config_json("produtos_config.json")
    customers: list[dict[str, Any]] = []
    customer_id_base = int(start_date.strftime("%Y%m%d")) * 10000
    sequence = 0
    files = 0
    total_sales = 0
    for offset in range(days):
        sale_date = start_date + timedelta(days=offset)
        for store in stores:
            profile = STORE_PROFILES[store["loja_id"]]
            day_volume = rng.randint(int(profile["min_vendas_dia"]), int(profile["max_vendas_dia"]))
            if sale_date.weekday() >= 5:
                day_volume = round(day_volume * 1.30)
            assigned: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
            for _ in range(day_volume):
                sequence += 1
                shift = rng.choices(list(SHIFT_HOURS), weights=[26, 44, 30], k=1)[0]
                first_hour, last_hour = SHIFT_HOURS[shift]
                when = datetime.combine(
                    sale_date,
                    dt_time(
                        hour=rng.randint(first_hour, last_hour),
                        minute=rng.randint(0, 59),
                        second=rng.randint(0, 59),
                    ),
                )
                product = choose_product(products, rng)
                customer = build_customer(customers, fake, rng, customer_id_base)
                assigned[shift].append(
                    build_sale(sequence, store, product, customer, when, profile, rng)
                )
                total_sales += 1
            for shift in SHIFT_HOURS:
                sales = assigned[shift]
                canonical_sales = [
                    VendaEntrada.model_validate(sale).model_dump(mode="json") for sale in sales
                ]
                payload = {
                    "schema_version": "1.0",
                    "origem": "sistema-pdv",
                    "loja_id": store["loja_id"],
                    "loja_nome": store["loja_nome"],
                    "cidade": store["cidade"],
                    "estado": store["estado"],
                    "turno": shift,
                    "data_geracao": datetime.combine(sale_date, dt_time(22, 0)).isoformat(),
                    "pipeline_id": str(uuid4()),
                    "quantidade_registros": len(sales),
                    "checksum": sha256_json(canonical_sales),
                    "vendas": sales,
                }
                partition = raw_store_partition(store["loja_id"], sale_date.isoformat())
                filename = f"vendas_{store['loja_id']}_{sale_date:%Y%m%d}_{shift.lower()}.json"
                destination = partition / filename
                if destination.exists() and not overwrite:
                    raise FileExistsError(
                        f"Arquivo Raw já existe e não será sobrescrito: {destination}. "
                        "Use --overwrite somente para uma correção controlada."
                    )
                atomic_write_json(destination, payload)
                files += 1
    metrics: dict[str, int | float] = {
        "lojas_processadas": len(stores),
        "dias_cobertos": days,
        "total_vendas": total_sales,
        "arquivos_json": files,
        "duracao_segundos": round(time.perf_counter() - started, 2),
    }
    log_metrics(get_pipeline_logger("generate_sales_data"), "Geração Raw concluída", metrics)
    return metrics


def parse_month(value: str) -> tuple[date, int]:
    """Converte ``YYYY-MM`` no primeiro dia e na duração do mês."""
    try:
        year, month = (int(part) for part in value.split("-", maxsplit=1))
        return date(year, month, 1), calendar.monthrange(year, month)[1]
    except (ValueError, TypeError) as exc:
        raise argparse.ArgumentTypeError("Mês inválido. Use YYYY-MM, por exemplo 2026-04.") from exc


def main() -> None:
    """Ponto de entrada CLI para geração de dados."""
    parser = argparse.ArgumentParser(description="Gera arquivos JSON de venda na camada Raw.")
    parser.add_argument("--start-date", type=date.fromisoformat, default=date(2026, 1, 1))
    parser.add_argument("--days", type=int, default=90)
    parser.add_argument("--month", help="Gera um mês calendário completo no formato YYYY-MM.")
    parser.add_argument("--seed", type=int, default=20260524)
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Substitui partições Raw existentes; use somente em correção controlada.",
    )
    args = parser.parse_args()
    start_date, days = parse_month(args.month) if args.month else (args.start_date, args.days)
    metrics = generate_raw_data(start_date, days, args.seed, args.overwrite)
    print(
        "Geração concluída:\n"
        f"Lojas processadas: {metrics['lojas_processadas']}/5\n"
        f"Total de vendas geradas: {metrics['total_vendas']}\n"
        f"Dias cobertos: {metrics['dias_cobertos']}\n"
        f"Arquivos JSON criados: {metrics['arquivos_json']}\n"
        f"Tempo de execução: {metrics['duracao_segundos']}s"
    )


if __name__ == "__main__":
    main()
