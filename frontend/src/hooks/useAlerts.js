import { useCallback, useEffect, useState } from "react";

import { fetchAlerts } from "../services/api";

const REFRESH_INTERVAL = 15000;

export function useAlerts(days) {
  const [snapshot, setSnapshot] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");

  const refresh = useCallback(async () => {
    setRefreshing(true);
    setError("");
    try {
      setSnapshot(await fetchAlerts(days));
    } catch (reason) {
      setError(reason.message);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [days]);

  useEffect(() => {
    refresh();
    const timer = window.setInterval(refresh, REFRESH_INTERVAL);
    return () => window.clearInterval(timer);
  }, [refresh]);

  return { snapshot, loading, refreshing, error, refresh };
}
