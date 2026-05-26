import { ErrorState, LoadingState } from "../components/Feedback";
import { Filters } from "../components/Filters";
import { FpaPanel } from "../components/FpaPanel";
import { Header } from "../components/Header";
import { KpiCard } from "../components/KpiCard";
import { Navigation } from "../components/Navigation";
import { OperationsPanel } from "../components/OperationsPanel";
import { ProductRanking } from "../components/ProductRanking";
import { RevenueTrend } from "../components/RevenueTrend";
import { StoresTable } from "../components/StoresTable";
import { useDashboard } from "../hooks/useDashboard";
import { formatCurrency, formatNumber, formatPercent } from "../utils/format";

export function DashboardPage() {
  const dashboard = useDashboard();
  if (dashboard.loading && !dashboard.snapshot) return <LoadingState />;
  if (dashboard.error && !dashboard.snapshot) {
    return <ErrorState message={dashboard.error} onRetry={dashboard.refresh} />;
  }

  const { data, updated_at: updatedAt } = dashboard.snapshot;
  const marginPct =
    data.overview.receita_liquida > 0
      ? (data.overview.margem_bruta / data.overview.receita_liquida) * 100
      : 0;

  return (
    <div className="dashboard-shell">
      <Navigation active="dashboard" />
      <Header updatedAt={updatedAt} refreshing={dashboard.refreshing} />
      <Filters
        competences={dashboard.competences}
        selected={dashboard.selected}
        onSelect={dashboard.setSelected}
        onRefresh={dashboard.refresh}
      />
      {dashboard.error ? <p className="inline-error">{dashboard.error}</p> : null}
      <section className="kpi-grid" aria-label="Indicadores principais">
        <KpiCard
          label="Receita líquida"
          value={formatCurrency(data.overview.receita_liquida)}
          detail={`Bruta ${formatCurrency(data.overview.receita_bruta)}`}
          tone="revenue"
        />
        <KpiCard
          label="EBITDA"
          value={formatCurrency(data.dre.ebitda)}
          detail={`Margem ${formatPercent(data.dre.margem_ebitda_pct)}`}
          tone="profit"
        />
        <KpiCard
          label="Ticket médio"
          value={formatCurrency(data.overview.ticket_medio)}
          detail={`${formatNumber(data.overview.pedidos)} pedidos concluídos`}
        />
        <KpiCard
          label="Margem bruta"
          value={formatPercent(marginPct)}
          detail={formatCurrency(data.overview.margem_bruta)}
        />
        <KpiCard
          label="Pendentes / canceladas"
          value={`${formatNumber(data.overview.pendentes)} / ${formatNumber(data.overview.canceladas)}`}
          detail="Monitoramento operacional"
          tone="attention"
        />
      </section>
      <section className="main-grid">
        <RevenueTrend trend={data.trend} />
        <ProductRanking products={data.products} />
        <StoresTable stores={data.stores} />
        <FpaPanel fpa={data.fpa} />
        <OperationsPanel pipeline={data.pipeline} channels={data.channels} />
      </section>
    </div>
  );
}
