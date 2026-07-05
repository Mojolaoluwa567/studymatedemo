export const API_URL = import.meta.env.VITE_API_URL || "http://localhost:5000";

/**
 * Reads the CSRF token flask-jwt-extended writes as a separate,
 * JS-readable cookie (csrf_access_token) alongside the HttpOnly JWT
 * cookie. Required on every state-changing request (POST/PUT/PATCH/
 * DELETE) once JWT_COOKIE_CSRF_PROTECT is enabled - without it the
 * backend rejects the request even though the JWT cookie itself is valid.
 */
function getCsrfToken() {
  const match = document.cookie.match(/csrf_access_token=([^;]+)/);
  return match ? decodeURIComponent(match[1]) : null;
}

function authHeaders(extra = {}, includeCsrf = false) {
  const headers = { ...extra };
  if (includeCsrf) {
    const csrf = getCsrfToken();
    if (csrf) headers["X-CSRF-TOKEN"] = csrf;
  }
  return headers;
}

async function handle(response) {
  let data;
  try {
    data = await response.json();
  } catch {
    data = null;
  }
  if (!response.ok) {
    const message = data?.error || data?.msg || "Something went wrong.";
    const error = new Error(message);
    error.status = response.status;
    throw error;
  }
  return data;
}

export const api = {
  async post(path, body) {
    const res = await fetch(`${API_URL}${path}`, {
      method: "POST",
      credentials: "include",
      headers: authHeaders({ "Content-Type": "application/json" }, true),
      body: JSON.stringify(body),
    });
    return handle(res);
  },

  async get(path) {
    const res = await fetch(`${API_URL}${path}`, {
      method: "GET",
      credentials: "include",
      headers: authHeaders(),
    });
    return handle(res);
  },

  async upload(path, formData) {
    const res = await fetch(`${API_URL}${path}`, {
      method: "POST",
      credentials: "include",
      headers: authHeaders({}, true), // do NOT set Content-Type, browser sets boundary
      body: formData,
    });
    return handle(res);
  },

  async delete(path) {
    const res = await fetch(`${API_URL}${path}`, {
      method: "DELETE",
      credentials: "include",
      headers: authHeaders({}, true),
    });
    return handle(res);
  },

  async patch(path, body) {
    const res = await fetch(`${API_URL}${path}`, {
      method: "PATCH",
      credentials: "include",
      headers: authHeaders({ "Content-Type": "application/json" }, true),
      body: JSON.stringify(body),
    });
    return handle(res);
  },
};

const DIFFICULTY_LABELS = {
  easy: "Stage 1 — Easy",
  hard: "Stage 2 — Hard",
  difficult: "Stage 3 — Difficult",
  lecturer_style: "Question Pattern Trainer",
};

export function difficultyLabel(difficulty) {
  return (
    DIFFICULTY_LABELS[difficulty] ||
    (difficulty
      ? difficulty.charAt(0).toUpperCase() + difficulty.slice(1)
      : "")
  );
}

export function formatDuration(seconds) {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  if (h > 0) return `${h}h ${m}m`;
  if (m > 0) return `${m}m ${s}s`;
  return `${s}s`;
}

export function gradeFromPercentage(percentage) {
  if (percentage >= 80) return "A";
  if (percentage >= 70) return "B";
  if (percentage >= 60) return "C";
  if (percentage >= 50) return "D";
  return "F";
}

export function formatClock(totalSeconds) {
  const m = Math.floor(totalSeconds / 60);
  const s = Math.floor(totalSeconds % 60);
  return `${m}m ${s.toString().padStart(2, "0")}s`;
}

export function formatDate(isoString) {
  return new Date(isoString).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

/**
 * The JWT itself now lives in an HttpOnly cookie the frontend can't read
 * (that's the entire point of the F3 security change). Session-expiry
 * awareness is derived instead from the JS-readable CSRF cookie, which
 * flask-jwt-extended sets with the SAME expiry as the underlying JWT -
 * so its presence/absence and max-age are a reliable proxy without ever
 * exposing the actual token to JavaScript.
 */
export function isLoggedIn() {
  return Boolean(getCsrfToken());
}
