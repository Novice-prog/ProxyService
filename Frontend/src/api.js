import { computed, ref } from 'vue'
import { baseRequest, createHttpError } from './http'

const accessToken = ref(localStorage.getItem('access_token'))
const refreshToken = ref(localStorage.getItem('refresh_token'))

let router = null
let refreshRequestPromise = null

export const isAuthenticated = computed(() => Boolean(accessToken.value))

export function setRouter(nextRouter) {
  router = nextRouter
}

function getAccessToken() {
  return accessToken.value
}

function redirectToLogin() {
  if (!router || router.currentRoute.value.path === '/login') {
    return
  }

  router.replace('/login')
}

function buildUnauthorizedError(message = 'Сессия истекла. Войдите снова', data = null) {
  return createHttpError(message, 401, data, { handled: true })
}

function saveTokens(data) {
  localStorage.setItem('access_token', data.access_token)
  localStorage.setItem('refresh_token', data.refresh_token)
  accessToken.value = data.access_token
  refreshToken.value = data.refresh_token
}

function clearTokens() {
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
  accessToken.value = null
  refreshToken.value = null
}

async function refreshAccessToken() {
  if (!refreshToken.value) {
    clearTokens()
    redirectToLogin()
    throw buildUnauthorizedError()
  }

  if (!refreshRequestPromise) {
    refreshRequestPromise = baseRequest('/auth/refresh', {
      method: 'POST',
      body: JSON.stringify({ refresh_token: refreshToken.value }),
    })
      .then((data) => {
        localStorage.setItem('access_token', data.access_token)
        accessToken.value = data.access_token
        return data.access_token
      })
      .catch((error) => {
        if (error.status === 401) {
          clearTokens()
          redirectToLogin()
          throw buildUnauthorizedError()
        }

        throw error
      })
      .finally(() => {
        refreshRequestPromise = null
      })
  }

  return refreshRequestPromise
}

async function authRequest(path, options = {}, retry = true) {
  try {
    return await baseRequest(path, options, getAccessToken())
  } catch (error) {
    if (error.status !== 401) {
      throw error
    }

    if (!retry) {
      clearTokens()
      redirectToLogin()
      throw buildUnauthorizedError()
    }

    await refreshAccessToken()
    return authRequest(path, options, false)
  }
}

export const api = {
  register(payload) {
    return baseRequest('/auth/register', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },

  async login(payload) {
    const data = await baseRequest('/auth/login', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
    saveTokens(data)
    return data
  },

  profile() {
    return authRequest('/profile')
  },

  refreshKey() {
    return authRequest('/profile/refresh-key', {
      method: 'POST',
    })
  },

  changePassword(payload) {
    return authRequest('/profile/change-password', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },

  logout() {
    clearTokens()
  },
}
