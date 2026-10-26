// Thin wrapper around fetch for the BBMS API. Every request sends the session token;
// a 401 means the session expired (BBS-SR-005), so the app logs the user out.

const TOKEN_KEY = "bbms.session";

export function loadSession() {
  try {
    return JSON.parse(sessionStorage.getItem(TOKEN_KEY));
  } catch {
    return null;
  }
}

export function saveSession(session) {
  try {
    if (session) sessionStorage.setItem(TOKEN_KEY, JSON.stringify(session));
    else sessionStorage.removeItem(TOKEN_KEY);
  } catch {
    // Storage blocked (e.g. private mode): the session just won't survive a reload.
  }
}

export class ApiError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
  }
}

let onUnauthorized = () => {};
export function setUnauthorizedHandler(handler) {
  onUnauthorized = handler;
}

// FastAPI errors come as a string, a list of validation errors, or an object.
function describe(detail, fallback) {
  if (!detail) return fallback;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) return detail.map((d) => d.msg).join("; ");
  if (detail.reasons) return detail.reasons.join("; ");
  return fallback;
}

export async function api(path, { method = "GET", body, token } = {}) {
  const headers = { Accept: "application/json" };
  const auth = token ?? loadSession()?.token;
  if (auth) headers.Authorization = `Bearer ${auth}`;
  if (body !== undefined) headers["Content-Type"] = "application/json";

  const response = await fetch(path, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
  });

  if (response.status === 204) return null;
  const data = await response.json().catch(() => null);
  if (!response.ok) {
    if (response.status === 401 && auth) onUnauthorized();
    throw new ApiError(response.status, describe(data?.detail, `Request failed (${response.status})`));
  }
  return data;
}

// Load several endpoints at once. A failing one gives `null` plus its error, so one
// missing piece (e.g. no donor profile yet) doesn't blank the whole dashboard.
export async function loadAll(requests) {
  const entries = Object.entries(requests);
  const results = await Promise.allSettled(entries.map(([, path]) => api(path)));
  const data = {};
  const errors = {};
  results.forEach((result, i) => {
    const key = entries[i][0];
    if (result.status === "fulfilled") data[key] = result.value;
    else {
      data[key] = null;
      errors[key] = result.reason;
    }
  });
  return { data, errors };
}
