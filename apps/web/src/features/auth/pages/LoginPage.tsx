import { zodResolver } from '@hookform/resolvers/zod'
import { Loader2 } from 'lucide-react'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { Link } from 'react-router'

import { FormField } from '@/components/forms/FormField'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { ROUTES } from '@/core/constants'
import { describeError } from '@/lib/api/errors'

import { AuthLayout } from '../components/AuthLayout'
import { FormAlert } from '../components/FormAlert'
import { useAuth } from '../hooks/use-auth'
import { type LoginValues, loginSchema } from '../schemas/auth-schemas'

/** Login page. On success, the route guard sends the user to the page they first asked for. */
export default function LoginPage() {
  const { login } = useAuth()
  const [formError, setFormError] = useState<string | null>(null)
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginValues>({ resolver: zodResolver(loginSchema) })

  const onSubmit = handleSubmit(async (values) => {
    setFormError(null)
    try {
      // On success <RedirectIfAuthenticated> sends the user on (to the page
      // they originally asked for, if any).
      await login(values)
    } catch (error) {
      setFormError(describeError(error))
    }
  })

  return (
    <AuthLayout title="Welcome back" subtitle="Sign in to continue to your knowledge base.">
      <form onSubmit={onSubmit} className="space-y-4" noValidate>
        {formError && <FormAlert message={formError} />}
        <FormField label="Email" error={errors.email?.message}>
          {(field) => (
            <Input
              {...field}
              type="email"
              autoComplete="email"
              placeholder="you@example.com"
              {...register('email')}
            />
          )}
        </FormField>
        <FormField label="Password" error={errors.password?.message}>
          {(field) => (
            <Input {...field} type="password" autoComplete="current-password" {...register('password')} />
          )}
        </FormField>
        <Button type="submit" size="lg" className="w-full" disabled={isSubmitting}>
          {isSubmitting && <Loader2 className="animate-spin" aria-hidden />}
          Sign in
        </Button>
      </form>
      <p className="mt-6 text-center text-xs text-muted-foreground">
        New to NeuralShelf?{' '}
        <Link to={ROUTES.signup} className="font-semibold text-primary hover:underline">
          Create an account
        </Link>
      </p>
    </AuthLayout>
  )
}
