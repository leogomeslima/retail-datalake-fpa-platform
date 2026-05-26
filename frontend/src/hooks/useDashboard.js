import { useCallback, useEffect, useState } from "react";

import { fetchCompetences, fetchDashboard } from "../services/api";

const REFRESH_INTERVAL = 15000;

export function useDashboard() {
  const [competences, setCompetences] = useState([]);
  const [selected, setSelected] = useState(null);
  const [snapshot, setSnapshot] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchCompetences()
      .then(({ items }) => {
        setCompetences(items);
        setSelected(items[0] || null);
      })
      .catch((reason) => {
        setError(reason.message);
        setLoading(false);
      });
  }, []);

  const loadDashboard = useCallback(
    async (background = false) => {
      if (!selected) return;
      background ? setRefreshing(true) : setLoading(true);
      try {
        const result = await fetchDashboard(selected);
        setSnapshot(result);
        setError(null);
      } catch (reason) {
        setError(reason.message);
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [selected],
  );

  useEffect(() => {
    loadDashboard();
    const interval = window.setInterval(() => loadDashboard(true), REFRESH_INTERVAL);
    return () => window.clearInterval(interval);
  }, [loadDashboard]);

  return {
    competences,
    selected,
    setSelected,
    snapshot,
    loading,
    refreshing,
    error,
    refresh: () => loadDashboard(true),
  };
}

