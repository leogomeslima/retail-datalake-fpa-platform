const currency = new Intl.NumberFormat("pt-BR", {
  style: "currency",
  currency: "BRL",
  maximumFractionDigits: 0,
});

const integer = new Intl.NumberFormat("pt-BR");

export function formatCurrency(value) {
  return currency.format(Number(value || 0));
}

export function formatNumber(value) {
  return integer.format(Number(value || 0));
}

export function formatPercent(value) {
  return `${Number(value || 0).toFixed(1).replace(".", ",")}%`;
}

export function formatCompetence(value) {
  const [year, month] = value.split("-");
  return new Intl.DateTimeFormat("pt-BR", { month: "long", year: "numeric" }).format(
    new Date(Number(year), Number(month) - 1, 1),
  );
}

export function formatTimestamp(value) {
  if (!value) return "Sem execução";
  return new Intl.DateTimeFormat("pt-BR", {
    dateStyle: "short",
    timeStyle: "medium",
  }).format(new Date(value));
}
