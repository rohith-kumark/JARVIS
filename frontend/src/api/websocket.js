/**
 * Resilient WebSocket Client for JARVIS.
 * Handles bidirectional streaming, automatic reconnects with backoff,
 * heartbeat pings, and event dispatching.
 * Pure JavaScript - decoupled from UI components.
 */

const DEFAULT_WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/api/ws';

export class JarvisWebSocket {
  constructor(url = DEFAULT_WS_URL) {
    this.url = url;
    this.socket = null;
    this.listeners = new Map();
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 10;
    this.reconnectDelay = 1500;
    this.pingIntervalMs = 25000;
    this.pingTimer = null;
    this.isExplicitDisconnect = false;
  }

  /**
   * Register event listener.
   * @param {string} event - Event name ('connection_ack', 'agent_thinking', 'tool_start', etc.)
   * @param {Function} callback
   */
  on(event, callback) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, new Set());
    }
    this.listeners.get(event).add(callback);
    return () => this.off(event, callback);
  }

  /**
   * Unregister event listener.
   */
  off(event, callback) {
    if (this.listeners.has(event)) {
      this.listeners.get(event).delete(callback);
    }
  }

  /**
   * Dispatch event to registered listeners.
   */
  _emit(event, data) {
    if (this.listeners.has(event)) {
      this.listeners.get(event).forEach((cb) => {
        try {
          cb(data);
        } catch (err) {
          console.error(`[WS] Error in handler for event '${event}':`, err);
        }
      });
    }
  }

  /**
   * Initiate WebSocket connection.
   */
  connect() {
    this.isExplicitDisconnect = false;
    if (this.socket && (this.socket.readyState === WebSocket.OPEN || this.socket.readyState === WebSocket.CONNECTING)) {
      return;
    }

    this._emit('status_change', { status: 'connecting' });

    try {
      this.socket = new WebSocket(this.url);

      this.socket.onopen = () => {
        console.log('[WS] Connected to JARVIS WebSocket server');
        this.reconnectAttempts = 0;
        this._startHeartbeat();
        this._emit('status_change', { status: 'connected' });
      };

      this.socket.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          const { type, payload } = message;
          this._emit(type, payload);
          this._emit('*', message);
        } catch (err) {
          console.warn('[WS] Malformed message received:', event.data);
        }
      };

      this.socket.onerror = (err) => {
        console.error('[WS] Connection error:', err);
        this._emit('error', err);
      };

      this.socket.onclose = (event) => {
        this._stopHeartbeat();
        this._emit('status_change', { status: 'disconnected', code: event.code });
        if (!this.isExplicitDisconnect) {
          this._handleReconnect();
        }
      };
    } catch (err) {
      console.error('[WS] Failed to initialize WebSocket:', err);
      this._handleReconnect();
    }
  }

  _handleReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts += 1;
      const delay = Math.min(this.reconnectDelay * Math.pow(1.5, this.reconnectAttempts - 1), 10000);
      console.log(`[WS] Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
      this._emit('status_change', { status: 'reconnecting', attempt: this.reconnectAttempts, delay });
      setTimeout(() => this.connect(), delay);
    } else {
      console.warn('[WS] Max reconnect attempts reached.');
      this._emit('status_change', { status: 'failed' });
    }
  }

  _startHeartbeat() {
    this._stopHeartbeat();
    this.pingTimer = setInterval(() => {
      this.send('ping', {});
    }, this.pingIntervalMs);
  }

  _stopHeartbeat() {
    if (this.pingTimer) {
      clearInterval(this.pingTimer);
      this.pingTimer = null;
    }
  }

  /**
   * Send JSON-formatted message to the server.
   */
  send(type, payload = {}) {
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
      console.warn('[WS] Cannot send message: Socket is not open');
      return false;
    }

    try {
      this.socket.send(JSON.stringify({ type, payload }));
      return true;
    } catch (err) {
      console.error('[WS] Failed to send message:', err);
      return false;
    }
  }

  /**
   * Send user prompt directive.
   */
  sendUserMessage(content, sessionId = null, callerPermission = 'admin') {
    return this.send('user_message', {
      content,
      session_id: sessionId,
      caller_permission: callerPermission,
    });
  }

  /**
   * Gracefully close connection.
   */
  disconnect() {
    this.isExplicitDisconnect = true;
    this._stopHeartbeat();
    if (this.socket) {
      this.socket.close();
      this.socket = null;
    }
    this._emit('status_change', { status: 'disconnected' });
  }
}

export const wsClient = new JarvisWebSocket();
export default wsClient;
