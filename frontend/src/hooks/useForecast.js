import { useCallback, useEffect, useState } from "react";

import { fetchForecast } from "../services/api";

const REFRESH_INTERVAL = 15000;

export function useForecast(months, adjustmentPct) {
  const [snapshot, setSnapshot] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");

  const refresh = useCallback(async () => {
    setRefreshing(true);
    setError("");
    try {
      setSnapshot(await fetchForecast(months, adjustmentPct));
    } catch (reason) {
      setError(reason.message);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [adjustmentPct, months]);

  useEffect(() => {
    refresh();
    const timer = window.setInterval(refresh, REFRESH_INTERVAL);
    return () => window.clearInterval(timer);
  }, [refresh]);

  return { snapshot, loading, refreshing, error, refresh };
}
