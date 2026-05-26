-- 01. Faturamento total nos últimos doze meses.
SELECT * FROM vw_faturamento_mensal ORDER BY ano DESC, mes DESC LIMIT 12;

-- 02. Ranking de lojas na competência mais recente.
SELECT * FROM vw_faturamento_por_loja
WHERE (ano, mes) = (SELECT ano, mes FROM vw_faturamento_mensal ORDER BY ano DESC, mes DESC LIMIT 1)
ORDER BY ranking;

-- 03. Top dez produtos por receita.
SELECT * FROM vw_top10_produtos ORDER BY ano DESC, mes DESC, ranking_receita LIMIT 10;

-- 04. Top dez produtos por volume.
SELECT * FROM vw_top10_produtos ORDER BY ano DESC, mes DESC, ranking_volume LIMIT 10;

-- 05. Ticket médio por loja e competência.
SELECT * FROM vw_ticket_medio_por_loja ORDER BY ano DESC, mes DESC, loja_id;

-- 06. Receita por canal.
SELECT canal_venda, SUM(receita) AS receita FROM vw_cohort_canais GROUP BY canal_venda ORDER BY receita DESC;

-- 07. Receita por forma de pagamento.
SELECT forma_pagamento, SUM(receita) AS receita FROM vw_cohort_canais GROUP BY forma_pagamento ORDER BY receita DESC;

-- 08. Taxa de cancelamento por loja.
SELECT loja_id, COUNT(*) FILTER (WHERE status = 'CANCELADA')::NUMERIC / NULLIF(COUNT(*), 0) * 100 AS cancelamento_pct
FROM fato_vendas GROUP BY loja_id ORDER BY cancelamento_pct DESC;

-- 09. Meta versus realizado.
SELECT * FROM vw_meta_vs_realizado ORDER BY ano, mes, loja_id;

-- 10. DRE por loja no mês mais recente.
SELECT * FROM fato_dre
WHERE (ano, mes) = (SELECT ano, mes FROM fato_dre ORDER BY ano DESC, mes DESC LIMIT 1)
ORDER BY loja_id;

-- 11. Margem bruta por loja e mês.
SELECT ano, mes, loja_id, SUM(margem_bruta) AS margem_bruta,
       SUM(margem_bruta) / NULLIF(SUM(valor_liquido), 0) * 100 AS margem_pct
FROM fato_vendas WHERE status = 'CONCLUIDA' GROUP BY ano, mes, loja_id ORDER BY ano, mes, loja_id;

-- 12. Evolução consolidada da margem.
SELECT ano, mes, SUM(margem_bruta) / NULLIF(SUM(valor_liquido), 0) * 100 AS margem_pct
FROM fato_vendas WHERE status = 'CONCLUIDA' GROUP BY ano, mes ORDER BY ano, mes;

-- 13. Crescimento mensal por loja.
SELECT ano, mes, loja_id, crescimento_mom FROM vw_faturamento_por_loja ORDER BY ano, mes, loja_id;

-- 14. Participação de receita por loja.
SELECT ano, mes, loja_id, market_share_pct FROM vw_faturamento_por_loja ORDER BY ano, mes, loja_id;

-- 15. Produtos com maior desconto percentual médio.
SELECT produto_id, AVG(desconto_pct) AS desconto_medio_pct
FROM fato_vendas WHERE status = 'CONCLUIDA' GROUP BY produto_id ORDER BY desconto_medio_pct DESC LIMIT 10;

-- 16. Receita por segmento de cliente.
SELECT c.segmento, SUM(v.valor_liquido) AS receita
FROM fato_vendas v JOIN dim_cliente c ON c.cliente_sk = v.cliente_sk
WHERE v.status = 'CONCLUIDA' GROUP BY c.segmento ORDER BY receita DESC;

-- 17. Desempenho por turno.
SELECT periodo, COUNT(DISTINCT id_venda) AS pedidos, SUM(valor_liquido) AS receita
FROM fato_vendas WHERE status = 'CONCLUIDA' GROUP BY periodo ORDER BY receita DESC;

-- 18. Receita contra o mesmo mês do ano anterior.
WITH mensal AS (
    SELECT ano, mes, SUM(valor_liquido) AS receita FROM fato_vendas
    WHERE status = 'CONCLUIDA' GROUP BY ano, mes
)
SELECT atual.ano, atual.mes, atual.receita, anterior.receita AS receita_ano_anterior,
       (atual.receita - anterior.receita) / NULLIF(anterior.receita, 0) * 100 AS crescimento_yoy_pct
FROM mensal atual LEFT JOIN mensal anterior ON anterior.ano = atual.ano - 1 AND anterior.mes = atual.mes;

-- 19. Previsão de receita mensal.
SELECT ano, mes, loja_id, forecast_mes, run_rate_anual FROM vw_indicadores_fpa ORDER BY ano DESC, mes DESC, loja_id;

-- 20. Auditoria de qualidade por data.
SELECT data_referencia, SUM(registros_lidos) AS lidos, SUM(registros_invalidos) AS invalidos,
       SUM(registros_validos)::NUMERIC / NULLIF(SUM(registros_lidos), 0) * 100 AS aprovacao_pct
FROM pipeline_audit_log GROUP BY data_referencia ORDER BY data_referencia DESC;
