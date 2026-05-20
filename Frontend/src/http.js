const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export function createHttpError(message, status, data = null, extra = {}) {
  const error = new Error(message)
  error.status = status
  error.data = data
  Object.assign(error, extra)
  return error
}

async function parseResponseBody(response) {
  if (response.status === 204) {
    return null
  }

  const text = await response.text()
  if (!text) {
    return null
  }

  try {
    return JSON.parse(text)
  } catch {
    return text
  }
}

export function parseErrorMessage(data, fallback = 'Ошибка запроса') {
  if (typeof data === 'string' && data.trim()) {
    return data
  }

  const detail = data?.detail ?? fallback

  if (Array.isArray(detail)) {
    return detail[0]?.msg ?? fallback
  }

  if (typeof detail === 'string' && detail.trim()) {
    return detail
  }

  return fallback
}

export async function baseRequest(path, options = {}, token) {
  const headers = {
    ...(options.headers ?? {}),
  }

  const hasContentType = Object.keys(headers).some((key) => key.toLowerCase() === 'content-type')
  if (!(options.body instanceof FormData) && !hasContentType) {
    headers['Content-Type'] = 'application/json'
  }

  if (token) {
    headers.Authorization = `Bearer ${token}`
  }

  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers,
  })

  const data = await parseResponseBody(response)

  if (!response.ok) {
    throw createHttpError(parseErrorMessage(data), response.status, data)
  }

  return data
}
