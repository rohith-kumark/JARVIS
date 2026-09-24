import React, { useState, useEffect } from "react";
import Header from "./components/Header";
import Sidebar from "./components/Sidebar";
import ChatWindow from "./components/ChatWindow";
import InputBox from "./components/InputBox";
import MemoryModal from "./components/MemoryModal";
import { api } from "./services/api";

export default function App() {
  const [health, setHealth] = useState(null);
  const [conversations, setConversations] = useState([]);
  const [currentConvId, setCurrentConvId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [memoryOpen, setMemoryOpen] = useState(false);
  const [errorBanner, setErrorBanner] = useState(null);

  // Poll / load health and conversations on mount
  useEffect(() => {
    checkHealth();
    loadConversations();
    const timer = setInterval(checkHealth, 15000);
    return () => clearInterval(timer);
  }, []);

  const checkHealth = async () => {
    try {
      const data = await api.getHealth();
      setHealth(data);
    } catch (err) {
      setHealth({ status: "disconnected", database: "unreachable" });
    }
  };

  const loadConversations = async () => {
    try {
      const data = await api.getConversations();
      setConversations(data);
    } catch (err) {
      console.error("Failed to load conversations:", err);
    }
  };

  // Load selected conversation history
  const handleSelectConversation = async (convId) => {
    setCurrentConvId(convId);
    setErrorBanner(null);
    try {
      const data = await api.getConversation(convId);
      setMessages(data.messages || []);
      if (window.innerWidth <= 768) {
        setSidebarOpen(false);
      }
    } catch (err) {
      setErrorBanner(`Failed to load conversation: ${err.message}`);
    }
  };

  // Start new conversation directive
  const handleNewConversation = () => {
    setCurrentConvId(null);
    setMessages([]);
    setErrorBanner(null);
    if (window.innerWidth <= 768) {
      setSidebarOpen(false);
    }
  };

  // Delete conversation
  const handleDeleteConversation = async (convId) => {
    try {
      await api.deleteConversation(convId);
      if (currentConvId === convId) {
        handleNewConversation();
      }
      loadConversations();
    } catch (err) {
      setErrorBanner(`Failed to delete conversation: ${err.message}`);
    }
  };

  // Send message to backend
  const handleSendMessage = async (textToSend = null) => {
    const messageContent = (textToSend || input).trim();
    if (!messageContent || loading) return;

    // Optimistically append user message
    const userMsg = {
      role: "user",
      content: messageContent,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);
    setErrorBanner(null);

    try {
      const chatRes = await api.sendMessage(messageContent, currentConvId);

      // If new session, set the active conversation ID
      if (!currentConvId && chatRes.conversation_id) {
        setCurrentConvId(chatRes.conversation_id);
      }

      // Append assistant response
      const assistantMsg = {
        role: "assistant",
        content: chatRes.response,
        tool_calls: chatRes.tool_calls || [],
        created_at: chatRes.created_at || new Date().toISOString(),
      };
      setMessages((prev) => [...prev, assistantMsg]);

      // Refresh conversations list in sidebar
      loadConversations();
    } catch (err) {
      console.error("Chat error:", err);
      const errorMsg = err.message || "An unexpected error occurred.";
      setErrorBanner(errorMsg);
      // Also show in chat window
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: `⚠️ Error executing directive: ${errorMsg}`,
          created_at: new Date().toISOString(),
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="jarvis-app">
      <Header
        health={health}
        onToggleSidebar={() => setSidebarOpen(!sidebarOpen)}
        onOpenMemory={() => setMemoryOpen(true)}
      />

      {errorBanner && (
        <div
          style={{
            background: "rgba(255, 51, 102, 0.2)",
            borderBottom: "1px solid var(--accent-red)",
            color: "#ff99aa",
            padding: "8px 24px",
            fontSize: "0.82rem",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <span>{errorBanner}</span>
          <button
            onClick={() => setErrorBanner(null)}
            style={{ background: "none", border: "none", color: "#fff", cursor: "pointer" }}
          >
            &times;
          </button>
        </div>
      )}

      <div className="jarvis-body">
        <Sidebar
          conversations={conversations}
          currentConvId={currentConvId}
          onSelectConversation={handleSelectConversation}
          onNewConversation={handleNewConversation}
          onDeleteConversation={handleDeleteConversation}
          isOpen={sidebarOpen}
        />

        <main className="jarvis-main">
          <ChatWindow
            messages={messages}
            loading={loading}
            onSelectPrompt={(prompt) => handleSendMessage(prompt)}
          />

          <InputBox
            input={input}
            setInput={setInput}
            onSend={() => handleSendMessage()}
            disabled={loading}
            loading={loading}
          />
        </main>
      </div>

      <MemoryModal
        isOpen={memoryOpen}
        onClose={() => setMemoryOpen(false)}
        currentConvId={currentConvId}
      />
    </div>
  );
}
