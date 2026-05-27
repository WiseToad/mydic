import axios from 'axios'

export const apiClient = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
})

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('mydicToken')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Expose 401 handler so auth store can react to expired tokens
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 && localStorage.getItem('mydicToken')) {
      localStorage.removeItem('mydicToken')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  },
)
