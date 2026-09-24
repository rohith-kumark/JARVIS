import React, { useRef, useEffect, useState } from 'react';
import { Bot, User, Wrench, CheckCircle, AlertTriangle, ChevronDown, ChevronRight, Sparkles } from 'lucide-react';

function ToolCard({ tool }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className={`tool-execution-card ${tool.success ? 'tool-success' : 'tool-failed'}`}>
      <div className="tool-card-summary" onClick={() => setExpanded(!expanded)}>
        <div className="tool-card-left">
          <Wrench size={14} className="tool-icon" />
          <span className="tool-name font-mono">{tool.tool_name}</span>
          {tool.execution_time_ms !== undefined && (
            <span className="tool-time font-mono">{tool.execution_time_ms}ms</span>
          )}
        </div>
        <div className="tool-card-right">
          {tool.success ? (
            <span className="status-badge success">
              <CheckCircle size={12} /> Succeeded
            </span>
          ) : (
            <span className="status-badge error">
              <AlertTriangle size={12} /> Failed
            </span>
          )}
          {expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        </div>
      </div>

      {expanded && (
        <div className="tool-card-detail">
          {tool.arguments && Object.keys(tool.arguments).length > 0 && (
            <div className="detail-section">
              <span className="detail-label">Arguments:</span>
              <pre className="detail-json font-mono">{JSON.stringify(tool.arguments, null, 2)}</pre>
            </div>
          )}
          <div className="detail-section">
            <span className="detail-label">{tool.success ? 'Output Data:' : 'Error Message:'}</span>
            <pre className="detail-json font-mono">
              {tool.success ? JSON.stringify(tool.data, null, 2) : tool.error}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
}

export function ChatWindow({ messages, isThinking, activeTool }) {
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isThinking, activeTool]);

  return (
    <div className="chat-window">
      <div className="chat-messages-container">
        {messages.map((msg) => {
          const isUser = msg.sender === 'user';
          const isSystem = msg.sender === 'system';

          return (
            <div
              key={msg.id}
              className={`message-row ${isUser ? 'msg-user-row' : isSystem ? 'msg-system-row' : 'msg-agent-row'}`}
            >
              <div className="avatar-col">
                <div className={`avatar-bubble ${msg.sender}-avatar`}>
                  {isUser ? <User size={16} /> : isSystem ? <Sparkles size={16} /> : <Bot size={16} />}
                </div>
              </div>

              <div className="message-content-col">
                <div className="message-meta">
                  <span className="sender-name">
                    {isUser ? 'Commander' : isSystem ? 'System Protocol' : 'JARVIS'}
                  </span>
                  {msg.timestamp && (
                    <span className="message-time">
                      {new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                    </span>
                  )}
                  {msg.llmProvider && (
                    <span className="provider-tag">{msg.llmProvider}</span>
                  )}
                </div>

                {/* Render any tools executed during this turn */}
                {msg.toolExecutions && msg.toolExecutions.length > 0 && (
                  <div className="tool-executions-list">
                    <span className="tools-heading">Controlled Tool Invocations:</span>
                    {msg.toolExecutions.map((tool, idx) => (
                      <ToolCard key={idx} tool={tool} />
                    ))}
                  </div>
                )}

                <div className={`message-bubble ${msg.isError ? 'bubble-error' : ''}`}>
                  <p className="message-text">{msg.text}</p>
                </div>
              </div>
            </div>
          );
        })}

        {/* Live Active Tool Execution State */}
        {activeTool && (
          <div className="message-row msg-agent-row">
            <div className="avatar-col">
              <div className="avatar-bubble agent-avatar">
                <Bot size={16} />
              </div>
            </div>
            <div className="message-content-col">
              <div className="message-meta">
                <span className="sender-name">JARVIS Execution Engine</span>
              </div>
              <div className="tool-execution-active">
                <div className="active-spinner"></div>
                <div className="active-text">
                  <span>Executing tool: <strong className="font-mono text-cyan">{activeTool.name}</strong></span>
                  {activeTool.arguments && Object.keys(activeTool.arguments).length > 0 && (
                    <span className="active-args font-mono">{JSON.stringify(activeTool.arguments)}</span>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Agent Thinking Indicator */}
        {isThinking && !activeTool && (
          <div className="message-row msg-agent-row">
            <div className="avatar-col">
              <div className="avatar-bubble agent-avatar">
                <Bot size={16} />
              </div>
            </div>
            <div className="message-content-col">
              <div className="thinking-indicator">
                <span className="thinking-dot"></span>
                <span className="thinking-dot"></span>
                <span className="thinking-dot"></span>
                <span className="thinking-label">Reasoning neural sequence...</span>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>
    </div>
  );
}

export default ChatWindow;
