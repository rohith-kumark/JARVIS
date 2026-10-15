import React, { useState, useEffect, useRef } from "react";
import Header from "./components/Header";
import Sidebar from "./components/Sidebar";
import ChatWindow from "./components/ChatWindow";
import InputBox from "./components/InputBox";
import MemoryModal from "./components/MemoryModal";
import VoiceHUD from "./components/VoiceHUD";
import { api } from "./services/api";
import { AudioStreamer } from "./services/audioStreamer";

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

  // Phase 3: Real-Time Voice State
  const [voiceActive, setVoiceActive] = useState(false);
  const [voiceState, setVoiceState] = useState("IDLE");
  const [voiceName, setVoiceName] = useState("Puck");
  const [supportedVoices, setSupportedVoices] = useState(["Puck", "Charon", "Kore", "Fenrir", "Aoede"]);
  const [voiceError, setVoiceError] = useState(null);

  const wsRef = useRef(null);
  const streamerRef = useRef(null);

  // Poll / load health, conversations, and voice configuration on mount
  useEffect(() => {
    checkHealth();
    loadConversations();
    loadVoiceConfig();
    const timer = setInterval(checkHealth, 15000);
    return () => clearInterval(timer);
  }, []);

  const loadVoiceConfig = async () => {
    try {
      const data = await api.getVoices();
      if (data?.voices?.length) {
        setSupportedVoices(data.voices);
      }
      if (data?.default) {
        setVoiceName(data.default);
      }
    } catch {
      // Use defaults if config endpoint unavailable
    }
  };

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

  // Cleanup voice session on unmount
  useEffect(() => {
    return () => {
      stopVoiceSession();
    };
  }, []);

  const stopVoiceSession = () => {
    if (streamerRef.current) {
      streamerRef.current.stopRecording();
      streamerRef.current = null;
    }
    if (wsRef.current) {
      try {
        if (wsRef.current.readyState === WebSocket.OPEN) {
          wsRef.current.send(JSON.stringify({ type: "stop" }));
        }
        wsRef.current.close();
      } catch {}
      wsRef.current = null;
    }
    setVoiceActive(false);
    setVoiceState("IDLE");
  };

  const handleInterruptVoice = () => {
    if (streamerRef.current) {
      streamerRef.current.interrupt();
    }
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: "interrupt" }));
    }
    setVoiceState("INTERRUPTED");
  };

  const handleToggleVoice = async () => {
    if (voiceActive) {
      stopVoiceSession();
      return;
    }

    setVoiceError(null);
    setVoiceState("CONNECTING");

    try {
      // 1. Initialize AudioStreamer
      const streamer = new AudioStreamer({
        onAudioChunk: (b64) => {
          if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify({ type: "audio", data: b64 }));
          }
        },
        onError: (err) => {
          setVoiceError(err);
          setVoiceState("ERROR");
          stopVoiceSession();
        },
      });

      streamerRef.current = streamer;

      // 2. Open WebSocket connection
      const wsUrl = api.getVoiceWsUrl();
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = async () => {
        // Send initial setup frame
        ws.send(JSON.stringify({ type: "start", voice_name: voiceName }));

        // Start microphone streaming
        try {
          await streamer.startRecording();
          setVoiceActive(true);
          setVoiceState("LISTENING");
        } catch (micErr) {
          setVoiceError(micErr.message);
          setVoiceState("ERROR");
          stopVoiceSession();
        }
      };

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          if (msg.type === "state" && msg.state) {
            setVoiceState(msg.state);
          } else if (msg.type === "audio" && msg.data) {
            streamer.playChunk(msg.data, msg.sample_rate || 24000);
          } else if (msg.type === "interrupted") {
            streamer.interrupt();
            setVoiceState("LISTENING");
          } else if (msg.type === "transcript" && msg.text) {
            // Append spoken transcript to chat window
            setMessages((prev) => [
              ...prev,
              {
                role: msg.role === "user" ? "user" : "assistant",
                content: msg.text,
                created_at: new Date().toISOString(),
              },
            ]);
          } else if (msg.type === "error") {
            setVoiceError(msg.message);
            setVoiceState("ERROR");
          }
        } catch (e) {
          console.warn("Error parsing voice message:", e);
        }
      };

      ws.onerror = (e) => {
        console.error("Voice WebSocket error:", e);
        setVoiceError("Voice streaming connection error.");
        setVoiceState("ERROR");
      };

      ws.onclose = () => {
        stopVoiceSession();
      };
    } catch (err) {
      setVoiceError(err.message || "Failed to start voice session");
      setVoiceState("ERROR");
      stopVoiceSession();
    }
  };

  return (
    <div className="jarvis-app">
      <Header
        health={health}
        onToggleSidebar={() => setSidebarOpen(!sidebarOpen)}
        onOpenMemory={() => setMemoryOpen(true)}
        voiceActive={voiceActive}
        voiceState={voiceState}
        onToggleVoice={handleToggleVoice}
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
          {/* Phase 3: Voice HUD Component */}
          <VoiceHUD
            voiceState={voiceState}
            voiceName={voiceName}
            supportedVoices={supportedVoices}
            onSelectVoice={(v) => setVoiceName(v)}
            onToggleVoice={handleToggleVoice}
            onInterrupt={handleInterruptVoice}
            errorMessage={voiceError}
          />

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
            voiceActive={voiceActive}
            voiceState={voiceState}
            onToggleVoice={handleToggleVoice}
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
