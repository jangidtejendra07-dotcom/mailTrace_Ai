import axios from 'axios'

const api = axios.create({
  baseURL: 'https://mailtrace-ai-backend.onrender.com/api/v1',
})

// Attach the JWT to every outgoing request, if we have one
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('mailtrace_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// If the token is invalid/expired, boot the user back to login
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error?.response?.status === 401) {
      localStorage.removeItem('mailtrace_token')
      localStorage.removeItem('mailtrace_user')
      if (!window.location.pathname.startsWith('/login')) {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

// ---------- Auth ----------
export async function registerUser({ email, password, full_name }) {
  const { data } = await api.post('/auth/register', { email, password, full_name })
  return data
}

export async function loginUser({ email, password }) {
  const { data } = await api.post('/auth/login', { email, password })
  return data
}

export async function fetchMe() {
  const { data } = await api.get('/auth/me')
  return data
}

// ---------- Email analysis ----------
export async function analyzeEmail(file) {
  const formData = new FormData()
  formData.append('email_file', file)
  const { data } = await api.post('/analyze-email', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

// ---------- Cases ----------
export async function listCases() {
  const { data } = await api.get('/cases')
  return data
}

export async function getCase(caseId) {
  const { data } = await api.get(`/cases/${caseId}`)
  return data
}

export function reportUrl(caseId) {
  const token = localStorage.getItem('mailtrace_token')
  return `/api/v1/cases/${caseId}/report?token=${encodeURIComponent(token || '')}`
}

// ---------- Gmail ----------
export async function getGmailStatus() {
  const { data } = await api.get('/gmail/status')
  return data
}

export async function getGmailAuthUrl() {
  const { data } = await api.get('/gmail/connect')
  return data
}

export async function syncGmail() {
  const { data } = await api.post('/gmail/sync')
  return data
}

export async function disconnectGmail() {
  const { data } = await api.post('/gmail/disconnect')
  return data
}

export async function startRealtimeWatch() {
  const { data } = await api.post('/gmail/watch/start')
  return data
}

export async function stopRealtimeWatch() {
  const { data } = await api.post('/gmail/watch/stop')
  return data
}

// ---------- Quarantine ----------
export async function listQuarantinedCases() {
  const { data } = await api.get('/cases/quarantined')
  return data
}

export async function releaseCase(caseId) {
  const { data } = await api.post(`/cases/${caseId}/release`)
  return data
}

export default api
