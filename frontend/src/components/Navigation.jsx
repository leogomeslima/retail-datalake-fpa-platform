export function Navigation({ active }) {
  return (
    <nav className="module-navigation" aria-label="Módulos RetailCo">
      <a className={active === "dashboard" ? "active" : ""} href="/">
        Indicadores FP&A
      </a>
      <a className={active === "evolution" ? "active" : ""} href="/evolucao">
        Evolução de Lojas
      </a>
      <a className={active === "store" ? "active" : ""} href="/lojas/1">
        Detalhe da Loja
      </a>
      <a className={active === "forecast" ? "active" : ""} href="/forecast">
        Ajuste de Forecast
      </a>
      <a className={active === "ml" ? "active" : ""} href="/previsao-ml">
        Previsão ML
      </a>
      <a className={active === "quality" ? "active" : ""} href="/qualidade">
        Qualidade
      </a>
      <a className={active === "alerts" ? "active" : ""} href="/alertas">
        Alertas
      </a>
      <a className={active === "pdv" ? "active" : ""} href="/pdv">
        Operação PDV
      </a>
    </nav>
  );
}
