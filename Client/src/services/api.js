// One place for every backend call.
// Base URL comes from .env (VITE_API_URL), e.g. http://127.0.0.1:8000/api
// A trailing "/" is removed so we never build URLs like /api//crops/.
const API_URL = (import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api').replace(/\/+$/, '');

// Error with the backend's message + field errors attached
export class ApiError extends Error {
  constructor(message, status, errors = {}) {
    super(message);
    this.status = status;
    this.errors = errors; // e.g. { email: ["Enter a valid email."] }
  }
}

// Turn the backend's { errors: {...} } into one readable line
export function firstFieldError(errors) {
  if (!errors || typeof errors !== 'object') return '';
  for (const value of Object.values(errors)) {
    if (Array.isArray(value) && value.length) return String(value[0]);
    if (typeof value === 'string') return value;
    if (value && typeof value === 'object') {
      const nested = firstFieldError(value);
      if (nested) return nested;
    }
  }
  return '';
}

async function request(path, { method = 'GET', body, auth = false } = {}) {
  // FormData (file uploads): let the browser set the multipart Content-Type itself
  const isForm = body instanceof FormData;
  const headers = isForm ? {} : { 'Content-Type': 'application/json' };

  if (auth) {
    const token = localStorage.getItem('token');
    if (token) headers.Authorization = `Token ${token}`;
  }

  let response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      method,
      headers,
      body: isForm ? body : body ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new ApiError(
      'Cannot reach the server. Is the backend running (python manage.py runserver)?',
      0
    );
  }

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    const detail = firstFieldError(data.errors);
    const message = data.message || `Request failed (${response.status})`;
    throw new ApiError(detail ? `${message} ${detail}` : message, response.status, data.errors);
  }
  return data;
}

/* ---------------- Data APIs ---------------- */

// GET /api/health/  -> { status, message, timestamp }
export const getHealth = () => request('/health/');

// GET /api/locations/  -> { count, results: [{ slug, name, lat, lon, country, zone, tier, featured }] }
export const getLocations = () => request('/locations/');

// GET /api/crops/  -> { count, results: [{ slug, name, name_ur, family, role, ... }] }
export const getCrops = () => request('/crops/');

// POST /api/analyze/  -> full analysis (strategies, climate, soil, alerts, ...)
export const analyzeFarm = (payload) => request('/analyze/', { method: 'POST', body: payload });

// POST /api/explain/  -> { explanation, recommended_strategy, overall_score }
export const explainAnalysis = (analysis, lang = 'en') =>
  request('/explain/', { method: 'POST', body: { analysis, lang } });

// POST /api/chat/  -> { reply }
// `messages` = the whole conversation [{ role: 'user' | 'assistant', content }],
// ending with the farmer's newest question (a plain string also works).
export const sendChatMessage = (messages, analysis = null, lang = 'en') =>
  request('/chat/', {
    method: 'POST',
    body: typeof messages === 'string'
      ? { message: messages, analysis, lang }
      : { messages, analysis, lang },
  });

/* ---------------- Auth APIs ---------------- */

// POST /api/auth/signup/  -> { user, token }
export const signup = ({ fullName, email, password, confirmPassword }) =>
  request('/auth/signup/', {
    method: 'POST',
    body: {
      full_name: fullName,
      email,
      password,
      confirm_password: confirmPassword,
    },
  });

// POST /api/auth/login/  -> { user, token }
export const login = ({ email, password }) =>
  request('/auth/login/', { method: 'POST', body: { email, password } });

// POST /api/auth/logout/  (needs token)
export const logout = () => request('/auth/logout/', { method: 'POST', auth: true });

// GET /api/auth/me/  (needs token) -> { user }
export const getMe = () => request('/auth/me/', { auth: true });

// POST /api/auth/profile-picture/  (needs token, multipart) -> { user } with profile_picture URL
export const uploadProfilePicture = (file) => {
  const form = new FormData();
  form.append('profile_picture', file);
  return request('/auth/profile-picture/', { method: 'POST', body: form, auth: true });
};

// DELETE /api/auth/profile-picture/  (needs token) -> { user }
export const removeProfilePicture = () =>
  request('/auth/profile-picture/', { method: 'DELETE', auth: true });
