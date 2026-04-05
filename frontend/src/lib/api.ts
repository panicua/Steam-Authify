import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('steam_token')
  if (token) {
    config.headers['Authorization'] = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      const url: string = error.config?.url || ''
      // Don't log out on Steam session/confirmation errors — those are Steam auth failures, not app auth
      const isSteamEndpoint = url.includes('/session/') || url.includes('/confirmations')
      if (!isSteamEndpoint) {
        localStorage.removeItem('steam_token')
        localStorage.removeItem('steam_user')
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

// --- Auth ---
export const auth = {
  telegram: (data: Record<string, unknown>) => api.post('/auth/telegram', data),
  me: () => api.get('/auth/me'),
}

// --- Steam Accounts ---
export const accounts = {
  list: () => api.get('/accounts'),
  get: (id: number) => api.get(`/accounts/${id}`),
  create: (data: Record<string, unknown>) => api.post('/accounts', data),
  upload: (file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post('/accounts/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  delete: (id: number) => api.delete(`/accounts/${id}`),
  getCode: (id: number) => api.get(`/accounts/${id}/code`),
  generate: (shared_secret: string) => api.post('/accounts/generate', { shared_secret }),
}

// --- Confirmations ---
export const confirmations = {
  list: (accountId: number) => api.get(`/accounts/${accountId}/confirmations`),
  accept: (accountId: number, confId: string) =>
    api.post(`/accounts/${accountId}/confirmations/${confId}/accept`),
  decline: (accountId: number, confId: string) =>
    api.post(`/accounts/${accountId}/confirmations/${confId}/decline`),
  batch: (accountId: number, data: { confirmation_ids: string[]; action: 'accept' | 'decline' }) =>
    api.post(`/accounts/${accountId}/confirmations/batch`, data),
}

// --- Steam Sessions ---
export const sessions = {
  login: (accountId: number, password: string) =>
    api.post(`/accounts/${accountId}/session/login`, { password }),
  logout: (accountId: number) =>
    api.post(`/accounts/${accountId}/session/logout`),
  status: (accountId: number) =>
    api.get(`/accounts/${accountId}/session/status`),
}

// --- Users (admin) ---
export const users = {
  list: () => api.get('/users'),
  update: (id: number, data: Record<string, unknown>) => api.patch(`/users/${id}`, data),
  delete: (id: number) => api.delete(`/users/${id}`),
}

export default api
