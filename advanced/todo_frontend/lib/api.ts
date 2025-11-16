// lib/api.ts

const API_BASE_URL = "http://localhost:5080";

// This is our fetch-based replacement for the axios instance
async function apiFetch(endpoint: string, options: RequestInit = {}) {
  const url = `${API_BASE_URL}${endpoint}`;

  // Set default headers and credentials
  const defaultHeaders = {
    "Content-Type": "application/json",
    ...options.headers,
  };

  const config: RequestInit = {
    ...options,
    headers: defaultHeaders,
    credentials: "include",
  };

  // Make the request
  const response = await fetch(url, config);
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    const error = new Error(errorData.detail || "An API error occurred");
    (error as any).status = response.status;
    (error as any).data = errorData;
    throw error;
  }

  // If the response has content, parse it as JSON
  if (response.status === 204) { // No Content
    return null;
  }
  return response.json();
}

// We can create helper methods to match the `axios` API
export const api = {
  get: (endpoint: string, options?: RequestInit) =>
    apiFetch(endpoint, { ...options, method: "GET" }),

  post: (endpoint: string, body: object, options?: RequestInit) =>
    apiFetch(endpoint, { ...options, method: "POST", body: JSON.stringify(body) }),

  delete: (endpoint: string, options?: RequestInit) =>
    apiFetch(endpoint, { ...options, method: "DELETE" }),

};