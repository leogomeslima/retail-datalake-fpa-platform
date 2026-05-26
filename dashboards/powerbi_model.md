# Modelo Power BI - RetailCo FP&A

## Conexão

Conecte ao PostgreSQL `retail_dw` no host publicado pelo Docker, porta `5432`, usando o
usuário configurado no arquivo `.env`. Em modo Import, carregue as views analíticas; para
atualização frequente, DirectQuery pode ser aplicado a `vw_faturamento_por_loja`.

## Modelo semântico

| Tabela ou view | Função no modelo | Chaves principais |
| --- | --- | --- |
| `dim_loja` | Dimensão organizacional | `loja_id` |
| `dim_produto` | Hierarquia de sortimento | `produto_id` |
| `dim_tempo` | Calendário marcado como tabela de data | `data_sk` |
| `fato_vendas` | Venda em grão de um item | `id_venda`, `loja_id` |
| `fato_orcamento` | Orçamento mensal | `loja_id`, `ano`, `mes` |
| `fato_dre` | Resultado mensal | `loja_id`, `ano`, `mes` |

Relacione dimensões em cardinalidade um-para-muitos com fatos e direção única da dimensão
para o fato. A primeira versão registra apenas um item por venda.

## Páginas recomendadas

1. Visão executiva: receita líquida, meta atingida, EBITDA, margem e alertas.
2. Lojas: ranking, participação na receita, ticket médio e variação mensal.
3. Produtos: top dez, categoria, volume, margem e desconto.
4. FP&A: variação do orçamento, forecast, ritmo anual e DRE.
5. Operação: qualidade, arquivos processados e saúde do pipeline.
