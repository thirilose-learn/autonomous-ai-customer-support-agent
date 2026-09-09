/**
 * Frontend API Service Layer
 * Reads base URL from VITE_API_URL environment variable with fallback to local backend.
 * Manages demo authentication tokens and customer session persistence.
 */
const API_BASE_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

const SESSION_TOKEN_KEY = "capstone_demo_session_token";
const SESSION_CUSTOMER_KEY = "capstone_demo_customer";

export function getStoredToken() {
  return localStorage.getItem(SESSION_TOKEN_KEY);
}

export function getStoredCustomer() {
  try {
    const raw = localStorage.getItem(SESSION_CUSTOMER_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function setStoredSession(token, customer) {
  if (token) {
    localStorage.setItem(SESSION_TOKEN_KEY, token);
  } else {
    localStorage.removeItem(SESSION_TOKEN_KEY);
  }
  if (customer) {
    localStorage.setItem(SESSION_CUSTOMER_KEY, JSON.stringify(customer));
  } else {
    localStorage.removeItem(SESSION_CUSTOMER_KEY);
  }
}

export function clearStoredSession() {
  localStorage.removeItem(SESSION_TOKEN_KEY);
  localStorage.removeItem(SESSION_CUSTOMER_KEY);
}

/**
 * Check backend health status.
 * @returns {Promise<{connected: boolean, data?: object, error?: string}>}
 */
export async function checkBackendHealth() {
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 5000);

    const response = await fetch(`${API_BASE_URL}/api/health`, {
      method: "GET",
      headers: {
        "Accept": "application/json",
      },
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      return {
        connected: false,
        error: `HTTP Error: ${response.status} ${response.statusText}`,
      };
    }

    const data = await response.json();
    return {
      connected: true,
      data,
    };
  } catch (err) {
    let errorMessage = "Unable to reach FastAPI backend.";
    if (err.name === "AbortError") {
      errorMessage = "Connection timed out after 5s.";
    } else if (err.message) {
      errorMessage = err.message;
    }
    return {
      connected: false,
      error: errorMessage,
    };
  }
}

/**
 * Fetch all 25 demo customer personas from the backend.
 * @returns {Promise<Array<object>>}
 */
export async function fetchDemoPersonas() {
  const response = await fetch(`${API_BASE_URL}/api/v1/auth/personas`, {
    method: "GET",
    headers: {
      "Accept": "application/json",
    },
  });
  if (!response.ok) {
    throw new Error(`Failed to load demo personas: ${response.statusText}`);
  }
  return response.json();
}

/**
 * Select active demo persona and obtain signed session token.
 * @param {string} demoCustomerId
 * @returns {Promise<{access_token: string, customer: object}>}
 */
export async function selectDemoPersona(demoCustomerId) {
  const response = await fetch(`${API_BASE_URL}/api/v1/auth/select-persona`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Accept": "application/json",
    },
    body: JSON.stringify({ demo_customer_id: demoCustomerId }),
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || `Persona selection failed: ${response.statusText}`);
  }
  const data = await response.json();
  setStoredSession(data.access_token, data.customer);
  return data;
}

/**
 * Validate current session and retrieve CustomerContext.
 * @returns {Promise<object|null>}
 */
export async function getCurrentCustomerProfile() {
  const token = getStoredToken();
  if (!token) return null;

  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/auth/me`, {
      method: "GET",
      headers: {
        "Accept": "application/json",
        "Authorization": `Bearer ${token}`,
      },
    });
    if (response.status === 401) {
      clearStoredSession();
      return null;
    }
    if (!response.ok) {
      return null;
    }
    const customer = await response.json();
    setStoredSession(token, customer);
    return customer;
  } catch {
    return null;
  }
}

/**
 * Query RAG knowledge base for policy clauses.
 * @param {string} query
 * @param {string} [category]
 * @param {number} [topK=3]
 * @returns {Promise<object>}
 */
export async function queryRAGKnowledgeBase(query, category = null, topK = 3) {
  const token = getStoredToken();
  const headers = {
    "Content-Type": "application/json",
    "Accept": "application/json",
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const payload = {
    query,
    top_k: topK,
  };
  if (category) {
    payload.category = category;
  }

  const response = await fetch(`${API_BASE_URL}/api/v1/rag/query`, {
    method: "POST",
    headers,
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || `RAG search failed: ${response.statusText}`);
  }
  return response.json();
}

/**
 * Send inquiry message to AI Agent.
 * Requires an active demo session token in localStorage.
 * @param {string} message
 * @param {string} [conversationId]
 * @returns {Promise<object>}
 */
export async function sendChatMessage(message, conversationId = null) {
  const token = getStoredToken();
  if (!token) {
    throw new Error("No active customer session. Please select a customer persona first.");
  }

  const payload = { message };
  if (conversationId) {
    payload.conversation_id = conversationId;
  }

  const response = await fetch(`${API_BASE_URL}/api/v1/chat/message`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Accept": "application/json",
      "Authorization": `Bearer ${token}`,
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || `Agent request failed: ${response.statusText}`);
  }
  return response.json();
}

/**
 * Reset conversation history for the active session.
 * @param {string} [conversationId]
 * @returns {Promise<object>}
 */
export async function resetChat(conversationId = null) {
  const token = getStoredToken();
  const headers = {
    "Content-Type": "application/json",
    "Accept": "application/json",
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const payload = { message: "reset" };
  if (conversationId) {
    payload.conversation_id = conversationId;
  }

  const response = await fetch(`${API_BASE_URL}/api/v1/chat/reset`, {
    method: "POST",
    headers,
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || `Reset failed: ${response.statusText}`);
  }
  return response.json();
}

export function getApiBaseUrl() {
  return API_BASE_URL;
}
