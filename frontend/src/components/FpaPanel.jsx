import { formatCurrency, formatPercent } from "../utils/format";

export function FpaPanel({ fpa }) {
  return (
    <article className="panel fpa-panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">FP&A</p>
          <h2>Forecast e meta</h2>
        </div>
      </div>
      <div className="fpa-list">
        {fpa.map((store) => (
          <div key={store.loja_id} className="fpa-row">
            <strong>{store.loja_nome}</strong>
            <div>
              <span>Meta atingida</span>
              <b>{formatPercent(store.meta_atingida_pct)}</b>
            </div>
            <div>
              <span>Forecast</span>
              <b>{formatCurrency(store.forecast_mes)}</b>
            </div>
          </div>
        ))}
      </div>
    </article>
  );
}

