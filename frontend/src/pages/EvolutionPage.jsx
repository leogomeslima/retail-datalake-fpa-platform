import { useState } from "react";

import { ErrorState, LoadingState } from "../components/Feedback";
import { LineChart } from "../components/LineChart";
import { Navigation } from "../components/Navigation";
import { useEvolution } from "../hooks/useEvolution";
import { formatCompetence, formatCurrency, formatPercent, formatTimestamp } from "../utils/format";

const MEASURES = {
  receita: { label: "Receita líquida", type: "currency" },
  ticket_medio: { label: "Ticket médio", type: "currency" },
  margem_pct: { label: "Margem bruta", type: "percent" },
  meta_atingida_pct: { label: "Meta atingida", type: "percent" },
  market_share_pct: { label: "Market share", type: "percent" },
};

function delta(current, previous) {
  if (!previous) return null;
  const before = Number(previous);
  return before === 0 ? null : ((Number(current) - before) / before) * 100;
}

export function EvolutionPage() {
  const evolution = useEvolution();
  const [measure, setMeasure] = useState("receita");
  const [selectedStore, setSelectedStore] = useState("1");

  if (evolution.loading && !evolution.snapshot) return <LoadingState />;
  if (evolution.error && !evolution.snapshot) {
    return <ErrorState message={evolution.error} onRetry={evolution.refresh} />;
  }

  const { data, updated_at: updatedAt } = evolution.snapshot;
  const storeLines = data.stores.map((store) => ({
    label: store.loja_nome,
    points: data.store_series.filter((row) => row.loja_id === store.loja_id),
  }));
  const storeHistory = data.store_series.filter((row) => row.loja_id === Number(selectedStore));
  const current = storeHistory.at(-1);
  const previous = storeHistory.at(-2);
  const latestNetwork = data.network.at(-1);
  const previousNetwork = data.network.at(-2);
  const revenueDelta = delta(current?.receita, previous?.receita);
  const ebitdaDelta = delta(latestNetwork?.ebitda, previousNetwork?.ebitda);
  const focusedSeries = [{ label: current?.loja_nome || "Loja", points: storeHistory }];

  return (
    <div className="dashboard-shell evolution-shell">
      <Navigation active="evolution" />
      <header className="topbar evolution-topbar">
        <div>
          <p className="eyebrow">RetailCo S.A. / Desempenho temporal</p>
          <h1>Evolução de Lojas</h1>
          <p className="hero-copy">
            Acompanhe receita, ticket, margem, participação e atingimento de meta ao longo das competências.
          </p>
        </div>
        <div className="live-status" aria-label="Status da atualização">
          <span className={`signal ${evolution.refreshing ? "pulse" : ""}`} />
          <div>
            <strong>{evolution.refreshing ? "Atualizando" : "Séries atualizadas"}</strong>
            <small>Última atualização: {formatTimestamp(updatedAt)}</small>
          </div>
        </div>
      </header>

      <section className="filters evolution-filters" aria-label="Filtros de evolução">
        <div>
          <label htmlFor="metric">Medida comparada</label>
          <select id="metric" value={measure} onChange={(event) => setMeasure(event.target.value)}>
            {Object.entries(MEASURES).map(([key, item]) => (
              <option key={key} value={key}>{item.label}</option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor="store">Detalhe da loja</label>
          <select id="store" value={selectedStore} onChange={(event) => setSelectedStore(event.target.value)}>
            {data.stores.map((store) => (
              <option key={store.loja_id} value={store.loja_id}>{store.loja_nome}</option>
            ))}
          </select>
        </div>
        <p>Base disponível: {data.network.length} competências processadas no Data Warehouse.</p>
        <button onClick={evolution.refresh} type="button">Atualizar séries</button>
      </section>
      {evolution.error ? <p className="inline-error">{evolution.error}</p> : null}
      {current?.competencia !== latestNetwork?.competencia ? (
        <p className="analysis-note">
          {current?.loja_nome} possui dados até {formatCompetence(current?.competencia)}; a rede
          possui movimento até {formatCompetence(latestNetwork?.competencia)}.
        </p>
      ) : null}

      <section className="evolution-kpis" aria-label="Medidas relevantes">
        <article>
          <span>Receita {current?.loja_nome}</span>
          <strong>{formatCurrency(current?.receita)}</strong>
          <small className={revenueDelta >= 0 ? "positive" : "negative"}>
            {revenueDelta === null ? "Primeira observação" : `${formatPercent(revenueDelta)} vs. mês anterior`}
          </small>
        </article>
        <article>
          <span>Meta atingida</span>
          <strong>{formatPercent(current?.meta_atingida_pct)}</strong>
          <small>Orçado {formatCurrency(current?.receita_orcada)}</small>
        </article>
        <article>
          <span>Forecast mensal</span>
          <strong>{formatCurrency(current?.forecast_mes)}</strong>
          <small>Competência {formatCompetence(current?.competencia)}</small>
        </article>
        <article>
          <span>EBITDA da rede</span>
          <strong>{formatCurrency(latestNetwork?.ebitda)}</strong>
          <small className={ebitdaDelta >= 0 ? "positive" : "negative"}>
            {ebitdaDelta === null ? "Primeira observação" : `${formatPercent(ebitdaDelta)} vs. mês anterior`}
          </small>
        </article>
        <article>
          <span>Cancelamento da rede</span>
          <strong>{formatPercent(latestNetwork?.cancelamento_pct)}</strong>
          <small>{formatCompetence(latestNetwork?.competencia)}</small>
        </article>
      </section>

      <section className="evolution-grid">
        <article className="panel all-stores-chart">
          <div className="panel-header">
            <div>
              <p className="eyebrow">Comparativo</p>
              <h2>{MEASURES[measure].label} por loja</h2>
            </div>
          </div>
          <LineChart
            ariaLabel={`${MEASURES[measure].label} mensal por loja`}
            series={storeLines}
            valueKey={measure}
            valueType={MEASURES[measure].type}
          />
        </article>

        <article className="panel focus-chart">
          <div className="panel-header">
            <div>
              <p className="eyebrow">Detalhe</p>
              <h2>{current?.loja_nome}</h2>
            </div>
          </div>
          <LineChart
            ariaLabel={`Receita mensal de ${current?.loja_nome}`}
            series={focusedSeries}
            valueKey="receita"
            valueType="currency"
          />
        </article>

        <article className="panel network-chart">
          <div className="panel-header">
            <div>
              <p className="eyebrow">Rede</p>
              <h2>EBITDA consolidado</h2>
            </div>
          </div>
          <LineChart
            ariaLabel="EBITDA mensal consolidado"
            series={[{ label: "Rede RetailCo", points: data.network }]}
            valueKey="ebitda"
            valueType="currency"
          />
        </article>
      </section>
    </div>
  );
}
