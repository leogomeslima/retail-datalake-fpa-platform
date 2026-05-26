import { formatCurrency } from "../utils/format";

export function RevenueTrend({ trend }) {
  const maximum = Math.max(...trend.map((item) => item.receita_liquida), 1);
  return (
    <article className="panel trend-panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Evolução</p>
          <h2>Receita líquida mensal</h2>
        </div>
      </div>
      <div className="bars" aria-label="Grafico de receita líquida mensal">
        {trend.map((item) => (
          <div className="bar-group" key={`${item.ano}-${item.mes}`}>
            <span className="bar-value">{formatCurrency(item.receita_liquida)}</span>
            <div
              className="bar"
              style={{ height: `${Math.max((item.receita_liquida / maximum) * 168, 12)}px` }}
            />
            <small>
              {String(item.mes).padStart(2, "0")}/{item.ano}
            </small>
          </div>
        ))}
      </div>
    </article>
  );
}

