import React, { useEffect, useRef } from "react";
import MessageItem from "./MessageItem";
import TypingIndicator from "./TypingIndicator";

export default function ChatWindow({ messages, loading, onSelectPrompt }) {
  const bottomRef = useRef(null);

  // Auto-scroll on new message or loading change
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const defaultSuggestions = [
    { title: "Query Current Time", prompt: "What is the current time and date?" },
    { title: "Safe Math Calculation", prompt: "Calculate (450 * 12) / 5 using the calculator." },
    { title: "System Capabilities", prompt: "What tools and capabilities do you currently have registered?" },
    { title: "Compound Query", prompt: "What time is it in UTC, and what is 2 to the power of 10?" },
  ];

  return (
    <div className="messages-container">
      {messages.length === 0 ? (
        <div className="empty-chat-state">
          <div className="hud-arc-reactor" style={{ width: "64px", height: "64px", margin: "0 auto" }}>
            <div className="hud-arc-inner" style={{ width: "28px", height: "28px" }}></div>
          </div>
          <h2>J.A.R.V.I.S. ONLINE</h2>
          <p>Phase 1 Orchestration Engine Active. Ready for Operator Directives.</p>

          <div className="empty-suggestions">
            {defaultSuggestions.map((item, idx) => (
              <div
                key={idx}
                className="suggestion-card"
                onClick={() => onSelectPrompt(item.prompt)}
              >
                <div style={{ color: "var(--cyan-primary)", fontWeight: "600", marginBottom: "4px" }}>
                  {item.title}
                </div>
                <div style={{ color: "var(--text-secondary)", fontSize: "0.78rem" }}>
                  "{item.prompt}"
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : (
        messages.map((msg, index) => <MessageItem key={msg.id || index} message={msg} />)
      )}

      {loading && <TypingIndicator />}
      <div ref={bottomRef} />
    </div>
  );
}
