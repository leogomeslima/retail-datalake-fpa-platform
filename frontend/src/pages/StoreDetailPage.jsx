import { useState } from "react";

import { ErrorState, LoadingState } from "../components/Feedback";
import { LineChart } from "../components/LineChart";
import { Navigation } from "../components/Navigation";
import { useStoreDetail } from "../hooks/useStoreDetail";
import { formatCompetence, formatCurrency, formatNumber, formatPercent, formatTimestamp } from "../utils/format";

function currentStoreId() {
  const match = window.location.pathname.match(/\/lojas\/(\d+)/);
  return Number(match?.[1] || 1);
}

function fileName(path) {
  return String(path || "").split(/[\\/]/).pop() || "Arquivo não identificado";
}

function revenuePoints(rows, key) {
  return rows.map((row) => ({ competencia: row.competencia, receita: row[key] }));
}

function statusTone(status) {
  const normalized = String(status || "").toLowerCase();
  if (["success", "processed", "concluida"].includes(normalized)) return "verde";
  if (["reprocessed", "pendente"].includes(normalized)) return "amarelo";
  return "vermelho";
}

export function StoreDetailPage() {
  const [storeId, setStoreId] = useState(currentStoreId());
  const [forecastMonths, setForecastMonths] = useState(6);
  const result = useStoreDetail(storeId, forecastMonths);

  function changeStore(value) {
    const nextStoreId = Number(value);
    setStoreId(nextStoreId);
    window.history.replaceState(null, "", `/lojas/${nextStoreId}`);
  }

  if (result.loading && !result.snapshot) return <LoadingState />;
  if (result.error && !result.snapshot) {
    return <ErrorState message={result.error} onRetry={result.refresh} />;
  }

  const { data, updated_at: updatedAt } = result.snapshot;
  const forecastSeries = [
    { label: "Realizado", points: revenuePoints(data.history, "receita") },
    { label: "Forecast gerencial", points: revenuePoints(data.forecast_projection, "forecast_ajustado") },
    { label: "Previsão ML", points: revenuePoints(data.ml_prediction.projection, "previsao") },
  ];
  const marginSeries = [{ label: data.store.loja_nome, points: data.history }];
  const nextForecast = data.forecast_projection[0];
  const nextMl = data.ml_prediction.projection[0];

  return (
    <div className="dashboard-shell store-detail-shell">
      <Navigation active="store" />
      <header className="topbar evolution-topbar">
        <div>
          <p className="eyebrow">Drill-down por loja</p>
          <h1>{data.store.loja_nome}</h1>
          <p className="hero-copy">
            Visão integrada da unidade: desempenho, meta, produtos, canais, qualidade dos arquivos e previsão
            dos próximos meses.
          </p>
        </div>
        <div className="live-status" aria-label="Status do detalhe da loja">
          <span className={`signal ${result.refreshing ? "pulse" : ""}`} />
          <div>
            <strong>{result.refreshing ? "Atualizando loja" : "Loja atualizada"}</strong>
            <small>Última atualização: {formatTimestamp(updatedAt)}</small>
          </div>
        </div>
      </header>

      <section className="filters store-detail-filters" aria-label="Filtros do detalhe da loja">
        <div>
          <label htmlFor="store-select">Loja analisada</label>
          <select id="store-select" value={storeId} onChange={(event) => changeStore(event.target.value)}>
            {[1, 2, 3, 4, 5].map((id) => (
              <option key={id} value={id}>Loja {id}</option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor="store-horizon">Horizonte previsto</label>
          <select
            id="store-horizon"
            value={forecastMonths}
            onChange={(event) => setForecastMonths(Number(event.target.value))}
          >
            <option value={3}>3 meses</option>
            <option value={6}>6 meses</option>
            <option value={9}>9 meses</option>
            <option value={12}>12 meses</option>
          </select>
        </div>
        <p>
          Última competência: {formatCompetence(data.latest_competence)}. Unidade em {data.store.cidade}/{data.store.estado},
          região {data.store.regiao}, tier {data.store.tier}.
        </p>
        <button onClick={result.refresh} type="button">Atualizar loja</button>
      </section>
      {result.error ? <p className="inline-error">{result.error}</p> : null}

      <section className="store-detail-kpis" aria-label="Indicadores da loja">
        <article className="highlight">
          <span>Receita líquida</span>
          <strong>{formatCurrency(data.overview.receita_liquida)}</strong>
          <small>{formatPercent(data.overview.crescimento_mom)} vs. mês anterior</small>
        </article>
        <article>
          <span>Meta atingida</span>
          <strong>{formatPercent(data.overview.meta_atingida_pct)}</strong>
          <small>{formatCurrency(data.overview.receita_orcada)} orçado</small>
        </article>
        <article>
          <span>Ticket médio</span>
          <strong>{formatCurrency(data.overview.ticket_medio)}</strong>
          <small>{formatNumber(data.overview.pedidos)} pedidos concluídos</small>
        </article>
        <article>
          <span>Ranking / share</span>
          <strong>#{formatNumber(data.overview.ranking)}</strong>
          <small>{formatPercent(data.overview.market_share_pct)} da rede</small>
        </article>
        <article>
          <span>EBITDA</span>
          <strong>{formatCurrency(data.overview.ebitda)}</strong>
          <small>Margem {formatPercent(data.overview.margem_ebitda_pct)}</small>
        </article>
      </section>

      <section className="store-detail-grid">
        <article className="panel store-detail-chart">
          <div className="panel-header">
            <div>
              <p className="eyebrow">Receita</p>
              <h2>Realizado x previsões</h2>
            </div>
          </div>
          <LineChart
            ariaLabel={`Receita e previsão de ${data.store.loja_nome}`}
            series={forecastSeries}
            valueKey="receita"
            valueType="currency"
          />
        </article>

        <article className="panel store-detail-summary">
          <div className="panel-header">
            <div>
              <p className="eyebrow">Próximo mês</p>
              <h2>Leitura rápida</h2>
            </div>
          </div>
          <div className="store-insights">
            <div>
              <span>Forecast gerencial</span>
              <strong>{formatCurrency(nextForecast?.forecast_ajustado)}</strong>
              <small>{formatCompetence(nextForecast?.competencia)}</small>
            </div>
            <div>
              <span>Previsão ML</span>
              <strong>{formatCurrency(nextMl?.previsao)}</strong>
              <small>{formatPercent(data.ml_prediction.model.tendencia_mensal_pct)} de tendência mensal</small>
            </div>
            <div>
              <span>Status da meta</span>
              <strong className={data.overview.variacao_absoluta >= 0 ? "positive" : "negative"}>
                {formatCurrency(data.overview.variacao_absoluta)}
              </strong>
              <small>{data.overview.status_semaforo}</small>
            </div>
          </div>
        </article>

        <article className="panel">
          <div className="panel-header">
            <div>
              <p className="eyebrow">Rentabilidade</p>
              <h2>Margem e meta</h2>
            </div>
          </div>
          <LineChart
            ariaLabel={`Margem bruta e meta de ${data.store.loja_nome}`}
            series={marginSeries}
            valueKey="margem_pct"
            valueType="percent"
          />
        </article>

        <article className="panel">
          <div className="panel-header">
            <div>
              <p className="eyebrow">Produtos</p>
              <h2>Top produtos da competência</h2>
            </div>
          </div>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Produto</th>
                  <th>Categoria</th>
                  <th>Receita</th>
                  <th>Volume</th>
                  <th>Margem</th>
                </tr>
              </thead>
              <tbody>
                {data.products.map((product) => (
                  <tr key={product.produto_id}>
                    <td>{product.produto_nome}</td>
                    <td>{product.categoria}</td>
                    <td>{formatCurrency(product.receita)}</td>
                    <td>{formatNumber(product.volume)}</td>
                    <td>{formatPercent(product.margem_pct)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </article>

        <article className="panel">
          <div className="panel-header">
            <div>
              <p className="eyebrow">Canais</p>
              <h2>Canais e pagamentos</h2>
            </div>
          </div>
          <div className="channel-list-detail">
            {data.channels.map((channel) => (
              <div key={`${channel.canal_venda}-${channel.forma_pagamento}`}>
                <span>{channel.canal_venda} / {channel.forma_pagamento}</span>
                <strong>{formatCurrency(channel.receita)}</strong>
                <small>{formatNumber(channel.pedidos)} pedidos, ticket {formatCurrency(channel.ticket_medio)}</small>
              </div>
            ))}
          </div>
        </article>

        <article className="panel">
          <div className="panel-header">
            <div>
              <p className="eyebrow">Operação</p>
              <h2>Status das vendas</h2>
            </div>
          </div>
          <div className="status-mix-list">
            {data.status_mix.map((item) => (
              <div key={item.status}>
                <span className={`badge ${statusTone(item.status)}`}>{item.status}</span>
                <strong>{formatNumber(item.registros)}</strong>
                <small>{formatCurrency(item.valor_liquido)}</small>
              </div>
            ))}
          </div>
        </article>

        <article className="panel store-detail-wide">
          <div className="panel-header">
            <div>
              <p className="eyebrow">Qualidade</p>
              <h2>Arquivos e aprovação da loja</h2>
            </div>
          </div>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Data</th>
                  <th>Arquivos</th>
                  <th>Lidos</th>
                  <th>Válidos</th>
                  <th>Inválidos</th>
                  <th>Aprovação</th>
                </tr>
              </thead>
              <tbody>
                {data.quality.map((row) => (
                  <tr key={row.data_referencia}>
                    <td>{row.data_referencia}</td>
                    <td>{formatNumber(row.arquivos)}</td>
                    <td>{formatNumber(row.registros_lidos)}</td>
                    <td>{formatNumber(row.registros_validos)}</td>
                    <td>{formatNumber(row.registros_invalidos)}</td>
                    <td>{formatPercent(row.taxa_aprovacao)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </article>

        <article className="panel store-detail-wide">
          <div className="panel-header">
            <div>
              <p className="eyebrow">Rastreabilidade</p>
              <h2>Últimos arquivos da loja</h2>
            </div>
          </div>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Arquivo</th>
                  <th>Data</th>
                  <th>Camada</th>
                  <th>Status</th>
                  <th>Registros</th>
                  <th>Atualizado em</th>
                </tr>
              </thead>
              <tbody>
                {data.recent_files.map((file) => (
                  <tr key={file.file_id}>
                    <td className="raw-file-name">{fileName(file.file_path)}</td>
                    <td>{file.data_referencia}</td>
                    <td>{file.camada_destino}</td>
                    <td><span className={`badge ${statusTone(file.status)}`}>{file.status}</span></td>
                    <td>{formatNumber(file.registros_validos)} / {formatNumber(file.registros_lidos)}</td>
                    <td>{formatTimestamp(file.updated_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </article>
      </section>
    </div>
  );
}
