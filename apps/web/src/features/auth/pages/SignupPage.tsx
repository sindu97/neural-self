import { zodResolver } from '@hookform/resolvers/zod'
import { Loader2 } from 'lucide-react'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { Link } from 'react-router'

import { FormField } from '@/components/forms/FormField'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { ROUTES } from '@/core/constants'
import { describeError, toApiError } from '@/lib/api/errors'

import { AuthLayout } from '../components/AuthLayout'
import { FormAlert } from '../components/FormAlert'
import { useAuth } from '../hooks/use-auth'
import { type SignupValues, signupSchema } from '../schemas/auth-schemas'

/** Signup page: creates the account, then logs in. Server field errors appear next to the fields. */
export default function SignupPage() {
  const { signup } = useAuth()
  const [formError, setFormError] = useState<string | null>(null)
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<SignupValues>({ resolver: zodResolver(signupSchema) })

  const onSubmit = handleSubmit(async (values) => {
    setFormError(null)
    try {
      await signup(values) // then <RedirectIfAuthenticated> takes over
    } catch (error) {
      const apiError = toApiError(error)
      if (apiError.is('EMAIL_ALREADY_REGISTERED')) {
        setError('email', { message: apiError.message })
        return
      }
      // Show the backend's per-field validation messages next to the fields.
      let mapped = false
      for (const fieldError of apiError.fieldErrors) {
        if (fieldError.field === 'name' || fieldError.field === 'email' || fieldError.field === 'password') {
          setError(fieldError.field, { message: fieldError.message })
          mapped = true
        }
      }
      if (!mapped) setFormError(describeError(apiError))
    }
  })

  return (
    <AuthLayout title="Create your shelf" subtitle="Start organising your documents in a minute.">
      <form onSubmit={onSubmit} className="space-y-4" noValidate>
        {formError && <FormAlert message={formError} />}
        <FormField label="Full name" error={errors.name?.message}>
          {(field) => <Input {...field} autoComplete="name" placeholder="Asha Verma" {...register('name')} />}
        </FormField>
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
        <FormField label="Password" error={errors.password?.message} hint="At least 8 characters.">
          {(field) => (
            <Input {...field} type="password" autoComplete="new-password" {...register('password')} />
          )}
        </FormField>
        <FormField label="Confirm password" error={errors.confirmPassword?.message}>
          {(field) => (
            <Input {...field} type="password" autoComplete="new-password" {...register('confirmPassword')} />
          )}
        </FormField>
        <Button type="submit" size="lg" className="w-full" disabled={isSubmitting}>
          {isSubmitting && <Loader2 className="animate-spin" aria-hidden />}
          Create account
        </Button>
      </form>
      <p className="mt-6 text-center text-xs text-muted-foreground">
        Already have an account?{' '}
        <Link to={ROUTES.login} className="font-semibold text-primary hover:underline">
          Sign in
        </Link>
      </p>
    </AuthLayout>
  )
}
