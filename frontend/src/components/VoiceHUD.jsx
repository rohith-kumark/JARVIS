import React from "react";

export default function VoiceHUD({
  voiceState,
  voiceName,
  supportedVoices,
  onSelectVoice,
  onToggleVoice,
  onInterrupt,
  errorMessage,
}) {
  const isListening = voiceState === "LISTENING";
  const isSpeaking = voiceState === "SPEAKING";
  const isThinking = voiceState === "THINKING";
  const isConnecting = voiceState === "CONNECTING";
  const isError = voiceState === "ERROR";
  const isActive = isListening || isSpeaking || isThinking || isConnecting;

  const getStateBadge = () => {
    switch (voiceState) {
      case "CONNECTING":
        return { text: "CONNECTING...", color: "#facc15", icon: "🟡" };
      case "LISTENING":
        return { text: "LISTENING...", color: "var(--cyan-primary)", icon: "🎤" };
      case "THINKING":
        return { text: "THINKING...", color: "#a855f7", icon: "🧠" };
      case "SPEAKING":
        return { text: "JARVIS SPEAKING...", color: "#22c55e", icon: "🔊" };
      case "INTERRUPTED":
        return { text: "INTERRUPTED", color: "#f97316", icon: "⚡" };
      case "ERROR":
        return { text: "VOICE UNAVAILABLE", color: "#ef4444", icon: "⚠️" };
      case "DISCONNECTED":
      case "IDLE":
      default:
        return { text: "VOICE READY", color: "#64748b", icon: "🎙️" };
    }
  };

  const badge = getStateBadge();

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "6px 14px",
        background: isActive
          ? "linear-gradient(90deg, rgba(0, 229, 255, 0.08) 0%, rgba(13, 22, 35, 0.95) 100%)"
          : "rgba(13, 22, 35, 0.6)",
        border: isActive ? "1px solid rgba(0, 229, 255, 0.35)" : "1px solid rgba(0, 229, 255, 0.15)",
        borderRadius: "8px",
        marginBottom: "8px",
        transition: "all 0.3s ease",
        fontFamily: "var(--font-hud)",
        fontSize: "0.8rem",
        letterSpacing: "0.5px",
      }}
    >
      {/* State & Visualizer */}
      <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
        <button
          onClick={onToggleVoice}
          title={isActive ? "Halt Voice Session" : "Initiate Real-Time Voice Session"}
          style={{
            background: isActive ? "rgba(0, 229, 255, 0.2)" : "rgba(255, 255, 255, 0.05)",
            border: `1px solid ${badge.color}`,
            borderRadius: "50%",
            width: "32px",
            height: "32px",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            cursor: "pointer",
            color: badge.color,
            boxShadow: isActive ? `0 0 10px ${badge.color}66` : "none",
            transition: "all 0.2s ease",
          }}
        >
          {isActive ? (
            <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
              <rect x="6" y="6" width="12" height="12" rx="2" />
            </svg>
          ) : (
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z" />
              <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
              <line x1="12" y1="19" x2="12" y2="22" />
            </svg>
          )}
        </button>

        <div style={{ display: "flex", flexDirection: "column" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
            <span>{badge.icon}</span>
            <span style={{ color: badge.color, fontWeight: 600 }}>{badge.text}</span>
            {isActive && (
              <span
                style={{
                  display: "inline-block",
                  width: "6px",
                  height: "6px",
                  borderRadius: "50%",
                  background: badge.color,
                  animation: "pulse 1.2s infinite ease-in-out",
                }}
              />
            )}
          </div>
          {isError && errorMessage && (
            <span style={{ color: "#ef4444", fontSize: "0.7rem", marginTop: "2px" }}>
              {errorMessage}
            </span>
          )}
        </div>
      </div>

      {/* Controls & Voice Picker */}
      <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
        {/* Barge-in Stop Button */}
        {isSpeaking && (
          <button
            onClick={onInterrupt}
            title="Interrupt JARVIS immediately"
            style={{
              background: "rgba(239, 68, 68, 0.2)",
              border: "1px solid rgba(239, 68, 68, 0.5)",
              color: "#ef4444",
              padding: "3px 8px",
              borderRadius: "4px",
              cursor: "pointer",
              fontSize: "0.72rem",
              fontWeight: 600,
            }}
          >
            ⏹ STOP
          </button>
        )}

        {/* Voice Selector */}
        <div style={{ display: "flex", alignItems: "center", gap: "4px" }}>
          <span style={{ color: "rgba(226, 232, 240, 0.6)", fontSize: "0.72rem" }}>VOICE:</span>
          <select
            value={voiceName}
            onChange={(e) => onSelectVoice(e.target.value)}
            disabled={isActive}
            style={{
              background: "rgba(10, 17, 26, 0.9)",
              border: "1px solid rgba(0, 229, 255, 0.25)",
              borderRadius: "4px",
              color: "var(--cyan-primary)",
              fontSize: "0.72rem",
              padding: "2px 6px",
              cursor: isActive ? "not-allowed" : "pointer",
              outline: "none",
            }}
          >
            {(supportedVoices || ["Puck", "Charon", "Kore", "Fenrir", "Aoede"]).map((v) => (
              <option key={v} value={v}>
                {v}
              </option>
            ))}
          </select>
        </div>
      </div>
    </div>
  );
}
