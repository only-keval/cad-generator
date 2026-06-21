import { useAuth } from '../store/auth';

const API_BASE = '/api';

function getAuthHeaders(): Record<string, string> {
  const { token } = useAuth.getState();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(),
      ...options?.headers,
    },
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    if (res.status === 401) {
      useAuth.getState().clearAuth();
    }
    throw new Error(error.detail || `Request failed with ${res.status}`);
  }
  return res.json();
}

export const api = {
  get<T>(path: string): Promise<T> {
    return request<T>(path);
  },
  post<T>(path: string, body?: unknown): Promise<T> {
    return request<T>(path, {
      method: 'POST',
      body: body ? JSON.stringify(body) : undefined,
    });
  },
  patch<T>(path: string, body: unknown): Promise<T> {
    return request<T>(path, {
      method: 'PATCH',
      body: JSON.stringify(body),
    });
  },
  delete<T>(path: string): Promise<T> {
    return request<T>(path, { method: 'DELETE' });
  },
};
