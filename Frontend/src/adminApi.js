import { computed, ref } from 'vue'
import { baseRequest, createHttpError } from './http'

const adminAccessToken = ref(localStorage.getItem('admin_access_token'))
const adminRefreshToken = ref(localStorage.getItem('admin_refresh_token'))

let adminRouter = null

export const isAdminAuthenticated = computed(() => Boolean(adminAccessToken.value))

export function setAdminRouter(nextRouter) {
  adminRouter = nextRouter
}

function saveAdminTokens(data) {
  localStorage.setItem('admin_access_token', data.access_token)
  localStorage.setItem('admin_refresh_token', data.refresh_token)
  adminAccessToken.value = data.access_token
  adminRefreshToken.value = data.refresh_token
}

export function clearAdminTokens() {
  localStorage.removeItem('admin_access_token')
  localStorage.removeItem('admin_refresh_token')
  adminAccessToken.value = null
  adminRefreshToken.value = null
}

function redirectToAdminLogin() {
  if (!adminRouter || adminRouter.currentRoute.value.path === '/admin/login') {
    return
  }

  adminRouter.replace('/admin/login')
}

function handleAdminUnauthorized(message = 'Сессия администратора истекла. Войдите снова', data = null) {
  clearAdminTokens()
  redirectToAdminLogin()
  return createHttpError(message, 401, data, { handled: true })
}

async function adminRequest(path, options = {}) {
  try {
    return await baseRequest(path, options, adminAccessToken.value)
  } catch (error) {
    if (error.status === 401) {
      throw handleAdminUnauthorized(error.message, error.data)
    }

    throw error
  }
}

export const adminApi = {
  async login(payload) {
    const data = await baseRequest('/auth/admin/login', {
      method: 'POST',
      body: JSON.stringify(payload),
    })

    saveAdminTokens(data)
    return data
  },

  logout() {
    clearAdminTokens()
  },

  listVms() {
    return adminRequest('/admin/virtual-machines')
  },

  createVm(payload) {
    return adminRequest('/admin/virtual-machines', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },

  updateVm(vmId, payload) {
    return adminRequest(`/admin/virtual-machines/${vmId}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    })
  },

  releaseVm(vmId) {
    return adminRequest(`/admin/virtual-machines/${vmId}/release`, {
      method: 'POST',
    })
  },

  deleteVm(vmId) {
    return adminRequest(`/admin/virtual-machines/${vmId}`, {
      method: 'DELETE',
    })
  },
}
