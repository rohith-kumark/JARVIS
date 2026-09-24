import React from 'react';
import { Activity, Server, Clock, ShieldCheck, RefreshCw, X } from 'lucide-react';

export function StatusCard({ health, isLoading, error, onRefresh, onClose }) {
  const formatUptime = (seconds) => {
    if (!seconds && seconds !== 0) return 'N/A';
    const hrs = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    if (hrs > 0) return `${hrs}h ${mins}m ${secs}s`;
    if (mins > 0) return `${mins}m ${secs}s`;
    return `${secs}s`;
  };

  return (
    <div className="telemetry-panel">
      <div className="telemetry-header">
        <div className="telemetry-title">
          <Activity size={16} className="text-cyan" />
          <span>System Health & Diagnostics</span>
        </div>
        <div className="telemetry-actions">
          <button
            className="icon-btn"
            onClick={onRefresh}
            disabled={isLoading}
            title="Refresh Telemetry"
          >
            <RefreshCw size={14} className={isLoading ? 'spin' : ''} />
          </button>
          <button className="icon-btn" onClick={onClose} title="Close Diagnostics">
            <X size={14} />
          </button>
        </div>
      </div>

      {error ? (
        <div className="telemetry-error">
          <span>Backend Unreachable: {error}</span>
        </div>
      ) : (
        <div className="telemetry-grid">
          <div className="telemetry-metric">
            <span className="metric-label">Status</span>
            <span className={`metric-value ${health?.status === 'ok' ? 'text-green' : 'text-yellow'}`}>
              {health?.status ? health.status.toUpperCase() : 'UNKNOWN'}
            </span>
          </div>

          <div className="telemetry-metric">
            <span className="metric-label">Uptime</span>
            <span className="metric-value font-mono">
              {formatUptime(health?.uptime_seconds)}
            </span>
          </div>

          <div className="telemetry-metric">
            <span className="metric-label">Environment</span>
            <span className="metric-value">{health?.environment || 'development'}</span>
          </div>

          <div className="telemetry-metric">
            <span className="metric-label">Active Core</span>
            <span className="metric-value text-cyan">
              {health?.llm_provider ? health.llm_provider.toUpperCase() : 'N/A'}
            </span>
          </div>

          <div className="telemetry-metric">
            <span className="metric-label">Registered Tools</span>
            <span className="metric-value font-mono text-cyan">
              {health?.tools_registered_count ?? 0}
            </span>
          </div>

          <div className="telemetry-metric">
            <span className="metric-label">Core Version</span>
            <span className="metric-value font-mono">v{health?.version || '0.1.0'}</span>
          </div>
        </div>
      )}
    </div>
  );
}

export default StatusCard;
