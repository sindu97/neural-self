export const ROUTES = {
  login: '/login',
  signup: '/signup',
  overview: '/',
  documents: '/documents',
  chat: '/chat',
  conversation: (id: string) => `/chat/${id}`,
  search: '/search',
  activity: '/activity',
  settings: '/settings',
  adminJobs: '/admin/jobs',
} as const

/** Must match the backend's limits (see backend/API.md). */
export const LIMITS = {
  maxUploadBytes: 20 * 1024 * 1024,
  maxQuestionLength: 4000,
  maxSearchLength: 2000,
  maxTopK: 20,
} as const

/** Poll documents while any is still being processed. */
export const DOCUMENT_POLL_INTERVAL_MS = 2500

/** Headers the backend expects (see backend/API.md, Authentication). */
export const CSRF_HEADER = 'X-NeuralShelf-CSRF'
export const REQUEST_ID_HEADER = 'x-request-id'
