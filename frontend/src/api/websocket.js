/**
 * Resilient WebSocket Client for JARVIS.
 * Handles bidirectional streaming, automatic reconnects with backoff,
 * heartbeat pings, and event dispatching.
 * Pure JavaScript - decoupled from UI components.
 */

function resolveWsUrl() {
  const envUrl = import.meta.env.VITE_WS_URL;
  // If explicitly specified with an IP, use it
  if (envUrl && !envUrl.includes('localhost')) {
    return envUrl;
  }
  if (typeof window !== 'undefined') {
    const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    // Prefer 127.0.0.1 over localhost on Linux to prevent IPv6 [::1] connection refusal
    const hostname = window.location.hostname === 'localhost' ? '127.0.0.1' : (window.location.hostname || '127.0.0.1');
    return `${proto}//${hostname}:8000/api/ws`;
  }
  return 'ws://127.0.0.1:8000/api/ws';
}

export class JarvisWebSocket {
  constructor(url = resolveWsUrl()) {
    this.url = url;
    this.socket = null;
    this.listeners = new Map();
    this.reconnectAttempts = 0;
    this.maxReconnectAttempts = 15;
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

    // Always re-resolve URL upon connect
    this.url = resolveWsUrl();
    this._emit('status_change', { status: 'connecting' });

    try {
      this.socket = new WebSocket(this.url);

      this.socket.onopen = () => {
        console.log(`[WS] Connected to JARVIS at ${this.url}`);
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
        console.warn(`[WS] Connection issue at ${this.url}:`, err);
        this._emit('connection_error', { url: this.url });
      };

      this.socket.onclose = (event) => {
        this._stopHeartbeat();
        this._emit('status_change', { status: 'disconnected', code: event.code });
        if (!this.isExplicitDisconnect) {
          this._handleReconnect();
        }
      };
    } catch (err) {
      console.warn('[WS] Failed to instantiate WebSocket:', err);
      this._handleReconnect();
    }
  }

  _handleReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts += 1;
      const delay = Math.min(this.reconnectDelay * Math.pow(1.3, this.reconnectAttempts - 1), 8000);
      console.log(`[WS] Reconnecting in ${Math.round(delay)}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
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
