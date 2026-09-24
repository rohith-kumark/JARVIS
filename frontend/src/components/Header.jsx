import React from 'react';
import { Activity, Cpu, Shield, Radio, Wrench } from 'lucide-react';

export function Header({
  connectionStatus,
  llmProvider,
  toolsCount,
  onOpenTools,
  onOpenHealth,
  showHealthCard,
}) {
  const getStatusBadge = () => {
    switch (connectionStatus) {
      case 'connected':
        return {
          label: 'ONLINE',
          color: 'status-connected',
          icon: <Radio className="status-icon pulse-slow" size={14} />,
        };
      case 'connecting':
      case 'reconnecting':
        return {
          label: 'LINKING...',
          color: 'status-warning',
          icon: <Activity className="status-icon spin" size={14} />,
        };
      default:
        return {
          label: 'OFFLINE',
          color: 'status-disconnected',
          icon: <Radio className="status-icon" size={14} />,
        };
    }
  };

  const status = getStatusBadge();

  return (
    <header className="app-header">
      <div className="header-brand">
        <div className="reactor-core">
          <div className="reactor-pulse"></div>
        </div>
        <div className="brand-text">
          <h1 className="brand-title">J.A.R.V.I.S.</h1>
          <span className="brand-sub">Modular Cognitive Assistant</span>
        </div>
      </div>

      <div className="header-center-info">
        <div className="info-chip">
          <Cpu size={14} className="chip-icon" />
          <span className="chip-label">Reasoning:</span>
          <span className="chip-value">{llmProvider ? llmProvider.toUpperCase() : 'INITIALIZING'}</span>
        </div>

        <button
          className={`info-chip interactive-chip ${showHealthCard ? 'active' : ''}`}
          onClick={onOpenHealth}
          title="Toggle System Health Telemetry"
        >
          <Activity size={14} className="chip-icon" />
          <span className="chip-label">Diagnostics</span>
        </button>

        <button
          className="info-chip interactive-chip"
          onClick={onOpenTools}
          title="Open Tool Registry"
        >
          <Wrench size={14} className="chip-icon" />
          <span className="chip-label">Tools:</span>
          <span className="chip-badge">{toolsCount ?? 0}</span>
        </button>
      </div>

      <div className="header-status">
        <div className={`connection-pill ${status.color}`}>
          {status.icon}
          <span className="status-label">{status.label}</span>
        </div>
      </div>
    </header>
  );
}

export default Header;
