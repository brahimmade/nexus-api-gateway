import axios from 'axios'
import Cookies from 'js-cookie'
import toast from 'react-hot-toast'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

// Create axios instance
export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000, // 30 seconds
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor to add auth token
apiClient.interceptors.request.use(
  (config) => {
    const token = Cookies.get('access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor to handle errors
apiClient.interceptors.response.use(
  (response) => {
    return response
  },
  (error) => {
    if (error.response) {
      const { status, data } = error.response
      
      switch (status) {
        case 401:
          // Unauthorized - clear token and redirect to login
          Cookies.remove('access_token')
          if (typeof window !== 'undefined' && !window.location.pathname.includes('/auth/')) {
            window.location.href = '/auth/login'
          }
          break
        case 403:
          toast.error('Access denied. You do not have permission to perform this action.')
          break
        case 404:
          toast.error('Resource not found.')
          break
        case 422:
          // Validation errors
          if (data.detail && Array.isArray(data.detail)) {
            const errorMessages = data.detail.map((err: any) => err.msg).join(', ')
            toast.error(`Validation error: ${errorMessages}`)
          } else {
            toast.error(data.detail || 'Validation error occurred.')
          }
          break
        case 429:
          toast.error('Too many requests. Please try again later.')
          break
        case 500:
          toast.error('Internal server error. Please try again later.')
          break
        case 502:
        case 503:
        case 504:
          toast.error('Service temporarily unavailable. Please try again later.')
          break
        default:
          toast.error(data.detail || 'An unexpected error occurred.')
      }
    } else if (error.request) {
      // Network error
      toast.error('Network error. Please check your connection and try again.')
    } else {
      // Something else happened
      toast.error('An unexpected error occurred.')
    }
    
    return Promise.reject(error)
  }
)

// API endpoints
export const api = {
  // Authentication
  auth: {
    login: (credentials: { username: string; password: string }) => 
      apiClient.post('/auth/login', credentials, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
      }),
    register: (userData: any) => apiClient.post('/auth/register', userData),
    refreshToken: () => apiClient.post('/auth/refresh'),
  },
  
  // Users
  users: {
    getMe: () => apiClient.get('/users/me'),
    getAll: (params?: any) => apiClient.get('/users/', { params }),
    getById: (id: string) => apiClient.get(`/users/${id}`),
    update: (id: string, data: any) => apiClient.put(`/users/${id}`, data),
    delete: (id: string) => apiClient.delete(`/users/${id}`),
    changePassword: (data: { current_password: string; new_password: string }) => 
      apiClient.post('/users/change-password', data),
  },
  
  // Health check
  health: {
    check: () => apiClient.get('/health'),
    metrics: () => apiClient.get('/metrics'),
  },
}

export default apiClient