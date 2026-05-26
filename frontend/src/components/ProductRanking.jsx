import { formatCurrency, formatNumber } from "../utils/format";

export function ProductRanking({ products }) {
  const maximum = Math.max(...products.map((product) => product.receita), 1);
  return (
    <article className="panel products-panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Sortimento</p>
          <h2>Top produtos</h2>
        </div>
      </div>
      <div className="ranking">
        {products.slice(0, 6).map((product) => (
          <div className="rank-item" key={product.produto_nome}>
            <div>
              <strong>{product.produto_nome}</strong>
              <small>
                {product.categoria} / {formatNumber(product.volume)} itens
              </small>
            </div>
            <span>{formatCurrency(product.receita)}</span>
            <div className="meter">
              <i style={{ width: `${(product.receita / maximum) * 100}%` }} />
            </div>
          </div>
        ))}
      </div>
    </article>
  );
}

