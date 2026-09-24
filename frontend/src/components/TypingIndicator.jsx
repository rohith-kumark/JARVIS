import React from "react";

export default function TypingIndicator() {
  return (
    <div className="message-row assistant">
      <div className="typing-container">
        <div className="typing-dot"></div>
        <div className="typing-dot"></div>
        <div className="typing-dot"></div>
        <span className="typing-text">ANALYZING DIRECTIVE...</span>
      </div>
    </div>
  );
}
