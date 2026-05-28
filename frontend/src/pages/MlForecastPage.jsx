import { useState } from "react";

import { ErrorState, LoadingState } from "../components/Feedback";
import { LineChart } from "../components/LineChart";
import { Navigation } from "../components/Navigation";
import { useMlForecast } from "../hooks/useMlForecast";
import { formatCompetence, formatCurrency, formatPercent, formatTimestamp } from "../utils/format";

function revenuePoints(rows, key) {
  return rows.map((row) => ({ competencia: row.competencia, receita: row[key] }));
}

function formatSignedCurrency(value) {
  const number = Number(value || 0);
  return `${number > 0 ? "+" : ""}${formatCurrency(number)}`;
}

function safeCompetence(value) {
  return value ? formatCompetence(value) : "-";
}

export function MlForecastPage() {
  const [months, setMonths] = useState(6);
  const [selectedStore, setSelectedStore] = useState("1");
  const result = useMlForecast(months);

  if (result.loading && !result.snapshot) return <LoadingState />;
  if (result.error && !result.snapshot) {
    return <ErrorState message={result.error} onRetry={result.refresh} />;
  }

  const { data, updated_at: updatedAt } = result.snapshot;
  const firstProjection = data.network.projection[0];
  const selectedStoreModel = data.store_models.find((store) => store.loja_id === Number(selectedStore));
  const networkSeries = [
    { label: "Realizado", points: revenuePoints(data.history, "receita") },
    { label: "Previsão ML", points: revenuePoints(data.network.projection, "previsao") },
    { label: "Limite superior", points: revenuePoints(data.network.projection, "limite_superior") },
    { label: "Limite inferior", points: revenuePoints(data.network.projection, "limite_inferior") },
  ];
  const storeSeries = [
    { label: "Realizado", points: revenuePoints(selectedStoreModel?.history || [], "receita") },
    { label: "Previsão ML", points: revenuePoints(selectedStoreModel?.projection || [], "previsao") },
  ];

  return (
    <div className="dashboard-shell forecast-shell">
      <Navigation active="ml" />
      <header className="topbar evolution-topbar">
        <div>
          <p className="eyebrow">Modelo estatístico / Receita mensal</p>
          <h1>Previsão ML</h1>
          <p className="hero-copy">
            Use uma regressão linear simples para estimar os próximos meses a partir do histórico realizado,
            com backtest do último mês e faixa de confiança estimada.
          </p>
        </div>
        <div className="live-status" aria-label="Status da previsão estatística">
          <span className={`signal ${result.refreshing ? "pulse" : ""}`} />
          <div>
            <strong>{result.refreshing ? "Treinando modelo" : "Modelo atualizado"}</strong>
            <small>Última atualização: {formatTimestamp(updatedAt)}</small>
          </div>
        </div>
      </header>

      <section className="filters forecast-filters" aria-label="Controles da previsão ML">
        <div>
          <label htmlFor="ml-horizon">Horizonte previsto</label>
          <select id="ml-horizon" value={months} onChange={(event) => setMonths(Number(event.target.value))}>
            <option value={3}>3 meses</option>
            <option value={6}>6 meses</option>
            <option value={9}>9 meses</option>
            <option value={12}>12 meses</option>
          </select>
        </div>
        <p>
          A previsão é treinada com as competências realizadas até {formatCompetence(data.latest_competence)}.
          Junho aparece como previsão futura, não como valor realizado.
        </p>
        <button onClick={result.refresh} type="button">Retreinar previsão</button>
      </section>
      {result.error ? <p className="inline-error">{result.error}</p> : null}

      <section className="forecast-kpis" aria-label="Resumo do modelo estatístico">
        <article className="highlight">
          <span>Próximo mês previsto</span>
          <strong>{formatCurrency(firstProjection?.previsao)}</strong>
          <small>{safeCompetence(firstProjection?.competencia)}</small>
        </article>
        <article>
          <span>Tendência mensal</span>
          <strong className={data.network.model.tendencia_mensal_pct >= 0 ? "positive" : "negative"}>
            {formatPercent(data.network.model.tendencia_mensal_pct)}
          </strong>
          <small>{formatSignedCurrency(data.network.model.coeficiente_mensal)} por mês</small>
        </article>
        <article>
          <span>Erro do backtest</span>
          <strong>{formatPercent(data.network.backtest?.erro_percentual_abs)}</strong>
          <small>{safeCompetence(data.network.backtest?.competencia)}</small>
        </article>
        <article>
          <span>RMSE do modelo</span>
          <strong>{formatCurrency(data.network.model.rmse)}</strong>
          <small>{data.network.model.observacoes_treino} meses no treino</small>
        </article>
        <article>
          <span>Ajuste R²</span>
          <strong>{formatPercent(data.network.model.r2 * 100)}</strong>
          <small>Qualidade do ajuste linear</small>
        </article>
      </section>

      <section className="forecast-grid">
        <article className="panel network-forecast-chart">
          <div className="panel-header">
            <div>
              <p className="eyebrow">Rede</p>
              <h2>Realizado x previsão estatística</h2>
            </div>
          </div>
          <LineChart
            ariaLabel="Receita realizada e previsão estatística da rede"
            series={networkSeries}
            valueKey="receita"
            valueType="currency"
          />
        </article>

        <article className="panel forecast-method ml-method">
          <div className="panel-header">
            <div>
              <p className="eyebrow">Como funciona</p>
              <h2>Modelo utilizado</h2>
            </div>
          </div>
          <p>{data.methodology.objective}</p>
          <p>{data.methodology.model}</p>
          <p>{data.methodology.validation}</p>
          <p>{data.methodology.interval}</p>
        </article>

        <article className="panel store-forecast-chart">
          <div className="panel-header forecast-store-header">
            <div>
              <p className="eyebrow">Unidade</p>
              <h2>Previsão por loja</h2>
            </div>
            <select
              aria-label="Loja analisada na previsão ML"
              value={selectedStore}
              onChange={(event) => setSelectedStore(event.target.value)}
            >
              {data.stores.map((store) => (
                <option key={store.loja_id} value={store.loja_id}>{store.loja_nome}</option>
              ))}
            </select>
          </div>
          <LineChart
            ariaLabel={`Receita realizada e previsão ML de ${selectedStoreModel?.loja_nome}`}
            series={storeSeries}
            valueKey="receita"
            valueType="currency"
          />
        </article>

        <article className="panel forecast-table-panel">
          <div className="panel-header">
            <div>
              <p className="eyebrow">Detalhamento</p>
              <h2>{selectedStoreModel?.loja_nome}</h2>
            </div>
          </div>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Mês</th>
                  <th>Previsão</th>
                  <th>Limite inferior</th>
                  <th>Limite superior</th>
                </tr>
              </thead>
              <tbody>
                {selectedStoreModel?.projection.map((row) => (
                  <tr key={row.competencia}>
                    <td>{safeCompetence(row.competencia)}</td>
                    <td>{formatCurrency(row.previsao)}</td>
                    <td>{formatCurrency(row.limite_inferior)}</td>
                    <td>{formatCurrency(row.limite_superior)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="model-footnote">
            Backtest da loja: {formatPercent(selectedStoreModel?.backtest?.erro_percentual_abs)} de erro absoluto
            em {safeCompetence(selectedStoreModel?.backtest?.competencia)}.
          </p>
        </article>
      </section>
    </div>
  );
}
