import React, { useRef, useEffect } from "react";

export default function InputBox({ input, setInput, onSend, disabled, loading }) {
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
          placeholder="Direct JARVIS... (e.g. 'What is the current time?' or 'Calculate 145 * 28')"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          rows={1}
        />
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
