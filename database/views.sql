-- Receita consolidada da rede por competência.
CREATE OR REPLACE VIEW vw_faturamento_mensal AS
SELECT
    ano,
    mes,
    SUM(valor_bruto) AS receita_bruta,
    SUM(valor_liquido) AS receita_liquida,
    SUM(desconto_valor) AS desconto_total,
    COUNT(DISTINCT id_venda) AS total_pedidos,
    SUM(valor_liquido) / NULLIF(COUNT(DISTINCT id_venda), 0) AS ticket_medio
FROM fato_vendas
WHERE status = 'CONCLUIDA'
GROUP BY ano, mes;

-- Receita, participação e tendência mensal de cada loja.
CREATE OR REPLACE VIEW vw_faturamento_por_loja AS
WITH mensal AS (
    SELECT ano, mes, loja_id, SUM(valor_liquido) AS faturamento
    FROM fato_vendas WHERE status = 'CONCLUIDA'
    GROUP BY ano, mes, loja_id
), calculado AS (
    SELECT
        mensal.*,
        SUM(faturamento) OVER (PARTITION BY ano, mes) AS total_rede,
        LAG(faturamento) OVER (PARTITION BY loja_id ORDER BY ano, mes) AS faturamento_anterior
    FROM mensal
)
SELECT
    c.ano, c.mes, c.loja_id, l.loja_nome, c.faturamento,
    RANK() OVER (PARTITION BY c.ano, c.mes ORDER BY c.faturamento DESC) AS ranking,
    ROUND(c.faturamento / NULLIF(c.total_rede, 0) * 100, 2) AS market_share_pct,
    ROUND((c.faturamento - c.faturamento_anterior) / NULLIF(c.faturamento_anterior, 0) * 100, 2)
        AS crescimento_mom
FROM calculado c
JOIN dim_loja l ON l.loja_id = c.loja_id;

-- Histórico de ticket médio e mudança frente ao mês anterior.
CREATE OR REPLACE VIEW vw_ticket_medio_por_loja AS
WITH ticket AS (
    SELECT
        ano, mes, loja_id,
        SUM(valor_liquido) / NULLIF(COUNT(DISTINCT id_venda), 0) AS ticket_medio
    FROM fato_vendas WHERE status = 'CONCLUIDA'
    GROUP BY ano, mes, loja_id
), anterior AS (
    SELECT
        ticket.*,
        LAG(ticket_medio) OVER (PARTITION BY loja_id ORDER BY ano, mes) AS ticket_anterior
    FROM ticket
)
SELECT
    anterior.*, l.loja_nome,
    ROUND((ticket_medio - ticket_anterior) / NULLIF(ticket_anterior, 0) * 100, 2) AS variacao_pct
FROM anterior
JOIN dim_loja l ON l.loja_id = anterior.loja_id;

-- Ranking por receita, margem realizada e percentual da meta.
CREATE OR REPLACE VIEW vw_ranking_lojas AS
WITH realizado AS (
    SELECT
        ano, mes, loja_id, SUM(valor_liquido) AS receita,
        SUM(margem_bruta) / NULLIF(SUM(valor_liquido), 0) * 100 AS margem_pct
    FROM fato_vendas WHERE status = 'CONCLUIDA'
    GROUP BY ano, mes, loja_id
)
SELECT
    r.ano, r.mes, r.loja_id, l.loja_nome, r.receita, ROUND(r.margem_pct, 2) AS margem_pct,
    ROUND(r.receita / NULLIF(o.receita_orcada, 0) * 100, 2) AS meta_atingida_pct,
    RANK() OVER (PARTITION BY r.ano, r.mes ORDER BY r.receita DESC) AS ranking_receita,
    RANK() OVER (PARTITION BY r.ano, r.mes ORDER BY r.margem_pct DESC) AS ranking_margem
FROM realizado r
JOIN dim_loja l ON l.loja_id = r.loja_id
JOIN fato_orcamento o ON o.loja_id = r.loja_id AND o.ano = r.ano AND o.mes = r.mes;

-- Comparação entre orçamento e vendas concluídas.
CREATE OR REPLACE VIEW vw_meta_vs_realizado AS
WITH realizado AS (
    SELECT ano, mes, loja_id, SUM(valor_liquido) AS receita_realizada
    FROM fato_vendas WHERE status = 'CONCLUIDA'
    GROUP BY ano, mes, loja_id
)
SELECT
    o.ano, o.mes, o.loja_id, l.loja_nome, o.receita_orcada,
    COALESCE(r.receita_realizada, 0) AS receita_realizada,
    COALESCE(r.receita_realizada, 0) - o.receita_orcada AS variacao_absoluta,
    ROUND((COALESCE(r.receita_realizada, 0) - o.receita_orcada) /
        NULLIF(o.receita_orcada, 0) * 100, 2) AS variacao_pct,
    CASE
        WHEN COALESCE(r.receita_realizada, 0) / NULLIF(o.receita_orcada, 0) >= 0.95 THEN 'VERDE'
        WHEN COALESCE(r.receita_realizada, 0) / NULLIF(o.receita_orcada, 0) >= 0.80 THEN 'AMARELO'
        ELSE 'VERMELHO'
    END AS status_semaforo
