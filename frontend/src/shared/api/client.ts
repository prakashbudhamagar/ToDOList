const API_BASE = '/api'

type HttpMethod = 'GET' | 'POST' | 'PATCH' | 'PUT' | 'DELETE'

interface RequestOptions {
  method?: HttpMethod
  body?: string
}

function getCookie(name: string): string | null {
  const match = document.cookie.match(new RegExp(`(^|;\\s*)${name}=([^;]*)`))
  return match ? decodeURIComponent(match[2]) : null
}

async function csrfToken(): Promise<string | null> {
  if (!getCookie('csrftoken')) {
    await fetch(`${API_BASE}/csrf/`, { credentials: 'same-origin' })
  }
  return getCookie('csrftoken')
}

export function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error)
}

export async function request<T>(
  path: string,
  { method = 'GET', body }: RequestOptions = {},
): Promise<T> {
  const headers: Record<string, string> = {}
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
    }
    throw new Error(detail)
  }

  return (response.status === 204 ? null : await response.json()) as T
}
