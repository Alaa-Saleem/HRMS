/** Base URL for FastAPI backend (Docker default: API on port 8787). */
import {
  getRefreshToken,
  getSessionEmail,
  saveAuthSession,
} from './session.js';

export function apiBaseUrl() {
  const w = typeof window !== 'undefined' ? window : undefined;
  if (w && w.__HRMS_API__) {
    return String(w.__HRMS_API__).replace(/\/+$/, '');
  }
  if (w && w.location && w.location.port === '8787') {
    return w.location.origin.replace(/\/+$/, '');
  }
  return 'http://127.0.0.1:8787';
}

/** @returns {Headers} */
export function apiHeaders(includeJson = false) {
  const h = new Headers();
  if (includeJson) h.set('Content-Type', 'application/json');
  const token =
    typeof sessionStorage !== 'undefined' ? sessionStorage.getItem('hrms_access_token') : null;
  if (token) h.set('Authorization', `Bearer ${token}`);
  return h;
}

let refreshInFlight = null;

async function tryRefreshToken() {
  if (refreshInFlight) return refreshInFlight;
  const rt = getRefreshToken();
  if (!rt) return false;
  refreshInFlight = (async () => {
    try {
      const res = await fetch(`${apiBaseUrl()}/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: rt }),
      });
      const data = await parseJsonSafe(res);
      if (!res.ok || !data?.access_token) return false;
      const email = getSessionEmail() || (data.user && data.user.email) || '';
      saveAuthSession(
        data.access_token,
        email,
        data.refresh_token || null
      );
      return true;
    } catch {
      return false;
    } finally {
      refreshInFlight = null;
    }
  })();
  return refreshInFlight;
}

function pathNoRetry(path) {
  const p = path.startsWith('/') ? path : `/${path}`;
  return p === '/auth/login' || p === '/auth/refresh';
}

export async function apiFetch(path, options = {}) {
  const url = `${apiBaseUrl()}${path.startsWith('/') ? path : '/' + path}`;
  const res = await fetch(url, options);
  if (res.status !== 401 || options._hrmsRetried || pathNoRetry(path)) {
    return res;
  }
  const ok = await tryRefreshToken();
  if (!ok) return res;
  const sendJson = options.body != null && typeof options.body === 'string';
  const next = { ...options, _hrmsRetried: true };
  const merged = new Headers();
  const fresh = apiHeaders(sendJson);
  if (options.headers) {
    new Headers(options.headers).forEach((v, k) => merged.set(k, v));
  }
  fresh.forEach((v, k) => merged.set(k, v));
  next.headers = merged;
  return fetch(url, next);
}

export async function parseJsonSafe(res) {
  const ct = res.headers.get('content-type') || '';
  if (ct.includes('application/json')) {
    try {
      return await res.json();
    } catch {
      return null;
    }
  }
  return null;
}

/** JSON request; omit `body` for no request body (e.g. read-all POST). */
export async function apiJson(method, path, body = undefined) {
  const sendJson = body !== undefined;
  const res = await apiFetch(path.startsWith('/') ? path : `/${path}`, {
    method,
    headers: apiHeaders(sendJson),
    body: sendJson ? JSON.stringify(body) : undefined,
  });
  return res;
}
