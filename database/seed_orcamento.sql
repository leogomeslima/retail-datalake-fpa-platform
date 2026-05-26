INSERT INTO fato_orcamento (
    loja_sk, loja_id, ano, mes, receita_orcada, margem_bruta_orcada,
    despesas_fixas_orcadas, despesas_var_orcadas, resultado_orcado
)
SELECT
    loja_sk,
    loja_id,
    2026,
    mes,
    meta_mensal,
    CASE WHEN loja_id IN (1, 3) THEN 39.00 WHEN loja_id = 4 THEN 40.00 ELSE 38.00 END,
    CASE loja_id WHEN 1 THEN 45000 WHEN 2 THEN 28000 WHEN 3 THEN 35000 WHEN 4 THEN 52000 ELSE 30000 END,
    meta_mensal * 0.06,
    meta_mensal * 0.22
FROM dim_loja
CROSS JOIN GENERATE_SERIES(1, 12) AS meses(mes)
ON CONFLICT (loja_id, ano, mes) DO UPDATE SET
    receita_orcada = EXCLUDED.receita_orcada,
    margem_bruta_orcada = EXCLUDED.margem_bruta_orcada,
    despesas_fixas_orcadas = EXCLUDED.despesas_fixas_orcadas,
    despesas_var_orcadas = EXCLUDED.despesas_var_orcadas,
    resultado_orcado = EXCLUDED.resultado_orcado;

