import React from "react";

export default function Header({
  health,
  onToggleSidebar,
  onOpenMemory,
}) {
  const isOnline = health?.status === "ok";

  return (
    <header className="jarvis-header">
      <div className="brand-section">
        <button
          className="btn-hud"
          style={{ display: "none", padding: "6px" }}
          id="mobile-toggle"
          onClick={onToggleSidebar}
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <line x1="3" y1="12" x2="21" y2="12"></line>
            <line x1="3" y1="6" x2="21" y2="6"></line>
            <line x1="3" y1="18" x2="21" y2="18"></line>
          </svg>
        </button>

        <div className="hud-arc-reactor">
          <div className="hud-arc-inner"></div>
        </div>

        <div>
          <div className="brand-title">J.A.R.V.I.S.</div>
          <div className="brand-subtitle">Personal AI Assistant &bull; Mark I</div>
        </div>
      </div>

      <div className="system-status-bar">
        {/* Backend & DB Status */}
        <div className="status-pill" title={`Database: ${health?.database || "Checking"}`}>
          <div className={`status-dot ${isOnline ? "online" : "offline"}`}></div>
          <span>{isOnline ? "CORE ONLINE" : "DISCONNECTED"}</span>
        </div>

        {/* Model */}
        {health?.model && (
          <div className="status-pill" title={`Provider: ${health.llm_provider}`}>
            <span style={{ color: "var(--cyan-primary)" }}>MODEL:</span>
            <span>{health.model}</span>
          </div>
        )}

        {/* Tools Count */}
        {health?.tools_count !== undefined && (
          <div className="status-pill" title={health.registered_tools?.join(", ")}>
            <span style={{ color: "var(--cyan-primary)" }}>TOOLS:</span>
            <span>{health.tools_count} ARMED</span>
          </div>
        )}

        {/* Memory View Button */}
        <button className="btn-hud" onClick={onOpenMemory} title="Inspect active memory and preferences">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"></path>
            <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"></path>
          </svg>
          <span>MEMORY HUD</span>
        </button>
      </div>
    </header>
  );
}
