import React, { useState } from 'react';
import { Send, RotateCcw, Shield, Sparkles } from 'lucide-react';

const SUGGESTIONS = [
  "Run system diagnostics and status check",
  "What is the current time and host environment?",
  "What are your core architectural capabilities?",
];

export function MessageInput({ onSendMessage, onClearMessages, isThinking, isConnected }) {
  const [inputText, setInputText] = useState('');
  const [permission, setPermission] = useState('admin');

  const handleSubmit = (e) => {
    e?.preventDefault();
    if (!inputText.trim() || isThinking) return;
    onSendMessage(inputText.trim(), permission);
    setInputText('');
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleSuggestionClick = (prompt) => {
    if (isThinking) return;
    onSendMessage(prompt, permission);
  };

  return (
    <div className="input-container">
      {/* Quick Suggestion Chips */}
      <div className="suggestions-row">
        {SUGGESTIONS.map((suggestion, idx) => (
          <button
            key={idx}
            className="suggestion-chip"
            onClick={() => handleSuggestionClick(suggestion)}
            disabled={isThinking}
          >
            <Sparkles size={11} className="suggestion-icon" />
            <span>{suggestion}</span>
          </button>
        ))}
      </div>

      <form className="input-form" onSubmit={handleSubmit}>
        <div className="input-controls-left">
          <div className="permission-selector" title="Security clearance for this directive">
            <Shield size={14} className="perm-icon" />
            <select
              value={permission}
              onChange={(e) => setPermission(e.target.value)}
              className="perm-select"
            >
              <option value="admin">ADMIN</option>
              <option value="execute">EXECUTE</option>
              <option value="read_only">READ ONLY</option>
            </select>
          </div>
        </div>

        <input
          type="text"
          className="text-input"
          placeholder={isConnected ? "Enter directive or question for JARVIS..." : "Waiting for connection to core..."}
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isThinking}
        />

        <div className="input-actions-right">
          <button
            type="button"
            className="icon-btn action-btn-clear"
            onClick={onClearMessages}
            title="Clear conversation and reset session"
          >
            <RotateCcw size={16} />
          </button>

          <button
            type="submit"
            className="btn-send"
            disabled={!inputText.trim() || isThinking}
            title="Send directive"
          >
            <Send size={16} />
          </button>
        </div>
      </form>
    </div>
  );
}

export default MessageInput;
