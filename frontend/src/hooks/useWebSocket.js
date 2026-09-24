import { useState, useEffect, useCallback, useRef } from 'react';
import { agentService } from '../services/agentService';

export function useWebSocket() {
  const [connectionStatus, setConnectionStatus] = useState('disconnected');
  const [messages, setMessages] = useState([
    {
      id: 'init_welcome',
      sender: 'agent',
      text: 'JARVIS Core initialized. Standing by for instructions.',
      timestamp: new Date().toISOString(),
      toolExecutions: [],
    }
  ]);
  const [isThinking, setIsThinking] = useState(false);
  const [activeTool, setActiveTool] = useState(null);

  useEffect(() => {
    // Connect to WebSocket via agent service
    agentService.connect();

    const unsubscribe = agentService.subscribe({
      onStatusChange: ({ status }) => {
        setConnectionStatus(status);
      },
      onAck: (ack) => {
        console.log('[useWebSocket] Link confirmed:', ack);
      },
      onThinking: (data) => {
        setIsThinking(true);
      },
      onToolStart: (data) => {
        setActiveTool({
          name: data.tool_name,
          arguments: data.arguments,
          status: 'executing',
          startTime: Date.now(),
        });
      },
      onToolComplete: (data) => {
        setActiveTool((prev) => (prev ? { ...prev, status: 'completed', result: data } : null));
      },
      onAgentMessage: (data) => {
        setIsThinking(false);
        setActiveTool(null);
        setMessages((prev) => [
          ...prev,
          {
            id: 'agent_' + Date.now(),
            sender: 'agent',
            text: data.reply,
            timestamp: new Date().toISOString(),
            toolExecutions: data.tool_executions || [],
            llmProvider: data.llm_provider,
          }
        ]);
      },
      onError: (err) => {
        setIsThinking(false);
        setActiveTool(null);
        setMessages((prev) => [
          ...prev,
          {
            id: 'err_' + Date.now(),
            sender: 'system',
            text: `System Alert: ${err.error || 'Communication failure'}`,
            timestamp: new Date().toISOString(),
            isError: true,
          }
        ]);
      },
    });

    return () => {
      unsubscribe();
      agentService.disconnect();
    };
  }, []);

  const sendMessage = useCallback((text, callerPermission = 'admin') => {
    if (!text || !text.trim()) return;

    const trimmed = text.trim();

    // Optimistically add user message to list
    setMessages((prev) => [
      ...prev,
      {
        id: 'user_' + Date.now(),
        sender: 'user',
        text: trimmed,
        timestamp: new Date().toISOString(),
      }
    ]);

    setIsThinking(true);

    const sent = agentService.sendDirective(trimmed, callerPermission);
    if (!sent) {
      // Fallback to REST API if WebSocket is not ready
      agentService.sendDirectiveRest(trimmed, callerPermission)
        .then((res) => {
          setIsThinking(false);
          setMessages((prev) => [
            ...prev,
            {
              id: 'agent_' + Date.now(),
              sender: 'agent',
              text: res.reply,
              timestamp: new Date().toISOString(),
              toolExecutions: res.tool_executions || [],
              llmProvider: res.llm_provider,
            }
          ]);
        })
        .catch((err) => {
          setIsThinking(false);
          setMessages((prev) => [
            ...prev,
            {
              id: 'err_' + Date.now(),
              sender: 'system',
              text: `Delivery failed: ${err.message}`,
              timestamp: new Date().toISOString(),
              isError: true,
            }
          ]);
        });
    }
  }, []);

  const clearMessages = useCallback(() => {
    agentService.resetSession();
    setMessages([
      {
        id: 'cleared_' + Date.now(),
        sender: 'system',
        text: 'Session reset. Memory context cleared.',
        timestamp: new Date().toISOString(),
      }
    ]);
  }, []);

  return {
    connectionStatus,
    isConnected: connectionStatus === 'connected',
    messages,
    isThinking,
    activeTool,
    sendMessage,
    clearMessages,
  };
}
