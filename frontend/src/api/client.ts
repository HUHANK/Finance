import axios from 'axios'

export const http = axios.create({ baseURL: '/api', timeout: 60000 })
// 重接口（一致预期等逐股抓取，可能 30 秒+）
export const httpLong = axios.create({ baseURL: '/api', timeout: 180000 })

export function errMsg(e: unknown): string {
  const err = e as { response?: { data?: { detail?: string } }; message?: string }
  return err?.response?.data?.detail || err?.message || String(e)
}
