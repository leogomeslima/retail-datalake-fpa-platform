const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api";

async function request(path, options) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!response.ok) {
    const detail = await response.json().catch(() => ({ detail: "Falha ao consultar API." }));
    throw new Error(detail.detail || "Falha ao consultar API.");
  }
  return response.json();
}

export function fetchCompetences() {
  return request("/competences");
}

export function fetchDashboard(competence) {
  const query = competence ? `?competencia=${encodeURIComponent(competence)}` : "";
  return request(`/dashboard${query}`);
}

export function fetchEvolution() {
  return request("/evolution");
}

export function fetchForecast(months, adjustmentPct) {
  const query = new URLSearchParams({
    months: String(months),
    adjustment_pct: String(adjustmentPct),
  });
  return request(`/forecast?${query.toString()}`);
}

export function fetchMlForecast(months) {
  const query = new URLSearchParams({ months: String(months) });
  return request(`/ml-forecast?${query.toString()}`);
}

export function fetchPdvConfig() {
  return request("/pdv/config");
}

export function emitShift(payload) {
  return request("/pdv/turnos", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function emitDailyClosing(payload) {
  return request("/pdv/fechamentos-gerais", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function processPdvDate(data) {
  return request("/pdv/processamentos", {
    method: "POST",
    body: JSON.stringify({ data }),
  });
}
