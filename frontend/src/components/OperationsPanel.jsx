import { formatCurrency, formatNumber, formatTimestamp } from "../utils/format";

export function OperationsPanel({ pipeline, channels }) {
  return (
    <article className="panel operations-panel">
      <div className="panel-header">
        <div>
          <p className="eyebrow">Operação</p>
          <h2>Pipeline e canais</h2>
        </div>
      </div>
      <div className="pipeline-stats">
        <div>
          <span>Arquivos tratados</span>
          <strong>{formatNumber(pipeline.arquivos_processados)}</strong>
        </div>
        <div>
          <span>Fatos no DW</span>
          <strong>{formatNumber(pipeline.fatos_carregados)}</strong>
        </div>
        <div>
          <span>Falhas</span>
          <strong className={pipeline.falhas ? "negative" : "positive"}>
            {formatNumber(pipeline.falhas)}
          </strong>
        </div>
      </div>
      <p className="audit-time">Auditoria: {formatTimestamp(pipeline.ultima_execucao)}</p>
      <div className="channels">
        {channels.map((channel) => (
          <div key={channel.canal_venda}>
            <span>{channel.canal_venda}</span>
            <strong>{formatCurrency(channel.receita)}</strong>
            <small>{formatNumber(channel.pedidos)} pedidos</small>
          </div>
        ))}
      </div>
    </article>
  );
}
