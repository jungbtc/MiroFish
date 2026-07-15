import axios from 'axios'
import i18n from '../i18n'
import { requestWithRetry } from './retry'

export { requestWithRetry }

// 创建axios实例
const service = axios.create({
  // Relative-by-default keeps browser traffic behind the trusted same-origin
  // dev/deployment proxy instead of exposing a private API key to JavaScript.
  baseURL: import.meta.env.VITE_API_BASE_URL || '',
  timeout: 300000, // 5分钟超时（本体生成可能需要较长时间）
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器
service.interceptors.request.use(
  config => {
    config.headers['Accept-Language'] = i18n.global.locale.value
    return config
  },
  error => {
    console.error('Request error:', error)
    return Promise.reject(error)
  }
)

// 响应拦截器（统一标准化错误信息，重试策略位于 retry.js）
service.interceptors.response.use(
  response => {
    const res = response.data
    
    // 如果返回的状态码不是success，则抛出错误
    if (!res.success && res.success !== undefined) {
      console.error('API Error:', res.error || res.message || 'Unknown error')
      const apiError = new Error(res.error || res.message || 'Error')
      apiError.method = response.config?.method
      apiError.status = response.status
      apiError.code = res.code
      apiError.traceback = res.traceback
      return Promise.reject(apiError)
    }
    
    return res
  },
  error => {
    console.error('Response error:', error)
    const backendError = error.response?.data?.error || error.response?.data?.message
    if (backendError) {
      const detailedError = new Error(backendError)
      detailedError.method = error.config?.method
      detailedError.status = error.response?.status
      detailedError.code = error.code
      detailedError.traceback = error.response?.data?.traceback
      return Promise.reject(detailedError)
    }
    
    // 处理超时
    if (error.code === 'ECONNABORTED' && error.message.includes('timeout')) {
      console.error('Request timeout')
    }
    
    // 处理网络错误
    if (error.message === 'Network Error') {
      console.error('Network error - please check your connection')
    }
    
    return Promise.reject(error)
  }
)

export default service
