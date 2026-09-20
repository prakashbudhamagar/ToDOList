// Thin fetch wrapper for the Django REST API mounted at /api/.
// In development Vite proxies /api/* to http://127.0.0.1:8000 (see
// vite.config.js) and in Docker nginx does the same, so the browser always talks
// to a single origin.
const API_BASE = '/api'

function getCookie(name) {
  const match = document.cookie.match(new RegExp(`(^|;\\s*)${name}=([^;]*)`))
  return match ? decodeURIComponent(match[2]) : null
}

// DRF enforces CSRF for session-authenticated requests (e.g. when you are also
// logged into /admin/ in the same browser), so make sure Django has set the
// csrftoken cookie and echo it back in the X-CSRFToken header.
async function csrfToken() {
  if (!getCookie('csrftoken')) {
    await fetch(`${API_BASE}/csrf/`, { credentials: 'same-origin' })
  }
  return getCookie('csrftoken')
}

/**
 * Performs a JSON request against the API and throws an Error with the response
 * detail when Django answers with a 4xx/5xx status.
 */
export async function request(path, { method = 'GET', body } = {}) {
  const headers = {}
  if (body !== undefined) {
    headers['Content-Type'] = 'application/json'
  }
  if (method !== 'GET') {
    const token = await csrfToken()
    if (token) {
      headers['X-CSRFToken'] = token
    }
  }

  const response = await fetch(`${API_BASE}${path}`, {
    method,
    body,
    headers,
    credentials: 'same-origin',
  })

  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`
    try {
      detail = JSON.stringify(await response.json())
    } catch {
      // response body was not JSON - keep the status text
    }
    throw new Error(detail)
  }

  return response.status === 204 ? null : response.json()
}
