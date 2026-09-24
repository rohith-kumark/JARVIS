import React, { useEffect, useState } from "react";
import { api } from "../services/api";

export default function MemoryModal({ isOpen, onClose, currentConvId }) {
  const [memoryData, setMemoryData] = useState({ memories: [], preferences: {} });
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (isOpen) {
      loadMemory();
    }
  }, [isOpen, currentConvId]);

  const loadMemory = async () => {
    setLoading(true);
    try {
      const data = await api.getMemory(currentConvId);
      setMemoryData(data);
    } catch (err) {
      console.error("Failed to load memory data:", err);
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div className="modal-title">CORE MEMORY & SYSTEM PREFERENCES</div>
          <button className="modal-close-btn" onClick={onClose}>&times;</button>
        </div>

        <div className="modal-body">
          {loading ? (
            <div style={{ color: "var(--cyan-primary)", fontFamily: "var(--font-hud)" }}>
              ACCESSING STORAGE MATRICES...
            </div>
          ) : (
            <>
              <div>
                <h4 style={{ color: "var(--cyan-primary)", marginBottom: "8px", fontFamily: "var(--font-hud)" }}>
                  SHORT-TERM MEMORIES ({memoryData.memories?.length || 0})
                </h4>
                {memoryData.memories?.length === 0 ? (
                  <p style={{ color: "var(--text-muted)" }}>No contextual memories recorded in current scope.</p>
                ) : (
                  <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                    {memoryData.memories.map((m) => (
                      <div
                        key={m.id}
                        style={{
                          background: "rgba(0, 0, 0, 0.4)",
                          padding: "8px 12px",
                          borderRadius: "4px",
                          border: "1px solid var(--cyan-dim)",
                          fontFamily: "var(--font-mono)",
                        }}
                      >
                        <div style={{ color: "var(--cyan-primary)", fontWeight: "600" }}>{m.key}</div>
                        <div style={{ color: "var(--text-primary)", marginTop: "2px" }}>{m.value}</div>
                        <div style={{ color: "var(--text-muted)", fontSize: "0.7rem", marginTop: "4px" }}>
                          Type: {m.memory_type} &bull; Scope: {m.conversation_id ? m.conversation_id.slice(0, 8) : "Global"}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <div style={{ marginTop: "12px" }}>
                <h4 style={{ color: "var(--cyan-primary)", marginBottom: "8px", fontFamily: "var(--font-hud)" }}>
                  USER PREFERENCES
                </h4>
                {Object.keys(memoryData.preferences || {}).length === 0 ? (
                  <p style={{ color: "var(--text-muted)" }}>No user preferences stored.</p>
                ) : (
                  <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                    {Object.entries(memoryData.preferences).map(([k, v]) => (
                      <div
                        key={k}
                        style={{
                          display: "flex",
                          justifyContent: "space-between",
                          background: "rgba(0, 0, 0, 0.4)",
                          padding: "6px 12px",
                          borderRadius: "4px",
                          border: "1px solid rgba(255, 255, 255, 0.05)",
                          fontFamily: "var(--font-mono)",
                        }}
                      >
                        <span style={{ color: "var(--cyan-primary)" }}>{k}</span>
                        <span style={{ color: "var(--text-primary)" }}>{v}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
