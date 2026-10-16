import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'

import { API, envelope, errorEnvelope, sessionTokens } from '../../../../tests/msw/handlers'
import { server } from '../../../../tests/msw/server'
import { page, renderRoutes } from '../../../../tests/render'
import { RedirectIfAuthenticated, RequireAuth } from '../components/RequireAuth'
import LoginPage from '../pages/LoginPage'

const routes = [
  { element: <RedirectIfAuthenticated />, children: [{ path: '/login', element: <LoginPage /> }] },
  {
    element: <RequireAuth />,
    children: [
      { path: '/documents', element: page('Documents page') },
      { path: '/', element: page('Overview page') },
    ],
  },
]

describe('authentication flow', () => {
  it('sends anonymous users to login, then back to the page they wanted', async () => {
    server.use(http.post(`${API}/auth/login`, () => HttpResponse.json(envelope([sessionTokens()]))))
    renderRoutes(routes, '/documents')

    expect(await screen.findByRole('heading', { name: 'Welcome back' })).toBeInTheDocument()
    await userEvent.type(screen.getByLabelText('Email'), 'asha@example.com')
    await userEvent.type(screen.getByLabelText('Password'), 'CorrectHorse!42')
    await userEvent.click(screen.getByRole('button', { name: 'Sign in' }))

    expect(await screen.findByRole('heading', { name: 'Documents page' })).toBeInTheDocument()
  })

  it('restores the session from the refresh cookie on page load', async () => {
    server.use(http.post(`${API}/auth/refresh`, () => HttpResponse.json(envelope([sessionTokens()]))))
    renderRoutes(routes, '/documents')

    expect(await screen.findByRole('heading', { name: 'Documents page' })).toBeInTheDocument()
  })

  it('validates the form before calling the API', async () => {
    renderRoutes(routes, '/login')

    await userEvent.click(await screen.findByRole('button', { name: 'Sign in' }))

    expect(await screen.findByText('Enter a valid email address.')).toBeInTheDocument()
    expect(screen.getByText('Enter your password.')).toBeInTheDocument()
  })

  it('shows the server error for wrong credentials', async () => {
    server.use(
      http.post(`${API}/auth/login`, () =>
        HttpResponse.json(errorEnvelope('INVALID_CREDENTIALS', 'Invalid email or password.'), {
          status: 401,
        }),
      ),
    )
    renderRoutes(routes, '/login')

    await userEvent.type(await screen.findByLabelText('Email'), 'asha@example.com')
    await userEvent.type(screen.getByLabelText('Password'), 'nope-nope')
    await userEvent.click(screen.getByRole('button', { name: 'Sign in' }))

    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('Invalid email or password.'))
  })
})
