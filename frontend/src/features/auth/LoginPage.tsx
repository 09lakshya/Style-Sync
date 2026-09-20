import { useMutation } from '@tanstack/react-query'
import { ArrowRight, Loader2 } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { AuthInput } from '../../components/auth/AuthInput'
import { EditorialVisual } from '../../components/auth/EditorialVisual'
import { PasswordInput } from '../../components/auth/PasswordInput'
import { loginApi } from './authApi'
import type { AuthSession, FormErrors } from './authTypes'

interface LoginPageProps {
  onSessionSuccess: (session: AuthSession) => void
  onNavigateToSignup: () => void
}

export function LoginPage({ onSessionSuccess, onNavigateToSignup }: LoginPageProps) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [errors, setErrors] = useState<FormErrors>({})

  const loginMutation = useMutation({
    mutationFn: (credentials: { email: string; password: string }) => loginApi(credentials),
    onSuccess: (session) => {
      setErrors({})
      onSessionSuccess(session)
    },
    onError: (error) => {
      setErrors({
        general: error instanceof Error ? error.message : 'Authentication failed. Please try again.',
      })
    },
  })

  function validateFormWithValues(emailVal: string, passwordVal: string): boolean {
    const newErrors: FormErrors = {}

    const trimmedEmail = emailVal.trim()
    if (!trimmedEmail) {
      newErrors.email = 'Email address is required.'
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(trimmedEmail)) {
      newErrors.email = 'Please enter a valid email address.'
    }

    if (!passwordVal) {
      newErrors.password = 'Password is required.'
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()

    // Extract values directly from form DOM elements in case browser autofill did not trigger React onChange
    const formData = new FormData(e.currentTarget)
    const formEmail = ((formData.get('email') as string) || email).trim()
    const formPassword = (formData.get('password') as string) || password

    if (formEmail !== email) setEmail(formEmail)
    if (formPassword !== password) setPassword(formPassword)

    if (validateFormWithValues(formEmail, formPassword)) {
      loginMutation.mutate({ email: formEmail, password: formPassword })
    }
  }

  return (
    <div className="min-h-screen w-full bg-[#0A0A09] text-[#F5F2EB] flex flex-col lg:flex-row font-sans-ui selection:bg-[#E8E0D0] selection:text-[#0A0A09]">
      {/* 50% Desktop Left Column - Editorial Visual */}
      <EditorialVisual />

      {/* 50% Desktop Right Column - Sign In Form */}
      {/* Sized to the viewport on desktop so the Sign In button is reachable without
          scrolling; it scrolls only if the content genuinely cannot fit. */}
      <main className="w-full lg:w-1/2 flex flex-col justify-between min-h-screen lg:h-screen lg:overflow-y-auto px-6 py-6 sm:px-12 sm:py-8 lg:px-16 lg:py-10 bg-[#0A0A09]">
        {/* Brand Header */}
        <header className="flex items-center justify-between">
          <div className="flex items-baseline gap-2">
            <span className="font-serif-editorial text-2xl tracking-widest font-normal text-[#F5F2EB] uppercase">
              Style<span className="italic font-light text-[#E8E0D0]">Sync</span>
            </span>
          </div>
          <button
            onClick={onNavigateToSignup}
            type="button"
            className="text-xs uppercase tracking-widest text-[#B8AD9A] hover:text-[#E8E0D0] transition-colors py-1 focus:outline-none focus:underline"
          >
            Create Account
          </button>
        </header>

        {/* Form Container */}
        <div className="w-full max-w-md mx-auto my-auto py-6 lg:py-4">
          <div className="mb-6 space-y-2">
            <p className="text-xs uppercase tracking-widest text-[#B8AD9A] font-medium">Welcome Back</p>
            <h1 className="font-serif-editorial text-3xl sm:text-4xl font-normal text-[#F5F2EB] tracking-wide">
              Sign in to your wardrobe
            </h1>
            <p className="text-sm text-[#B8AD9A] pt-1">
              Enter your credentials to access your smart closet and AI recommendations.
            </p>
          </div>

          {errors.general && (
            <div
              className="mb-4 border border-amber-500/30 bg-amber-950/20 px-4 py-3 text-xs text-amber-300 animate-fade-in font-sans-ui flex flex-col gap-1"
              role="alert"
            >
              <span>{errors.general}</span>
              {errors.general.includes('Incorrect email or password') && (
                <span className="text-[11px] text-amber-200/70 pt-1">
                  If you haven&apos;t created a StyleSync account yet with this email, please{' '}
                  <button
                    type="button"
                    onClick={onNavigateToSignup}
                    className="underline text-[#E8E0D0] hover:text-white font-medium focus:outline-none"
                  >
                    Sign Up first
                  </button>
                  .
                </span>
              )}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5" noValidate>
            <AuthInput
              label="Email Address"
              type="email"
              name="email"
              id="email"
              placeholder="name@example.com"
              value={email}
              onChange={(e) => {
                setEmail(e.target.value)
                if (errors.email) setErrors((prev) => ({ ...prev, email: undefined }))
              }}
              error={errors.email}
              autoComplete="email"
              disabled={loginMutation.isPending}
            />

            <PasswordInput
              label="Password"
              name="password"
              id="password"
              placeholder="••••••••"
              value={password}
              onChange={(e) => {
                setPassword(e.target.value)
                if (errors.password) setErrors((prev) => ({ ...prev, password: undefined }))
              }}
              error={errors.password}
              autoComplete="current-password"
              disabled={loginMutation.isPending}
            />

            <button
              type="submit"
              disabled={loginMutation.isPending}
              className="group relative w-full flex items-center justify-center gap-3 bg-[#E8E0D0] hover:bg-[#F5F2EB] text-[#0A0A09] py-4 px-6 text-xs font-semibold uppercase tracking-widest transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer focus:outline-none focus:ring-2 focus:ring-[#E8E0D0] focus:ring-offset-2 focus:ring-offset-[#0A0A09]"
            >
              {loginMutation.isPending ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin text-[#0A0A09]" />
                  <span>Signing In...</span>
                </>
              ) : (
                <>
                  <span>Sign In</span>
                  <ArrowRight className="h-4 w-4 text-[#0A0A09] transition-transform duration-300 group-hover:translate-x-1" />
                </>
              )}
            </button>
          </form>

          <div className="mt-6 text-center pt-4 border-t border-white/5">
            <p className="text-xs text-[#B8AD9A]">
              Don&apos;t have an account?{' '}
              <button
                type="button"
                onClick={onNavigateToSignup}
                className="text-[#E8E0D0] hover:underline font-medium focus:outline-none"
              >
                Sign up for StyleSync
              </button>
            </p>
          </div>
        </div>

        {/* Footer info */}
        <footer className="text-center sm:text-left text-[11px] text-[#62605A] uppercase tracking-widest flex flex-col sm:flex-row justify-between gap-2">
          <span>&copy; {new Date().getFullYear()} StyleSync Technologies</span>
        </footer>
      </main>
    </div>
  )
}
