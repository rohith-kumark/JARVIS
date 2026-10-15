import React, { useRef, useEffect } from "react";

export default function InputBox({
  input,
  setInput,
  onSend,
  disabled,
  loading,
  voiceActive,
  voiceState,
  onToggleVoice,
}) {
  const textareaRef = useRef(null);

  // Auto-resize textarea height as user types
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 140)}px`;
    }
  }, [input]);

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (!disabled && input.trim()) {
        onSend();
      }
    }
  };

  return (
    <div className="input-dock">
      <div className="input-box-wrapper">
        <textarea
          ref={textareaRef}
          className="chat-input"
          placeholder={voiceActive ? `JARVIS Voice Mode Active (${voiceState})...` : "Direct JARVIS... (e.g. 'What is the current time?' or 'Calculate 145 * 28')"}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          rows={1}
        />

        {/* Microphone Voice Assistant Toggle */}
        <button
          type="button"
          className="btn-send"
          onClick={onToggleVoice}
          style={{
            background: voiceActive ? "rgba(0, 229, 255, 0.25)" : "transparent",
            borderColor: voiceActive ? "var(--cyan-primary)" : "rgba(0, 229, 255, 0.3)",
            color: voiceActive ? "var(--cyan-primary)" : "#94a3b8",
            boxShadow: voiceActive ? "0 0 12px rgba(0, 229, 255, 0.4)" : "none",
          }}
          title={voiceActive ? "Halt Voice Session" : "Initiate Real-Time Spoken Dialogue"}
        >
          {voiceActive ? (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z" />
              <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
              <line x1="12" y1="19" x2="12" y2="22" stroke="currentColor" strokeWidth="2.5" />
            </svg>
          ) : (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
              <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z" />
              <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
              <line x1="12" y1="19" x2="12" y2="22" />
            </svg>
          )}
        </button>

        <button
          className="btn-send"
          onClick={onSend}
          disabled={disabled || !input.trim()}
          title="Transmit directive (Enter)"
        >
          {loading ? (
            <div className="typing-dot" style={{ margin: "auto" }}></div>
          ) : (
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <line x1="22" y1="2" x2="11" y2="13"></line>
              <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
            </svg>
          )}
        </button>
      </div>
      <div className="input-subtext">
        <span>JARVIS Mark I — Neural Command Interface</span>
        <span>Press <b>Enter</b> to transmit &bull; <b>Shift + Enter</b> for newline</span>
      </div>
    </div>
  );
}
