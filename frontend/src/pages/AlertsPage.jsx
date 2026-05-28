import { useState } from "react";

import { ErrorState, LoadingState } from "../components/Feedback";
import { Navigation } from "../components/Navigation";
import { useAlerts } from "../hooks/useAlerts";
import { formatCompetence, formatNumber, formatPercent, formatTimestamp } from "../utils/format";

const SEVERITIES = ["TODOS", "CRITICO", "ALTO", "MEDIO", "INFO"];
const TYPES = ["TODOS", "META", "RECEITA", "MARGEM", "CANCELAMENTO", "QUALIDADE", "PIPELINE", "FORECAST", "OPERACAO"];

function severityClass(severity) {
  return `severity-${String(severity || "info").toLowerCase()}`;
}

function metricLabel(alert) {
  if (alert.metric_value === null || alert.metric_value === undefined) return "Monitoramento";
  if (["META", "RECEITA", "MARGEM", "CANCELAMENTO", "FORECAST"].includes(alert.type)) {
    return formatPercent(alert.metric_value);
  }
  return formatNumber(alert.metric_value);
}

export function AlertsPage() {
  const [days, setDays] = useState(14);
  const [severity, setSeverity] = useState("TODOS");
  const [type, setType] = useState("TODOS");
  const alerts = useAlerts(days);

  if (alerts.loading && !alerts.snapshot) return <LoadingState />;
  if (alerts.error && !alerts.snapshot) {
    return <ErrorState message={alerts.error} onRetry={alerts.refresh} />;
  }

  const { data, updated_at: updatedAt } = alerts.snapshot;
  const filteredAlerts = data.alerts.filter((alert) => (
    (severity === "TODOS" || alert.severity === severity)
    && (type === "TODOS" || alert.type === type)
  ));

  return (
    <div className="dashboard-shell alerts-shell">
      <Navigation active="alerts" />
      <header className="topbar evolution-topbar">
        <div>
          <p className="eyebrow">Monitoramento inteligente</p>
          <h1>Central de Alertas</h1>
          <p className="hero-copy">
            Priorize desvios de meta, queda de receita, margem baixa, cancelamentos, falhas de pipeline,
            qualidade de arquivos e divergência entre forecast e previsão ML.
          </p>
        </div>
        <div className="live-status" aria-label="Status dos alertas">
          <span className={`signal ${alerts.refreshing ? "pulse" : ""}`} />
          <div>
            <strong>{alerts.refreshing ? "Reavaliando regras" : "Alertas atualizados"}</strong>
            <small>Última atualização: {formatTimestamp(updatedAt)}</small>
          </div>
        </div>
      </header>

      <section className="filters alerts-filters" aria-label="Filtros de alertas">
        <div>
          <label htmlFor="alerts-days">Janela de qualidade</label>
          <select id="alerts-days" value={days} onChange={(event) => setDays(Number(event.target.value))}>
            <option value={7}>7 dias</option>
            <option value={14}>14 dias</option>
            <option value={30}>30 dias</option>
            <option value={60}>60 dias</option>
            <option value={90}>90 dias</option>
          </select>
        </div>
        <div>
          <label htmlFor="alerts-severity">Severidade</label>
          <select id="alerts-severity" value={severity} onChange={(event) => setSeverity(event.target.value)}>
            {SEVERITIES.map((item) => <option key={item} value={item}>{item}</option>)}
          </select>
        </div>
        <div>
          <label htmlFor="alerts-type">Tipo</label>
          <select id="alerts-type" value={type} onChange={(event) => setType(event.target.value)}>
            {TYPES.map((item) => <option key={item} value={item}>{item}</option>)}
          </select>
        </div>
        <p>Competência analisada: {formatCompetence(data.latest_competence)}.</p>
        <button onClick={alerts.refresh} type="button">Atualizar alertas</button>
      </section>
      {alerts.error ? <p className="inline-error">{alerts.error}</p> : null}

      <section className="alerts-kpis" aria-label="Resumo dos alertas">
        <article className="critical">
          <span>Críticos</span>
          <strong>{formatNumber(data.summary.CRITICO)}</strong>
          <small>Exigem ação imediata</small>
        </article>
        <article>
          <span>Altos</span>
          <strong>{formatNumber(data.summary.ALTO)}</strong>
          <small>Prioridade operacional</small>
        </article>
        <article>
          <span>Médios</span>
          <strong>{formatNumber(data.summary.MEDIO)}</strong>
          <small>Acompanhar tendência</small>
        </article>
        <article>
          <span>Informativos</span>
          <strong>{formatNumber(data.summary.INFO)}</strong>
          <small>Sem ação urgente</small>
        </article>
        <article>
          <span>Exibidos</span>
          <strong>{formatNumber(filteredAlerts.length)}</strong>
          <small>{formatNumber(data.total)} alertas totais</small>
        </article>
      </section>

      <section className="alerts-grid">
        <article className="panel alerts-list-panel">
          <div className="panel-header">
            <div>
              <p className="eyebrow">Fila de atenção</p>
              <h2>Alertas acionáveis</h2>
            </div>
          </div>
          <div className="alerts-list">
            {filteredAlerts.map((alert) => (
              <a className={`alert-card ${severityClass(alert.severity)}`} href={alert.route} key={alert.id}>
                <div>
                  <span className="alert-type">{alert.type}</span>
                  <span className="alert-severity">{alert.severity}</span>
                </div>
                <section>
                  <h3>{alert.title}</h3>
                  <p>{alert.description}</p>
                  <small>{alert.action}</small>
                </section>
                <aside>
                  <strong>{metricLabel(alert)}</strong>
                  <span>{alert.threshold || alert.entity}</span>
                </aside>
              </a>
            ))}
          </div>
        </article>

        <article className="panel alerts-rules-panel">
          <div className="panel-header">
            <div>
              <p className="eyebrow">Regras</p>
              <h2>Como os alertas são gerados</h2>
            </div>
          </div>
          <div className="rules-list">
            {data.rules.map((rule) => (
              <p key={rule}>{rule}</p>
            ))}
          </div>
        </article>
      </section>
    </div>
  );
}
