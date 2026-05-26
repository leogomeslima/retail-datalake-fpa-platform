import { useEffect, useMemo, useState } from "react";

import { Navigation } from "../components/Navigation";
import { emitDailyClosing, emitShift, fetchPdvConfig, processPdvDate } from "../services/api";
import { formatCurrency, formatNumber } from "../utils/format";

function localToday() {
  const now = new Date();
  const local = new Date(now.getTime() - now.getTimezoneOffset() * 60000);
  return local.toISOString().slice(0, 10);
}

function StatusBadge({ status }) {
  return <span className={`sale-status ${status.toLowerCase()}`}>{status}</span>;
}

export function PdvPage() {
  const [config, setConfig] = useState({ lojas: [], produtos: [], turnos: [] });
  const [form, setForm] = useState({
    loja_id: "1",
    data: localToday(),
    turno: "MANHA",
    quantidade: "15",
    seed: String(Date.now()).slice(-8),
  });
  const [emission, setEmission] = useState(null);
  const [dailyClosing, setDailyClosing] = useState(null);
  const [processing, setProcessing] = useState(null);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    fetchPdvConfig()
      .then(setConfig)
      .catch((reason) => setError(reason.message));
  }, []);

  const store = useMemo(
    () => config.lojas.find((item) => item.loja_id === Number(form.loja_id)),
    [config.lojas, form.loja_id],
  );

  function change(event) {
    const { name, value } = event.target;
    setForm((current) => ({ ...current, [name]: value }));
  }

  async function issueShift(event) {
    event.preventDefault();
    setBusy("emitindo");
    setError("");
    setProcessing(null);
    setDailyClosing(null);
    try {
      const result = await emitShift({
        ...form,
        loja_id: Number(form.loja_id),
        quantidade: Number(form.quantidade),
        seed: Number(form.seed),
      });
      setEmission(result);
    } catch (reason) {
      setError(reason.message);
    } finally {
      setBusy("");
    }
  }

  async function issueDailyClosing() {
    setBusy("emitindo-dia");
    setError("");
    setEmission(null);
    setProcessing(null);
    try {
      const result = await emitDailyClosing({
        data: form.data,
        quantidade_por_turno: Number(form.quantidade),
        seed: Number(form.seed),
      });
      setDailyClosing(result);
      setProcessing(result.processamento);
    } catch (reason) {
      setError(reason.message);
    } finally {
      setBusy("");
    }
  }

  async function processDate() {
    setBusy("processando");
    setError("");
    try {
      const result = await processPdvDate(form.data);
      setProcessing(result);
    } catch (reason) {
      setError(reason.message);
    } finally {
      setBusy("");
    }
  }

  return (
    <div className="dashboard-shell pdv-shell">
      <Navigation active="pdv" />
      <header className="pdv-hero">
        <div>
          <p className="eyebrow">RetailCo S.A. / Terminal de loja</p>
          <h1>Operação PDV</h1>
          <p className="hero-copy">
            Simule fechamentos reais de turno, grave a camada Raw e envie a data para o
            processamento financeiro.
          </p>
        </div>
        <div className="terminal-state">
          <span className={`signal ${busy ? "pulse" : ""}`} />
          <div>
            <strong>{busy ? "Terminal em operação" : "Caixa disponível"}</strong>
            <small>{store ? `${store.loja_nome} / ${store.cidade}` : "Carregando lojas"}</small>
          </div>
        </div>
      </header>

      <section className="pdv-layout">
        <form className="panel pdv-form" onSubmit={issueShift}>
          <div className="panel-header">
            <div>
              <p className="eyebrow">Fechamento</p>
              <h2>Emitir turno</h2>
            </div>
          </div>
          <label>
            Loja
            <select name="loja_id" value={form.loja_id} onChange={change}>
              {config.lojas.map((item) => (
                <option value={item.loja_id} key={item.loja_id}>
                  {item.loja_nome} - {item.cidade}
                </option>
              ))}
            </select>
          </label>
          <div className="form-pair">
            <label>
              Data operacional
              <input name="data" type="date" value={form.data} onChange={change} required />
            </label>
            <label>
              Turno
              <select name="turno" value={form.turno} onChange={change}>
                {config.turnos.map((turno) => (
                  <option value={turno} key={turno}>
                    {turno}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <div className="form-pair">
            <label>
              Vendas no turno
              <input
                name="quantidade"
                type="number"
                min="1"
                max="150"
                value={form.quantidade}
                onChange={change}
                required
              />
            </label>
            <label>
              Semente da simulação
              <input name="seed" type="number" min="1" value={form.seed} onChange={change} required />
            </label>
          </div>
          <button className="primary-action" disabled={Boolean(busy)} type="submit">
            {busy === "emitindo" ? "Emitindo Raw..." : "Fechar turno e emitir Raw"}
          </button>
          <button
            className="general-closing-action"
            disabled={Boolean(busy)}
            onClick={issueDailyClosing}
            type="button"
          >
            {busy === "emitindo-dia"
              ? "Emitindo e carregando DW..."
              : "Fechar dia completo, emitir Raw e carregar DW"}
          </button>
          <button
            className="secondary-action"
            disabled={Boolean(busy)}
            onClick={processDate}
            type="button"
          >
            {busy === "processando" ? "Processando..." : "Processar data no DW"}
          </button>
          <p className="field-note">
            Cada loja aceita um arquivo por turno e data. Os arquivos emitidos sao imutaveis.
            O fechamento geral usa a quantidade informada em cada um dos 15 turnos e atualiza o DW.
          </p>
        </form>

        <article className="panel pdv-receipt">
          <div className="panel-header">
            <div>
              <p className="eyebrow">Resumo do caixa</p>
              <h2>
                {dailyClosing
                  ? "Fechamento geral do dia"
                  : emission
                    ? `${emission.loja_nome} / ${emission.turno}`
                    : "Aguardando emissão"}
              </h2>
            </div>
          </div>
          {dailyClosing ? (
            <>
              <div className="receipt-values">
                <div>
                  <span>Líquido emitido</span>
                  <strong>{formatCurrency(dailyClosing.totais.valor_liquido)}</strong>
                </div>
                <div>
                  <span>Arquivos Raw</span>
                  <strong>{formatNumber(dailyClosing.arquivos_raw)}</strong>
                </div>
                <div>
                  <span>Transações</span>
                  <strong>{formatNumber(dailyClosing.quantidade)}</strong>
                </div>
              </div>
              <div className="receipt-status">
                <span>Concluídas <b>{dailyClosing.totais.concluidas}</b></span>
                <span>Pendentes <b>{dailyClosing.totais.pendentes}</b></span>
                <span>Canceladas <b>{dailyClosing.totais.canceladas}</b></span>
              </div>
              <p className="raw-path">
                {dailyClosing.lojas} lojas x {dailyClosing.turnos_por_loja} turnos emitidos em Raw.
              </p>
            </>
          ) : emission ? (
            <>
              <div className="receipt-values">
                <div>
                  <span>Líquido emitido</span>
                  <strong>{formatCurrency(emission.totais.valor_liquido)}</strong>
                </div>
                <div>
                  <span>Descontos</span>
                  <strong>{formatCurrency(emission.totais.descontos)}</strong>
                </div>
                <div>
                  <span>Transações</span>
                  <strong>{formatNumber(emission.quantidade)}</strong>
                </div>
              </div>
              <div className="receipt-status">
                <span>Concluídas <b>{emission.totais.concluidas}</b></span>
                <span>Pendentes <b>{emission.totais.pendentes}</b></span>
                <span>Canceladas <b>{emission.totais.canceladas}</b></span>
              </div>
              <p className="raw-path">Raw: {emission.arquivo}</p>
            </>
          ) : (
            <p className="empty-state">
              Defina os parametros do terminal e emita um fechamento para visualizar os totais.
            </p>
          )}
          {processing ? (
            <div className="processing-result" aria-label="Resultado do processamento">
              <strong>Data carregada no DW</strong>
              <span>Run ID: {processing.run_id}</span>
              <span>
                Inseridos: {formatNumber(processing.registros_inseridos)} / Atualizados:{" "}
                {formatNumber(processing.registros_atualizados)}
              </span>
              <span>
                Válidos: {formatNumber(processing.registros_validos)} / Cancelados:{" "}
                {formatNumber(processing.registros_cancelados)}
              </span>
            </div>
          ) : null}
          {error ? <p className="inline-error pdv-error">{error}</p> : null}
        </article>
      </section>

      <article className="panel sales-journal">
        <div className="panel-header">
          <div>
            <p className="eyebrow">Transações</p>
            <h2>{dailyClosing ? "Arquivos do fechamento geral" : "Movimento do turno"}</h2>
          </div>
          {dailyClosing ? (
            <span className="journal-count">{dailyClosing.arquivos_raw} arquivos Raw</span>
          ) : emission ? (
            <span className="journal-count">{emission.quantidade} lançamentos</span>
          ) : null}
        </div>
        {dailyClosing ? (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Loja</th>
                  <th>Turno</th>
                  <th>Transações</th>
                  <th>Líquido emitido</th>
                  <th>Raw</th>
                </tr>
              </thead>
              <tbody>
                {dailyClosing.emissoes.map((closing) => (
                  <tr key={`${closing.loja_id}-${closing.turno}`}>
                    <td>{closing.loja_nome}</td>
                    <td>{closing.turno}</td>
                    <td>{formatNumber(closing.quantidade)}</td>
                    <td>{formatCurrency(closing.valor_liquido)}</td>
                    <td className="raw-file-name">{closing.arquivo.split(/[/\\]/).pop()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : emission ? (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>ID venda</th>
                  <th>Produto</th>
                  <th>Cliente</th>
                  <th>Pagamento</th>
                  <th>Valor</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {emission.vendas.map((sale) => (
                  <tr key={sale.id_venda}>
                    <td>{sale.id_venda}</td>
                    <td>{sale.produto_nome}</td>
                    <td>{sale.cliente_nome}</td>
                    <td>{sale.forma_pagamento}</td>
                    <td>{formatCurrency(sale.quantidade * sale.valor_unitario - sale.desconto_valor)}</td>
                    <td>
                      <StatusBadge status={sale.status} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="empty-state">Nenhuma transacao emitida neste terminal nesta sessao.</p>
        )}
      </article>
    </div>
  );
}
