import { formatTimestamp } from "../utils/format";

export function Header({ updatedAt, refreshing }) {
  return (
    <header className="topbar">
      <div>
        <p className="eyebrow">RetailCo S.A. / Planejamento e Análise Financeira</p>
        <h1>Painel de Indicadores</h1>
      </div>
      <div className="live-status" aria-label="Status da atualização">
        <span className={`signal ${refreshing ? "pulse" : ""}`} />
        <div>
          <strong>{refreshing ? "Atualizando" : "Dados ativos"}</strong>
          <small>Última atualização: {formatTimestamp(updatedAt)}</small>
        </div>
      </div>
    </header>
  );
}
