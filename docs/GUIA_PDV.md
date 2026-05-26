# Guia do Operador - Terminal PDV RetailCo

## Finalidade

A tela de Operação PDV permite simular o fechamento de um turno de loja e
encaminhar as vendas geradas ao Data Warehouse. Não é uma demonstração
estática: cada emissão cria um arquivo Raw real e cada processamento altera
os indicadores disponíveis no Painel de Indicadores.

## Acesso

1. Garanta que a plataforma esteja ativa:

```bash
docker compose --env-file .env up -d api frontend postgres_dw
```

2. Abra:

```text
http://localhost:5173/pdv
```

3. Para voltar aos indicadores financeiros, use a navegação
`Indicadores FP&A` ou acesse `http://localhost:5173`.

## Tela de Operação

| Área | Uso |
| --- | --- |
| `Emitir turno` | Parametriza e fecha um turno |
| `Fechar dia completo, emitir Raw e carregar DW` | Emite todas as cinco lojas e três turnos da data e carrega o DW |
| `Resumo do caixa` | Mostra líquido, descontos, volume e status da emissão |
| `Movimento do turno` | Exibe as vendas individuais geradas |
| `Processar data no DW` | Envia as origens da data para o ETL |

## Emitir Um Turno

Preencha os campos:

| Campo | Descrição | Regra |
| --- | --- | --- |
| Loja | Unidade responsável pelo caixa | Uma das cinco lojas cadastradas |
| Data operacional | Dia da venda | Formato de data válido |
| Turno | Janela de operação | `MANHA`, `TARDE` ou `NOITE` |
| Vendas no turno | Quantidade de registros a gerar | Entre `1` e `150` |
| Semente da simulação | Permite repetibilidade dos valores | Inteiro positivo |

Clique em `Fechar turno e emitir Raw`.

Após sucesso, a tela mostra:

- Caminho do arquivo Raw gravado.
- Total bruto, descontos e total líquido do fechamento.
- Quantidades concluídas, pendentes e canceladas.
- Relação de transações, produtos, clientes e forma de pagamento.

## Regra de Imutabilidade

Um fechamento já emitido para a mesma combinação de loja, data e turno não
pode ser emitido novamente na tela. Essa regra protege o documento de origem.

Exemplo:

| Loja | Data | Turno | Resultado da segunda emissão |
| --- | --- | --- | --- |
| Loja Centro | `2026-05-25` | `MANHA` | Rejeitada, arquivo Raw já existente |

Para operar a mesma loja na mesma data, selecione outro turno. Os identificadores
de vendas e clientes são separados por turno para que não haja colisão.

## Fechar o Dia Completo

Para simular o fechamento geral operacional:

1. Informe a data, a quantidade de vendas por turno e a semente.
2. Clique em `Fechar dia completo, emitir Raw e carregar DW`.
3. Confira o resumo consolidado e a relação de arquivos emitidos.
4. Confira o retorno `Data carregada no DW`, pois a atualização é automática.

A operação emite `5 lojas x 3 turnos = 15 arquivos Raw`. A quantidade informada
é aplicada a cada turno; por exemplo, `20` gera `300` transações no dia.

Por proteção de origem, o fechamento geral somente é iniciado quando nenhum
dos quinze documentos da data já existe. Uma data com turno previamente emitido
deve ser processada com os arquivos existentes ou substituída por outra data de
simulação.

O botão `Processar data no DW` permanece disponível para fechamentos individuais
já emitidos ou para recuperar arquivos Raw existentes que ainda não tenham sido carregados.

## Processar a Data no Warehouse

Depois de emitir um ou mais turnos de uma data, clique em
`Processar data no DW`.

O botão executa:

```text
Raw -> Bronze -> Validação -> Silver -> Gold -> Data Warehouse
```

Essa ação é imediata e é executada pela API do PDV, sem criar uma execução
na interface do Airflow. Para rodar o mesmo processamento sob supervisão do
Airflow, com visualização de tarefas e novas tentativas, use:

```bash
make trigger-airflow REFERENCE_DATE=2026-05-25
```

O retorno apresentado contém:

| Informação | Significado |
| --- | --- |
| `Run ID` | Identificador rastreável da carga acionada pelo PDV |
| `Inseridos` | Fatos novos incluídos no DW |
| `Atualizados` | Fatos já existentes reprocessados |
| `Válidos` | Linhas aprovadas na qualidade |
| `Cancelados` | Registros separados como cancelamento |

## Conferir no Painel de Indicadores

1. Navegue para `Indicadores FP&A`.
2. Selecione a competência correspondente à data processada.
3. Observe a atualização de receita, ticket, status e métricas operacionais.

Observação: o recibo do PDV apresenta o fechamento emitido, inclusive vendas
canceladas. O painel financeiro soma receita de vendas concluídas conforme
a regra analítica do warehouse.

## Exemplo Operacional Completo

1. Selecione `Loja Centro`.
2. Informe a data `2026-05-25`.
3. Escolha o turno `MANHA`.
4. Informe `8` vendas e uma semente positiva.
5. Clique em `Fechar turno e emitir Raw`.
6. Confira os registros exibidos no movimento do turno.
7. Clique em `Processar data no DW`.
8. Abra o Painel de Indicadores e selecione `maio de 2026`.

Em uma execução validada durante o desenvolvimento, esse cenário gerou:

| Resultado | Valor |
| --- | ---: |
| Vendas Raw emitidas | 8 |
| Concluídas | 7 |
| Canceladas | 1 |
| Registros inseridos no DW | 8 |

## Problemas Comuns

| Mensagem ou situação | Causa provável | Ação |
| --- | --- | --- |
| Arquivo Raw já existe | O turno já foi fechado | Selecione outro turno/data |
| Nenhum fechamento Raw emitido nesta data | Processamento acionado sem origem | Emita ao menos um turno |
| Painel não mostra o dia imediatamente | Competência ainda não foi processada | Execute `Processar data no DW` |
| API indisponível | Serviço não iniciado | Execute `docker compose --env-file .env up -d api` |

## Rastreabilidade

Para localizar o evento após a operação:

```sql
SELECT *
FROM pipeline_audit_log
WHERE run_id LIKE 'pdv_api_%'
ORDER BY created_at DESC;
```

```sql
SELECT file_path, status, registros_lidos, processed_at
FROM processed_files
WHERE data_referencia = '2026-05-25'
ORDER BY file_path;
```

## Referências

- [Diagrama de Fluxo](DIAGRAMA_FLUXO.md)
- [Arquitetura e Operação](ARQUITETURA_E_OPERACAO.md)
- [Referência REST da API](API_REFERENCE.md)
