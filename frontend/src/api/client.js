/**
 * REST API Client for JARVIS Core Backend.
 * Handles HTTP requests, endpoint URLs, and response formatting.
 * Keeps networking concerns isolated from React components.
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

class ApiClient {
  constructor(baseUrl = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  async _request(endpoint, options = {}) {
    const url = `${this.baseUrl}${endpoint}`;
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
   * @returns {Promise<{status: string, version: string, environment: string, llm_provider: string, tools_registered_count: number, uptime_seconds: number}>}
   */
  async getHealth() {
    return this._request('/api/health');
  }

  /**
   * Fetch registered tools list
   * @param {string} [permission]
   * @returns {Promise<{tools: Array, total: number}>}
   */
  async getTools(permission = null) {
    const query = permission ? `?permission=${encodeURIComponent(permission)}` : '';
    return this._request(`/api/tools${query}`);
  }

  /**
   * Manually execute a tool
   * @param {string} name
   * @param {object} args
   * @param {string} permission
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
   * @param {string} message
   * @param {string} [sessionId]
   * @param {string} [permission]
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
