/**
 * The shared HTTP client. Every feature's api/ module uses it, so auth,
 * refresh-on-401 and error normalisation happen in exactly one place.
 */
import axios, { type AxiosRequestConfig, type InternalAxiosRequestConfig } from 'axios'

import { env } from '@/core/config/env'

import { toApiError } from './errors'
import { getAccessToken, notifySessionExpired, refreshSession } from './session'
import type { ApiEnvelope, Page, PaginatedEnvelope } from './types'

export const http = axios.create({
  baseURL: env.apiBaseUrl,
  withCredentials: true, // send the httpOnly refresh cookie to /auth/*
  timeout: 60_000,
})

http.interceptors.request.use((config) => {
  const token = getAccessToken()
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

type RetriableConfig = InternalAxiosRequestConfig & { _retried?: boolean }

http.interceptors.response.use(
  (response) => response,
  async (error: unknown) => {
    const apiError = toApiError(error)
    const config = axios.isAxiosError(error) ? (error.config as RetriableConfig | undefined) : undefined

    // Access token expired: refresh once, then replay the original request.
    // Auth endpoints are excluded so a failed login can't loop.
    if (apiError.is('UNAUTHORIZED') && config && !config._retried && !config.url?.startsWith('/auth/')) {
      config._retried = true
      try {
        await refreshSession()
      } catch {
        notifySessionExpired()
        throw apiError
      }
      return http.request(config)
    }

    throw apiError
  },
)

// ---- helpers that unwrap the backend envelope ------------------------------

/** GET a single item and unwrap it from the response envelope. */
export async function getOne<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
  const response = await http.get<ApiEnvelope<T>>(url, config)
  return firstItem(response.data)
}

/** GET a list and unwrap it from the response envelope. */
export async function getList<T>(url: string, config?: AxiosRequestConfig): Promise<T[]> {
  const response = await http.get<ApiEnvelope<T>>(url, config)
  return response.data.data
}

/** GET a paginated list: its items and pagination details. */
export async function getPage<T>(url: string, config?: AxiosRequestConfig): Promise<Page<T>> {
  const response = await http.get<PaginatedEnvelope<T>>(url, config)
  return { items: response.data.data, pagination: response.data.pagination }
}

/** POST and unwrap the single item in the response. */
export async function postOne<T>(url: string, body?: unknown, config?: AxiosRequestConfig): Promise<T> {
  const response = await http.post<ApiEnvelope<T>>(url, body, config)
  return firstItem(response.data)
}

/** POST and unwrap the list in the response. */
export async function postList<T>(url: string, body?: unknown, config?: AxiosRequestConfig): Promise<T[]> {
  const response = await http.post<ApiEnvelope<T>>(url, body, config)
  return response.data.data
}

/** DELETE a resource. */
export async function remove(url: string): Promise<void> {
  await http.delete(url)
}

function firstItem<T>(envelope: ApiEnvelope<T>): T {
  const item = envelope.data[0]
  if (item === undefined) {
    throw toApiError(new Error(`Expected one item in the response: ${envelope.message}`))
  }
  return item
}
