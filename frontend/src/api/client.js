/**
 * REST API Client for JARVIS Core Backend.
 * Handles HTTP requests, endpoint URLs, and response formatting.
 * Keeps networking concerns isolated from React components.
 */

function resolveApiUrl() {
  const envUrl = import.meta.env.VITE_API_BASE_URL;
  if (envUrl && !envUrl.includes('localhost')) {
    return envUrl;
  }
  if (typeof window !== 'undefined') {
    const proto = window.location.protocol;
    const hostname = window.location.hostname === 'localhost' ? '127.0.0.1' : (window.location.hostname || '127.0.0.1');
    return `${proto}//${hostname}:8000`;
  }
  return 'http://127.0.0.1:8000';
}

class ApiClient {
  constructor(baseUrl = resolveApiUrl()) {
    this.baseUrl = baseUrl;
  }

  async _request(endpoint, options = {}) {
    const currentBase = resolveApiUrl();
    const url = `${currentBase}${endpoint}`;
    const defaultHeaders = {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    };

    const config = {
      ...options,
      headers: {
        ...defaultHeaders,
        ...options.headers,
      },
    };

    try {
      const response = await fetch(url, config);
      if (!response.ok) {
        let errorData;
        try {
          errorData = await response.json();
        } catch {
          errorData = { error: response.statusText };
        }
        throw new Error(errorData.detail || errorData.error || `HTTP ${response.status}: ${response.statusText}`);
      }
      return await response.json();
    } catch (error) {
      console.error(`[ApiClient Error] ${options.method || 'GET'} ${endpoint}:`, error);
      throw error;
    }
  }

  /**
   * Health check endpoint
   */
  async getHealth() {
    return this._request('/api/health');
  }

  /**
   * Fetch registered tools list
   */
  async getTools(permission = null) {
    const query = permission ? `?permission=${encodeURIComponent(permission)}` : '';
    return this._request(`/api/tools${query}`);
  }

  /**
   * Manually execute a tool
   */
  async executeTool(name, args = {}, permission = 'admin') {
    return this._request('/api/tools/execute', {
      method: 'POST',
      body: JSON.stringify({
        name,
        arguments: args,
        caller_permission: permission,
      }),
    });
  }

  /**
   * REST chat endpoint
   */
  async sendChat(message, sessionId = null, permission = 'admin') {
    return this._request('/api/chat', {
      method: 'POST',
      body: JSON.stringify({
        message,
        session_id: sessionId,
        caller_permission: permission,
      }),
    });
  }
}

export const apiClient = new ApiClient();
export default apiClient;
