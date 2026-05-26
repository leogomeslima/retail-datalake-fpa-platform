import { useState } from "react";

import { ErrorState, LoadingState } from "../components/Feedback";
import { LineChart } from "../components/LineChart";
import { Navigation } from "../components/Navigation";
import { useForecast } from "../hooks/useForecast";
import { formatCompetence, formatCurrency, formatPercent, formatTimestamp } from "../utils/format";

function sum(rows, key) {
  return rows.reduce((total, row) => total + Number(row[key] || 0), 0);
}

function revenuePoints(rows, key) {
  return rows.map((row) => ({ competencia: row.competencia, receita: row[key] }));
}

export function ForecastPage() {
  const [months, setMonths] = useState(6);
  const [adjustmentPct, setAdjustmentPct] = useState(0);
  const [selectedStore, setSelectedStore] = useState("1");
  const result = useForecast(months, adjustmentPct);

  function changeAdjustment(value) {
    setAdjustmentPct(Math.max(-30, Math.min(30, Number(value) || 0)));
  }

  if (result.loading && !result.snapshot) return <LoadingState />;
  if (result.error && !result.snapshot) {
    return <ErrorState message={result.error} onRetry={result.refresh} />;
  }

  const { data, updated_at: updatedAt } = result.snapshot;
  const firstMonth = data.network_projection[0];
  const totalForecast = sum(data.network_projection, "forecast_ajustado");
  const totalBase = sum(data.network_projection, "forecast_base");
  const budgetRows = data.network_projection.filter((row) => row.receita_orcada !== null);
  const totalBudget = sum(budgetRows, "receita_orcada");
  const forecastWithBudget = sum(budgetRows, "forecast_ajustado");
  const totalVariance = forecastWithBudget - totalBudget;
  const projectionDelta = totalBase ? ((totalForecast - totalBase) / totalBase) * 100 : 0;
  const store = data.stores.find((item) => item.loja_id === Number(selectedStore));
  const storeHistory = data.store_history.filter((row) => row.loja_id === Number(selectedStore));
  const storeProjection = data.store_projection.filter((row) => row.loja_id === Number(selectedStore));

  const networkSeries = [
    {
      label: "Realizado",
      points: revenuePoints(data.history, "receita_liquida"),
    },
    {
      label: "Forecast base",
      points: revenuePoints(data.network_projection, "forecast_base"),
    },
    {
      label: "Forecast ajustado",
      points: revenuePoints(data.network_projection, "forecast_ajustado"),
    },
  ];
  const storeSeries = [
    { label: "Realizado", points: revenuePoints(storeHistory, "receita") },
    { label: "Forecast ajustado", points: revenuePoints(storeProjection, "forecast_ajustado") },
  ];

  return (
    <div className="dashboard-shell forecast-shell">
      <Navigation active="forecast" />
      <header className="topbar evolution-topbar">
        <div>
          <p className="eyebrow">RetailCo S.A. / Planejamento preditivo</p>
          <h1>Ajuste de Forecast</h1>
          <p className="hero-copy">
            Projete os próximos meses a partir do realizado, ajuste o cenário e compare com o orçamento provisionado.
          </p>
        </div>
        <div className="live-status" aria-label="Status da atualização">
          <span className={`signal ${result.refreshing ? "pulse" : ""}`} />
          <div>
            <strong>{result.refreshing ? "Recalculando" : "Cenário calculado"}</strong>
            <small>Última atualização: {formatTimestamp(updatedAt)}</small>
          </div>
        </div>
      </header>

      <section className="filters forecast-filters" aria-label="Controles do forecast">
        <div>
          <label htmlFor="forecast-horizon">Horizonte projetado</label>
          <select
            id="forecast-horizon"
            value={months}
            onChange={(event) => setMonths(Number(event.target.value))}
          >
            <option value={3}>3 meses</option>
            <option value={6}>6 meses</option>
            <option value={9}>9 meses</option>
            <option value={12}>12 meses</option>
          </select>
        </div>
        <div className="adjustment-control">
          <label htmlFor="forecast-adjustment">Ajuste gerencial sobre a base</label>
          <div>
            <input
              id="forecast-adjustment"
              max="30"
              min="-30"
              onChange={(event) => changeAdjustment(event.target.value)}
              step="1"
              type="range"
              value={adjustmentPct}
            />
            <input
              aria-label="Ajuste percentual informado"
              className="adjustment-value-input"
              max="30"
              min="-30"
              onChange={(event) => changeAdjustment(event.target.value)}
              step="1"
              type="number"
              value={adjustmentPct}
            />
            <strong>%</strong>
          </div>
        </div>
        <button onClick={result.refresh} type="button">Recalcular cenário</button>
      </section>
      {result.error ? <p className="inline-error">{result.error}</p> : null}

      <section className="forecast-kpis" aria-label="Resumo da projeção">
        <article className="highlight">
          <span>Forecast próximo mês</span>
          <strong>{formatCurrency(firstMonth?.forecast_ajustado)}</strong>
          <small>{formatCompetence(firstMonth?.competencia)}</small>
        </article>
        <article>
          <span>Forecast acumulado</span>
          <strong>{formatCurrency(totalForecast)}</strong>
          <small>{months} meses projetados</small>
        </article>
        <article>
          <span>Impacto do ajuste</span>
          <strong className={projectionDelta >= 0 ? "positive" : "negative"}>
            {projectionDelta > 0 ? "+" : ""}{formatPercent(projectionDelta)}
          </strong>
          <small>Comparado ao cenario base</small>
        </article>
        <article>
          <span>Desvio vs. orçamento</span>
          <strong className={totalVariance >= 0 ? "positive" : "negative"}>
            {formatCurrency(totalVariance)}
          </strong>
          <small>{budgetRows.length} meses com orçamento disponível</small>
        </article>
        <article>
          <span>EBITDA estimado</span>
          <strong>{formatCurrency(firstMonth?.ebitda_estimado)}</strong>
          <small>Margem de referência {formatPercent(firstMonth?.margem_ebitda_referencia_pct)}</small>
        </article>
      </section>

      <section className="forecast-grid">
        <article className="panel network-forecast-chart">
          <div className="panel-header">
            <div>
              <p className="eyebrow">Rede</p>
              <h2>Realizado x forecast de receita</h2>
            </div>
          </div>
          <LineChart
            ariaLabel="Receita realizada e prevista da rede"
            series={networkSeries}
            valueKey="receita"
            valueType="currency"
          />
        </article>

        <article className="panel forecast-method">
          <div className="panel-header">
            <div>
              <p className="eyebrow">Premissas</p>
              <h2>Modelo do cenário</h2>
            </div>
          </div>
          <p>{data.methodology.base}</p>
          <p>{data.methodology.trend}</p>
          <p>{data.methodology.adjustment}</p>
          <small>Última competência realizada: {formatCompetence(data.latest_competence)}</small>
        </article>

        <article className="panel store-forecast-chart">
          <div className="panel-header forecast-store-header">
            <div>
              <p className="eyebrow">Unidade</p>
              <h2>Trajetória por loja</h2>
            </div>
            <select
              aria-label="Loja analisada no forecast"
              value={selectedStore}
              onChange={(event) => setSelectedStore(event.target.value)}
            >
              {data.stores.map((item) => (
                <option key={item.loja_id} value={item.loja_id}>{item.loja_nome}</option>
              ))}
            </select>
          </div>
          <LineChart
            ariaLabel={`Receita realizada e prevista de ${store?.loja_nome}`}
            series={storeSeries}
            valueKey="receita"
            valueType="currency"
          />
        </article>

        <article className="panel forecast-table-panel">
          <div className="panel-header">
            <div>
              <p className="eyebrow">Detalhamento</p>
              <h2>{store?.loja_nome}</h2>
            </div>
          </div>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Mês</th>
                  <th>Forecast</th>
                  <th>Budget</th>
                  <th>Desvio</th>
                  <th>Meta</th>
                </tr>
              </thead>
              <tbody>
                {storeProjection.map((row) => (
                  <tr key={row.competencia}>
                    <td>{formatCompetence(row.competencia)}</td>
                    <td>{formatCurrency(row.forecast_ajustado)}</td>
                    <td>{row.receita_orcada === null ? "Não provisionado" : formatCurrency(row.receita_orcada)}</td>
                    <td className={Number(row.variacao_orcamento) >= 0 ? "positive" : "negative"}>
                      {row.variacao_orcamento === null ? "-" : formatCurrency(row.variacao_orcamento)}
                    </td>
                    <td>{row.meta_atingida_pct === null ? "-" : formatPercent(row.meta_atingida_pct)}</td>
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
