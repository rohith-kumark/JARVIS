/**
 * Agent Service Layer for JARVIS.
 * Encapsulates session management, message preparation, and event mapping.
 * Keeps business logic strictly outside React components.
 */

import { wsClient } from '../api/websocket';
import { apiClient } from '../api/client';

class AgentService {
  constructor() {
    this.sessionId = this._getOrCreateSessionId();
  }

  _getOrCreateSessionId() {
    const key = 'jarvis_session_id';
    let sid = sessionStorage.getItem(key);
    if (!sid) {
      sid = 'session_' + Math.random().toString(36).substring(2, 10);
      sessionStorage.setItem(key, sid);
    }
    return sid;
  }

  getSessionId() {
    return this.sessionId;
  }

  resetSession() {
    this.sessionId = 'session_' + Math.random().toString(36).substring(2, 10);
    sessionStorage.setItem('jarvis_session_id', this.sessionId);
    return this.sessionId;
  }

  /**
   * Connect WebSocket client
   */
  connect() {
    wsClient.connect();
  }

  /**
   * Disconnect WebSocket client
   */
  disconnect() {
    wsClient.disconnect();
  }

  /**
   * Send directive via real-time WebSocket connection
   */
  sendDirective(content, callerPermission = 'admin') {
    return wsClient.sendUserMessage(content, this.sessionId, callerPermission);
  }

  /**
   * Fallback: send directive via REST API
   */
  async sendDirectiveRest(content, callerPermission = 'admin') {
    return apiClient.sendChat(content, this.sessionId, callerPermission);
  }

  /**
   * Subscribe to agent lifecycle events
   */
  subscribe(eventHandlers = {}) {
    const unsubs = [];

    if (eventHandlers.onStatusChange) {
      unsubs.push(wsClient.on('status_change', eventHandlers.onStatusChange));
    }
    if (eventHandlers.onAck) {
      unsubs.push(wsClient.on('connection_ack', eventHandlers.onAck));
    }
    if (eventHandlers.onThinking) {
      unsubs.push(wsClient.on('agent_thinking', eventHandlers.onThinking));
    }
    if (eventHandlers.onToolStart) {
      unsubs.push(wsClient.on('tool_start', eventHandlers.onToolStart));
    }
    if (eventHandlers.onToolComplete) {
      unsubs.push(wsClient.on('tool_complete', eventHandlers.onToolComplete));
    }
    if (eventHandlers.onAgentMessage) {
      unsubs.push(wsClient.on('agent_message', eventHandlers.onAgentMessage));
    }
    if (eventHandlers.onError) {
      unsubs.push(wsClient.on('error', eventHandlers.onError));
    }

    // Return cleanup function
    return () => {
      unsubs.forEach((unsub) => unsub());
    };
  }

  /**
   * Retrieve backend system health
   */
  async checkHealth() {
    return apiClient.getHealth();
  }

  /**
   * Retrieve available tools registry
   */
  async getRegisteredTools() {
    return apiClient.getTools();
  }
}

export const agentService = new AgentService();
export default agentService;
