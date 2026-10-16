import axios from 'axios'

import { REQUEST_ID_HEADER } from '@/core/constants'

import type { FieldError } from './types'

/** Error codes the UI branches on. The full list is in backend/API.md. */
export type ApiErrorCode =
  | 'UNAUTHORIZED'
  | 'INVALID_CREDENTIALS'
  | 'INVALID_REFRESH_TOKEN'
  | 'CSRF_CHECK_FAILED'
  | 'FORBIDDEN'
  | 'NOT_FOUND'
  | 'DOCUMENT_NOT_FOUND'
  | 'CONVERSATION_NOT_FOUND'
  | 'JOB_NOT_FOUND'
  | 'EMAIL_ALREADY_REGISTERED'
  | 'DOCUMENT_BUSY'
  | 'JOB_NOT_FAILED'
  | 'FILE_TOO_LARGE'
  | 'VALIDATION_ERROR'
  | 'INVALID_FILE'
  | 'RATE_LIMITED'
  | 'INTERNAL_SERVER_ERROR'
  | 'EMBEDDING_SERVICE_UNAVAILABLE'
  | 'LLM_SERVICE_UNAVAILABLE'
  | 'NETWORK_ERROR'
  | (string & {})

/** One error type for the whole app, built from the backend's error envelope. */
export class ApiError extends Error {
  readonly status: number
  readonly code: ApiErrorCode
  readonly fieldErrors: FieldError[]
  readonly requestId: string | null
  readonly retryAfterSeconds: number | null

  constructor(options: {
    status: number
    code: ApiErrorCode
    message: string
    fieldErrors?: FieldError[]
    requestId?: string | null
    retryAfterSeconds?: number | null
  }) {
    super(options.message)
    this.name = 'ApiError'
    this.status = options.status
    this.code = options.code
    this.fieldErrors = options.fieldErrors ?? []
    this.requestId = options.requestId ?? null
    this.retryAfterSeconds = options.retryAfterSeconds ?? null
  }

  is(...codes: ApiErrorCode[]): boolean {
    return codes.includes(this.code)
  }
}

interface ErrorEnvelope {
  code?: string
  message?: string
  data?: unknown
}

function isFieldErrorList(value: unknown): value is FieldError[] {
  return (
    Array.isArray(value) &&
    value.every((item) => typeof item === 'object' && item !== null && 'field' in item)
  )
}

/** Build an ApiError from a status, headers and (possibly non-JSON) body. */
export function apiErrorFromResponse(
  status: number,
  body: unknown,
  headers: { get(name: string): string | null | undefined },
): ApiError {
  const envelope = (typeof body === 'object' && body !== null ? body : {}) as ErrorEnvelope
  const retryAfter = Number(headers.get('retry-after'))
  return new ApiError({
    status,
    code: envelope.code ?? (status >= 500 ? 'INTERNAL_SERVER_ERROR' : 'HTTP_ERROR'),
    message: envelope.message ?? 'Something went wrong. Please try again.',
    fieldErrors: isFieldErrorList(envelope.data) ? envelope.data : [],
    requestId: headers.get(REQUEST_ID_HEADER) ?? null,
    retryAfterSeconds: Number.isFinite(retryAfter) && retryAfter > 0 ? retryAfter : null,
  })
}

/** Normalise anything thrown by Axios, fetch or our code into an ApiError. */
export function toApiError(error: unknown): ApiError {
  if (error instanceof ApiError) return error

  if (axios.isAxiosError(error)) {
    if (error.response) {
      const responseHeaders = error.response.headers
      return apiErrorFromResponse(error.response.status, error.response.data, {
        get: (name) => {
          const value: unknown = responseHeaders[name]
          return typeof value === 'string' ? value : null
        },
      })
    }
    return networkError()
  }

  if (error instanceof TypeError) return networkError() // fetch network failure

  return new ApiError({
    status: 0,
    code: 'INTERNAL_SERVER_ERROR',
    message: error instanceof Error ? error.message : 'Something went wrong.',
  })
}

function networkError(): ApiError {
  return new ApiError({
    status: 0,
    code: 'NETWORK_ERROR',
    message: 'Cannot reach NeuralShelf. Check your connection and try again.',
  })
}

/** A short, user-facing description, e.g. for toasts. */
export function describeError(error: unknown): string {
  const apiError = toApiError(error)
  if (apiError.is('RATE_LIMITED') && apiError.retryAfterSeconds) {
    return `${apiError.message} Try again in ${apiError.retryAfterSeconds}s.`
  }
  return apiError.message
}
