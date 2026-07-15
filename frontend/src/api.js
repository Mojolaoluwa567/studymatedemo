export const API_URL = import.meta.env.VITE_API_URL || "http://localhost:5000";

function authHeaders(extra = {}) {
  const token = localStorage.getItem("token");
  return {
    ...extra,
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

async function handle(response) {
  let data;
  try {
    data = await response.json();
  } catch {
    data = null;
  }
  if (!response.ok) {
    // Errors come in two shapes depending on which part of the backend
    // produced them: most routes return a plain string ({"error": "..."}),
    // but the global 404/429/500 handlers return a structured object
    // ({"error": {"code": "...", "message": "..."}}). Handle both so a
    // real server error never renders as the literal text "[object Object]".
    let message = "Something went wrong.";
    if (typeof data?.error === "string") {
      message = data.error;
    } else if (data?.error?.message) {
      message = data.error.message;
    } else if (data?.msg) {
      message = data.msg;
    }
    const error = new Error(message);
    error.status = response.status;
    error.code = data?.error?.code;
    throw error;
  }
  return data;
}

export const api = {
  async post(path, body) {
    const res = await fetch(`${API_URL}${path}`, {
      method: "POST",
      headers: authHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify(body),
    });
    return handle(res);
  },

  async get(path) {
    const res = await fetch(`${API_URL}${path}`, {
      method: "GET",
      headers: authHeaders(),
    });
    return handle(res);
  },

  async upload(path, formData) {
    const res = await fetch(`${API_URL}${path}`, {
      method: "POST",
      headers: authHeaders(),
      body: formData,
    });
    return handle(res);
  },

  async delete(path) {
    const res = await fetch(`${API_URL}${path}`, {
      method: "DELETE",
      headers: authHeaders(),
    });
    return handle(res);
  },

  async patch(path, body) {
    const res = await fetch(`${API_URL}${path}`, {
      method: "PATCH",
      headers: authHeaders({ "Content-Type": "application/json" }),
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
    (difficulty ? difficulty.charAt(0).toUpperCase() + difficulty.slice(1) : "")
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

export function getTokenExpiry(token) {
  if (!token) return null;
  try {
    const payloadPart = token.split(".")[1];
    const json = JSON.parse(
      atob(payloadPart.replace(/-/g, "+").replace(/_/g, "/")),
    );
    return json.exp ? new Date(json.exp * 1000) : null;
  } catch {
    return null;
  }
}
