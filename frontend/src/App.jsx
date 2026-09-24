import React, { useState } from 'react';
import { useWebSocket } from './hooks/useWebSocket';
import { useHealth } from './hooks/useHealth';
import { Header } from './components/Header';
import { StatusCard } from './components/StatusCard';
import { ChatWindow } from './components/ChatWindow';
import { MessageInput } from './components/MessageInput';
import { ToolRegistryModal } from './components/ToolRegistryModal';
import './styles/index.css';
import './styles/App.css';

export function App() {
  const {
    connectionStatus,
    isConnected,
    messages,
    isThinking,
    activeTool,
    sendMessage,
    clearMessages,
  } = useWebSocket();

  const { health, isLoading: isHealthLoading, error: healthError, refreshHealth } = useHealth(15000);

  const [isToolsModalOpen, setIsToolsModalOpen] = useState(false);
  const [showHealthCard, setShowHealthCard] = useState(true);

  return (
    <div className="jarvis-app">
      {/* Background HUD glow effect */}
      <div className="hud-grid-overlay" />
      <div className="ambient-glow glow-top" />
      <div className="ambient-glow glow-bottom" />

      {/* Top Application Header */}
      <Header
        connectionStatus={connectionStatus}
        llmProvider={health?.llm_provider}
        toolsCount={health?.tools_registered_count}
        onOpenTools={() => setIsToolsModalOpen(true)}
        onOpenHealth={() => setShowHealthCard((prev) => !prev)}
        showHealthCard={showHealthCard}
      />

      {/* Main Workspace Layout */}
      <main className="app-main-layout">
        {/* Collapsible Health & Diagnostics Card */}
        {showHealthCard && (
          <StatusCard
            health={health}
            isLoading={isHealthLoading}
            error={healthError}
            onRefresh={refreshHealth}
            onClose={() => setShowHealthCard(false)}
          />
        )}

        {/* Central Chat & Telemetry Feed */}
        <section className="chat-section">
          <ChatWindow
            messages={messages}
            isThinking={isThinking}
            activeTool={activeTool}
          />

          <MessageInput
            onSendMessage={sendMessage}
            onClearMessages={clearMessages}
            isThinking={isThinking}
            isConnected={isConnected}
          />
        </section>
      </main>

      {/* Central Tool Registry Modal */}
      <ToolRegistryModal
        isOpen={isToolsModalOpen}
        onClose={() => setIsToolsModalOpen(false)}
      />
    </div>
  );
}

export default App;
