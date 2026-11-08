import axios, { type AxiosError, type InternalAxiosRequestConfig } from 'axios'
import type { ApiErrorResponse } from './types'

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 40000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request Interceptor: Attach current active API Key
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const storedKey = localStorage.getItem('verity_api_key') || 'verity-admin-secret-key'
    if (storedKey && config.headers) {
      config.headers['X-API-Key'] = storedKey
    }
    return config
  },
  (error) => Promise.reject(error)
)

// Response Interceptor: Format error messages consistently
apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError<ApiErrorResponse>) => {
    let message = 'An unexpected network error occurred.'
    if (error.response?.data?.error?.message) {
      message = error.response.data.error.message
    } else if (error.message) {
      message = error.message
    }
    return Promise.reject(new Error(message))
  }
)

export default apiClient
