import { formatCurrency, formatPercent } from "../utils/format";

export function StoresTable({ stores }) {
  return (
    <article className="panel stores-panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Desempenho por unidade</p>
          <h2>Ranking de lojas</h2>
        </div>
      </div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Loja</th>
              <th>Receita</th>
              <th>Share</th>
              <th>Vs. meta</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {stores.map((store) => (
              <tr key={store.loja_id}>
                <td>
                  <a className="store-link" href={`/lojas/${store.loja_id}`}>
                    <b>#{store.ranking}</b> {store.loja_nome}
                  </a>
                </td>
                <td>{formatCurrency(store.faturamento)}</td>
                <td>{formatPercent(store.market_share_pct)}</td>
                <td className={store.variacao_pct >= 0 ? "positive" : "negative"}>
                  {formatPercent(store.variacao_pct)}
                </td>
                <td>
                  <span className={`badge ${store.status_semaforo.toLowerCase()}`}>
                    {store.status_semaforo}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </article>
  );
}
