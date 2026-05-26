"""Testes unitários do controle de qualidade por registro."""

from __future__ import annotations

from scripts.data_quality import evaluate_rules, quality_score


def valid_record() -> dict[str, object]:
    """Monta uma linha de entrada mínima para as regras de qualidade."""
    return {
        "id_venda": "VND-2026-001-0001",
        "loja_id": 1,
        "quantidade": 1,
        "valor_unitario": 3500.0,
        "custo_unitario": 2100.0,
        "desconto_valor": 175.0,
        "data_venda": "2026-01-08T10:00:00",
        "status": "CONCLUIDA",
        "produto_id": 501,
        "cliente_id": 1001,
    }


class TestQualidade:
    """Cobre regras impeditivas e consultivas de qualidade de dados."""

    def test_rejeita_quantidade_zero(self) -> None:
        failures = evaluate_rules(valid_record() | {"quantidade": 0})
        assert "quantidade_positiva" in {failure.name for failure in failures}

    def test_rejeita_valor_unitario_zero(self) -> None:
        failures = evaluate_rules(valid_record() | {"valor_unitario": 0})
        assert "valor_unitario_positivo" in {failure.name for failure in failures}

    def test_rejeita_status_invalido(self) -> None:
        failures = evaluate_rules(valid_record() | {"status": "DEVOLVIDA"})
        assert "status_permitido" in {failure.name for failure in failures}

    def test_aceita_registro_concluido_valido(self) -> None:
        assert evaluate_rules(valid_record()) == []

    def test_score_qualidade_calculado(self) -> None:
        assert quality_score(100, 3) == 97.0
