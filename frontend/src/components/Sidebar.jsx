import React from "react";

export default function Sidebar({
  conversations,
  currentConvId,
  onSelectConversation,
  onNewConversation,
  onDeleteConversation,
  isOpen,
}) {
  return (
    <aside className={`jarvis-sidebar ${isOpen ? "open" : ""}`}>
      <div className="sidebar-header">
        <button className="btn-new-chat" onClick={onNewConversation}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
            <line x1="12" y1="5" x2="12" y2="19"></line>
            <line x1="5" y1="12" x2="19" y2="12"></line>
          </svg>
          <span>NEW DIRECTIVE</span>
        </button>
      </div>

      <div className="conversation-list">
        {conversations.length === 0 ? (
          <div style={{ padding: "16px", color: "var(--text-muted)", fontSize: "0.8rem", textAlign: "center" }}>
            No recorded sessions
          </div>
        ) : (
          conversations.map((conv) => {
            const isActive = conv.id === currentConvId;
            return (
              <div
                key={conv.id}
                className={`conv-item ${isActive ? "active" : ""}`}
                onClick={() => onSelectConversation(conv.id)}
              >
                <div className="conv-title" title={conv.title}>
                  {conv.title || "Directive Session"}
                </div>
                <button
                  className="conv-delete-btn"
                  title="Erase session"
                  onClick={(e) => {
                    e.stopPropagation();
                    onDeleteConversation(conv.id);
                  }}
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <polyline points="3 6 5 6 21 6"></polyline>
                    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                  </svg>
                </button>
              </div>
            );
          })
        )}
      </div>

      <div className="sidebar-footer">
        <span>SQLITE SHORT-TERM STORE</span>
        <span>V1.0</span>
      </div>
    </aside>
  );
}