FROM fato_orcamento o
JOIN dim_loja l ON l.loja_id = o.loja_id
LEFT JOIN realizado r ON r.loja_id = o.loja_id AND r.ano = o.ano AND r.mes = o.mes;

-- DRE por loja acrescida de linha consolidada mensal.
CREATE OR REPLACE VIEW vw_dre_consolidada AS
SELECT
    ano, mes, loja_id::VARCHAR AS unidade, receita_bruta, descontos, impostos,
    receita_liquida, cmv, lucro_bruto, margem_bruta_pct, despesas_variaveis,
    despesas_fixas, ebitda, margem_ebitda_pct, depreciacao, ebit,
    despesas_financeiras, resultado_antes_ir, margem_liquida_pct
FROM fato_dre
UNION ALL
SELECT
    ano, mes, 'REDE' AS unidade, SUM(receita_bruta), SUM(descontos), SUM(impostos),
    SUM(receita_liquida), SUM(cmv), SUM(lucro_bruto),
    SUM(lucro_bruto) / NULLIF(SUM(receita_liquida), 0) * 100,
    SUM(despesas_variaveis), SUM(despesas_fixas), SUM(ebitda),
    SUM(ebitda) / NULLIF(SUM(receita_liquida), 0) * 100,
    SUM(depreciacao), SUM(ebit), SUM(despesas_financeiras), SUM(resultado_antes_ir),
    SUM(resultado_antes_ir) / NULLIF(SUM(receita_liquida), 0) * 100
FROM fato_dre
GROUP BY ano, mes;

-- Previsão e ritmo anual a partir dos dias observados em cada competência.
CREATE OR REPLACE VIEW vw_indicadores_fpa AS
WITH actual AS (
    SELECT
        ano, mes, loja_id, SUM(valor_liquido) AS realizado,
        COUNT(DISTINCT data_venda::DATE) AS dias_observados
    FROM fato_vendas WHERE status = 'CONCLUIDA'
    GROUP BY ano, mes, loja_id
)
SELECT
    a.ano, a.mes, a.loja_id, a.realizado, o.receita_orcada,
    ROUND(a.realizado / NULLIF(o.receita_orcada, 0) * 100, 2) AS meta_atingida_pct,
    ROUND(a.realizado / NULLIF(a.dias_observados, 0) *
        EXTRACT(DAY FROM (MAKE_DATE(a.ano, a.mes, 1) + INTERVAL '1 month - 1 day')), 2)
        AS forecast_mes,
    ROUND(a.realizado / NULLIF(a.dias_observados, 0) *
        EXTRACT(DAY FROM (MAKE_DATE(a.ano, a.mes, 1) + INTERVAL '1 month - 1 day')) * 12, 2)
        AS run_rate_anual
FROM actual a
JOIN fato_orcamento o ON o.loja_id = a.loja_id AND o.ano = a.ano AND o.mes = a.mes;

-- Produtos líderes em receita e volume.
CREATE OR REPLACE VIEW vw_top10_produtos AS
WITH produtos AS (
    SELECT
        v.ano, v.mes, p.produto_id, p.produto_nome, p.categoria,
        SUM(v.valor_liquido) AS receita, SUM(v.quantidade) AS volume
    FROM fato_vendas v
    JOIN dim_produto p ON p.produto_sk = v.produto_sk
    WHERE v.status = 'CONCLUIDA'
    GROUP BY v.ano, v.mes, p.produto_id, p.produto_nome, p.categoria
), ranks AS (
    SELECT
        produtos.*,
        RANK() OVER (PARTITION BY ano, mes ORDER BY receita DESC) AS ranking_receita,
        RANK() OVER (PARTITION BY ano, mes ORDER BY volume DESC) AS ranking_volume
    FROM produtos
)
SELECT * FROM ranks WHERE ranking_receita <= 10 OR ranking_volume <= 10;

-- Distribuição de vendas por canal e pagamento.
CREATE OR REPLACE VIEW vw_cohort_canais AS
SELECT
    ano, mes, canal_venda, forma_pagamento,
    COUNT(DISTINCT id_venda) AS pedidos,
    SUM(valor_liquido) AS receita,
    SUM(valor_liquido) / NULLIF(COUNT(DISTINCT id_venda), 0) AS ticket_medio
FROM fato_vendas
WHERE status = 'CONCLUIDA'
GROUP BY ano, mes, canal_venda, forma_pagamento;

-- Execuções e volume rejeitado do pipeline.
CREATE OR REPLACE VIEW vw_pipeline_health AS
SELECT
    data_referencia, task_id, status, COUNT(*) AS execucoes,
    SUM(registros_lidos) AS registros_lidos,
    SUM(registros_validos) AS registros_validos,
    SUM(registros_invalidos) AS registros_invalidos,
    MAX(created_at) AS ultima_execucao
FROM pipeline_audit_log
GROUP BY data_referencia, task_id, status;
