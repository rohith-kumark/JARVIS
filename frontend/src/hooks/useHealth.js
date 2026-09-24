import { useState, useEffect, useCallback } from 'react';
import { agentService } from '../services/agentService';

export function useHealth(pollIntervalMs = 10000) {
  const [health, setHealth] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchHealth = useCallback(async () => {
    try {
      const data = await agentService.checkHealth();
      setHealth(data);
      setError(null);
    } catch (err) {
      setError(err.message || 'Health check unreachable');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchHealth();
    if (pollIntervalMs > 0) {
      const timer = setInterval(fetchHealth, pollIntervalMs);
      return () => clearInterval(timer);
    }
  }, [fetchHealth, pollIntervalMs]);

  return {
    health,
    isLoading,
    error,
    isHealthy: health?.status === 'ok',
    refreshHealth: fetchHealth,
  };
}
