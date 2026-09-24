import React, { useState } from "react";

export default function MessageItem({ message }) {
  const isUser = message.role === "user";
  const [showToolDetails, setShowToolDetails] = useState(false);

  // Parse tool calls and saved memories if present in metadata or passed directly
  let toolCalls = message.tool_calls || [];
  let savedMemories = message.saved_memories || [];

  if (message.metadata_json) {
    try {
      const parsed = JSON.parse(message.metadata_json);
      if (!toolCalls.length && parsed.tool_calls) {
        toolCalls = parsed.tool_calls;
      }
      if (!savedMemories.length && parsed.saved_memories) {
        savedMemories = parsed.saved_memories;
      }
    } catch {
      // Ignore JSON parse errors
    }
  }

  const formatTime = (isoString) => {
    if (!isoString) return "";
    try {
      const date = new Date(isoString);
      return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
    } catch {
      return "";
    }
  };

  return (
    <div className={`message-row ${isUser ? "user" : "assistant"}`}>
      <div className="message-bubble">
        <div className="message-sender">
          {isUser ? (
            <>
              <span>OPERATOR</span>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
                <circle cx="12" cy="7" r="4"></circle>
              </svg>
            </>
          ) : (
            <>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="10"></circle>
                <path d="m9 12 2 2 4-4"></path>
              </svg>
              <span>J.A.R.V.I.S.</span>
            </>
          )}
        </div>

        <div className="message-content">{message.content}</div>

        {/* Subtle Memory Indicator */}
        {savedMemories && savedMemories.length > 0 && (
          <div
            style={{
              marginTop: "8px",
              display: "inline-flex",
              alignItems: "center",
              gap: "6px",
              background: "rgba(0, 229, 255, 0.1)",
              border: "1px solid rgba(0, 229, 255, 0.3)",
              borderRadius: "14px",
              padding: "3px 10px",
              fontSize: "0.74rem",
              color: "var(--cyan-primary)",
              fontFamily: "var(--font-hud)",
              letterSpacing: "0.5px",
            }}
          >
            <span>🧠 Memory saved:</span>
            <span style={{ color: "#e2e8f0", fontFamily: "var(--font-sans)", fontWeight: 400 }}>
              {savedMemories.map((m) => m.content).join("; ")}
            </span>
          </div>
        )}

        {/* Display Tool Calling Badges */}
        {toolCalls && toolCalls.length > 0 && (
          <div className="tool-execution-badge">
            <div
              className="tool-badge-header"
              onClick={() => setShowToolDetails(!showToolDetails)}
              title="Click to toggle execution details"
            >
              <div className="tool-name-tag">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"></path>
                </svg>
                <span>Tool Executed: {toolCalls.map((t) => t.tool_name).join(", ")}</span>
              </div>
              <div className={`tool-status-tag ${toolCalls[0].status === "error" ? "error" : ""}`}>
                {toolCalls[0].status.toUpperCase()} ({toolCalls[0].execution_time_ms}ms) {showToolDetails ? "▲" : "▼"}
              </div>
            </div>

            {showToolDetails && (
              <div className="tool-badge-body">
                {toolCalls.map((t, idx) => (
                  <div key={idx} className="tool-call-record">
                    <div className="tool-detail-row">
                      <span className="tool-detail-label">Arguments:</span>
                      <code>{JSON.stringify(t.arguments)}</code>
                    </div>
                    <div className="tool-detail-row">
                      <span className="tool-detail-label">Result:</span>
                      <code>{JSON.stringify(t.result)}</code>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {message.created_at && (
          <div className="message-time">{formatTime(message.created_at)}</div>
        )}
      </div>
    </div>
  );
}
