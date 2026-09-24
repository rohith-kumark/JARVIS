/**
 * JARVIS API Service Layer
 * Centralized REST client communicating with FastAPI backend.
 */

const API_BASE = "/api";

async function request(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;
  const headers = {
    "Content-Type": "application/json",
    ...options.headers,
  };

  try {
    const response = await fetch(url, {
      ...options,
      headers,
    });

    const data = await response.json().catch(() => null);

    if (!response.ok) {
      const errorMsg = data?.detail || data?.error || `HTTP ${response.status}: Request failed`;
      throw new Error(errorMsg);
    }

    return data;
  } catch (error) {
    console.error(`API Error on ${endpoint}:`, error);
    throw error;
  }
}

export const api = {
  /**
   * Health check endpoint
   */
  async getHealth() {
    return request("/health");
  },

  /**
   * Send a chat message through orchestrator
   * @param {string} message - User message
   * @param {string|null} conversationId - Optional conversation ID
   */
  async sendMessage(message, conversationId = null) {
    return request("/chat", {
      method: "POST",
      body: JSON.stringify({
        message,
        conversation_id: conversationId,
      }),
    });
  },

  /**
   * List all conversation sessions
   */
  async getConversations(limit = 50) {
    return request(`/conversations?limit=${limit}`);
  },

  /**
   * Create a new conversation session explicitly
   */
  async createConversation(title = "New Conversation") {
    return request("/conversations", {
      method: "POST",
      body: JSON.stringify({ title }),
    });
  },

  /**
   * Fetch conversation details with messages
   */
  async getConversation(conversationId) {
    return request(`/conversations/${conversationId}`);
  },

  /**
   * Delete a conversation
   */
  async deleteConversation(conversationId) {
    return request(`/conversations/${conversationId}`, {
      method: "DELETE",
    });
  },

  /**
   * Fetch memories and preferences
   */
  async getMemory(conversationId = null) {
    const query = conversationId ? `?conversation_id=${conversationId}` : "";
    return request(`/memory${query}`);
  },
};
