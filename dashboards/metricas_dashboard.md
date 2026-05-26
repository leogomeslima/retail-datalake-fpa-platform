# Dicionário de Métricas

| Métrica | Fórmula | Origem |
| --- | --- | --- |
| Receita bruta | `SUM(valor_bruto)` de vendas concluídas | `fato_vendas` |
| Receita líquida | `SUM(valor_liquido)` de vendas concluídas | `fato_vendas` |
| Ticket médio | `receita_liquida / pedidos` | `vw_faturamento_mensal` |
| Participação na receita | `receita_loja / receita_rede` | `vw_faturamento_por_loja` |
| Margem bruta percentual | `lucro_bruto / receita_liquida` | `fato_dre` |
| EBITDA | `lucro_bruto - despesas_variaveis - despesas_fixas` | `fato_dre` |
| Meta atingida | `receita_realizada / receita_orcada` | `vw_meta_vs_realizado` |
| Forecast mensal | `media_diaria * dias_no_mes` | `vw_indicadores_fpa` |
| Run rate anual | `forecast_mensal * 12` | `vw_indicadores_fpa` |
| Taxa de aprovação | `validos / lidos` | `pipeline_audit_log` |

Filtros globais recomendados: competência, loja, estado, categoria, canal e segmento.
