import { useState } from "react";

import { ErrorState, LoadingState } from "../components/Feedback";
import { Navigation } from "../components/Navigation";
import { useDataQuality } from "../hooks/useDataQuality";
import { formatNumber, formatPercent, formatTimestamp } from "../utils/format";

function fileName(path) {
  return String(path || "").split(/[\\/]/).pop() || "Arquivo não identificado";
}

function statusTone(status) {
  const normalized = String(status || "").toLowerCase();
  if (["success", "processed"].includes(normalized)) return "verde";
  if (["reprocessed"].includes(normalized)) return "amarelo";
  return "vermelho";
}

function approvalTone(value) {
  const rate = Number(value || 0);
  if (rate >= 98) return "positive";
  if (rate >= 95) return "attention-text";
  return "negative";
}

export function DataQualityPage() {
  const [days, setDays] = useState(14);
  const quality = useDataQuality(days);

  if (quality.loading && !quality.snapshot) return <LoadingState />;
  if (quality.error && !quality.snapshot) {
    return <ErrorState message={quality.error} onRetry={quality.refresh} />;
  }

  const { data, updated_at: updatedAt } = quality.snapshot;
  const latestDate = data.overview.ultima_data_referencia;

  return (
    <div className="dashboard-shell quality-shell">
      <Navigation active="quality" />
      <header className="topbar evolution-topbar">
        <div>
          <p className="eyebrow">Pipeline / Qualidade e rastreabilidade</p>
          <h1>Qualidade dos Dados</h1>
          <p className="hero-copy">
            Acompanhe arquivos processados, rejeições, execução das tarefas e cobertura de lojas
            para entender se os dados chegaram completos ao Data Warehouse.
          </p>
        </div>
        <div className="live-status" aria-label="Status da qualidade de dados">
          <span className={`signal ${quality.refreshing ? "pulse" : ""}`} />
          <div>
            <strong>{quality.refreshing ? "Atualizando auditoria" : "Auditoria atualizada"}</strong>
            <small>Última atualização: {formatTimestamp(updatedAt)}</small>
          </div>
        </div>
      </header>

      <section className="filters quality-filters" aria-label="Filtros de qualidade">
        <div>
          <label htmlFor="quality-days">Janela analisada</label>
          <select id="quality-days" value={days} onChange={(event) => setDays(Number(event.target.value))}>
            <option value={7}>7 dias</option>
            <option value={14}>14 dias</option>
            <option value={30}>30 dias</option>
            <option value={60}>60 dias</option>
            <option value={90}>90 dias</option>
          </select>
        </div>
        <p>
          Última data de movimento: {latestDate}. A visão cruza controle de arquivos, auditoria
          do pipeline e cobertura das lojas.
        </p>
        <button onClick={quality.refresh} type="button">Atualizar qualidade</button>
      </section>
      {quality.error ? <p className="inline-error">{quality.error}</p> : null}

      <section className="quality-kpis" aria-label="Resumo de qualidade">
        <article className="highlight">
          <span>Taxa de aprovação</span>
          <strong>{formatPercent(data.overview.taxa_aprovacao)}</strong>
          <small>{formatNumber(data.overview.registros_validos)} registros válidos</small>
        </article>
        <article>
          <span>Arquivos controlados</span>
          <strong>{formatNumber(data.overview.total_arquivos)}</strong>
          <small>{formatNumber(data.overview.reprocessados)} reprocessados</small>
        </article>
        <article>
          <span>Execuções auditadas</span>
          <strong>{formatNumber(data.overview.total_execucoes)}</strong>
          <small>{formatPercent(data.overview.taxa_sucesso_execucoes)} de sucesso</small>
        </article>
        <article>
          <span>Rejeições</span>
          <strong>{formatNumber(data.overview.total_rejeicoes)}</strong>
          <small>{formatNumber(data.overview.quarentenados)} arquivos em quarentena</small>
        </article>
        <article>
          <span>Duração média</span>
          <strong>{Number(data.overview.duracao_media_segundos || 0).toFixed(2)}s</strong>
          <small>Última execução: {formatTimestamp(data.overview.ultima_execucao)}</small>
        </article>
      </section>

      <section className="quality-alerts" aria-label="Alertas de qualidade">
        {data.alerts.map((alert) => (
          <article key={alert}>
            <span />
            <p>{alert}</p>
          </article>
        ))}
      </section>

      <section className="quality-grid">
        <article className="panel quality-daily-panel">
          <div className="panel-header">
            <div>
              <p className="eyebrow">Janela operacional</p>
              <h2>Qualidade por data</h2>
            </div>
          </div>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Data</th>
                  <th>Arquivos</th>
                  <th>Lojas</th>
                  <th>Lidos</th>
                  <th>Válidos</th>
                  <th>Inválidos</th>
                  <th>Aprovação</th>
                </tr>
              </thead>
              <tbody>
                {data.daily_quality.map((row) => (
                  <tr key={row.data_referencia}>
                    <td>{row.data_referencia}</td>
                    <td>{formatNumber(row.arquivos)}</td>
                    <td>{formatNumber(row.lojas)}</td>
                    <td>{formatNumber(row.registros_lidos)}</td>
                    <td>{formatNumber(row.registros_validos)}</td>
                    <td>{formatNumber(row.registros_invalidos)}</td>
                    <td className={approvalTone(row.taxa_aprovacao)}>{formatPercent(row.taxa_aprovacao)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </article>

        <article className="panel">
          <div className="panel-header">
            <div>
              <p className="eyebrow">Cobertura</p>
              <h2>Lojas na última data</h2>
            </div>
          </div>
          <div className="coverage-list">
            {data.coverage.map((store) => (
              <div key={store.loja_id} className="coverage-row">
                <div>
                  <strong>{store.loja_nome}</strong>
                  <small>{formatNumber(store.registros_validos)} registros válidos</small>
                </div>
                <span>{formatNumber(store.arquivos)} arquivos</span>
                <b className={approvalTone(store.taxa_aprovacao)}>{formatPercent(store.taxa_aprovacao)}</b>
              </div>
            ))}
          </div>
        </article>

        <article className="panel">
          <div className="panel-header">
            <div>
              <p className="eyebrow">Execuções</p>
              <h2>Tarefas auditadas</h2>
            </div>
          </div>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Tarefa</th>
                  <th>Status</th>
                  <th>Execuções</th>
                  <th>Lidos</th>
                  <th>Inseridos</th>
                  <th>Duração média</th>
                </tr>
              </thead>
              <tbody>
                {data.task_quality.map((row) => (
                  <tr key={`${row.task_id}-${row.status}`}>
                    <td>{row.task_id}</td>
                    <td><span className={`badge ${statusTone(row.status)}`}>{row.status}</span></td>
                    <td>{formatNumber(row.execucoes)}</td>
                    <td>{formatNumber(row.registros_lidos)}</td>
                    <td>{formatNumber(row.registros_inseridos)}</td>
                    <td>{Number(row.duracao_media_segundos || 0).toFixed(2)}s</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </article>

        <article className="panel">
          <div className="panel-header">
            <div>
              <p className="eyebrow">Rastreabilidade</p>
              <h2>Últimos arquivos</h2>
            </div>
          </div>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Arquivo</th>
                  <th>Loja</th>
                  <th>Data</th>
                  <th>Camada</th>
                  <th>Status</th>
                  <th>Registros</th>
                </tr>
              </thead>
              <tbody>
                {data.recent_files.map((file) => (
                  <tr key={file.file_id}>
                    <td className="raw-file-name">{fileName(file.file_path)}</td>
                    <td>{file.loja_nome}</td>
                    <td>{file.data_referencia}</td>
                    <td>{file.camada_destino}</td>
                    <td><span className={`badge ${statusTone(file.status)}`}>{file.status}</span></td>
                    <td>{formatNumber(file.registros_validos)} / {formatNumber(file.registros_lidos)}</td>
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
