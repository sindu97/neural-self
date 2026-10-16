/**
 * API types. Entities come from schema.d.ts, which is generated from the
 * backend's OpenAPI document (`npm run gen:api`), so they can't drift from
 * the real contract. Only the envelope and token shapes, which the backend
 * declares loosely, are written by hand.
 */
import type { components } from './schema'

type Schemas = components['schemas']

export type User = Schemas['UserResponse']
export type DocumentItem = Schemas['DocumentResponse']
export type DocumentStatus = Schemas['DocumentStatus']
export type SearchRequest = Schemas['SearchRequest']
export type SearchResult = Schemas['SearchResult']
export type Conversation = Schemas['ConversationResponse']
export type ChatMessage = Schemas['MessageResponse']
export type Citation = Schemas['Citation']
export type Exchange = Schemas['ExchangeResponse']
export type MessageCreateRequest = Schemas['MessageCreateRequest']
export type IngestionJob = Schemas['IngestionJobResponse']
export type JobStatus = Schemas['JobStatus']
export type JobStats = Schemas['JobStatsResponse']
export type BulkRetryResult = Schemas['BulkRetryResponse']
export type PaginationMeta = Schemas['PaginationMeta']

/** Every response: `data` is always a list. */
export interface ApiEnvelope<T> {
  success: boolean
  code: string
  message: string
  data: T[]
}

/** Response envelope for list endpoints, with pagination details. */
export interface PaginatedEnvelope<T> extends ApiEnvelope<T> {
  pagination: PaginationMeta
}

/** A page of items, unwrapped from its envelope. */
export interface Page<T> {
  items: T[]
  pagination: PaginationMeta
}

/** Offset pagination query parameters. */
export interface PageParams {
  limit?: number
  offset?: number
}

/** Login/refresh body for browsers (the refresh token is an httpOnly cookie). */
export interface SessionTokens {
  access_token: string
  token_type: 'bearer'
  expires_in: number
  refresh_expires_at: string
  user: User
}

/** One invalid field in a 422 validation error. */
export interface FieldError {
  field: string
  message: string
}
