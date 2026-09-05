import axios from 'axios'

const http = axios.create({
  baseURL: '/api',
  timeout: 180000,
})

http.interceptors.response.use(
  (res) => res,
  (err) => {
    const detail = err?.response?.data?.detail
    return Promise.reject(new Error(typeof detail === 'string' ? detail : detail?.map((d: any) => d.msg).join('; ') || err.message))
  },
)

export default http