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
    mutationFn: () => loginApi({ email, password }),
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

  function validateForm(): boolean {
    const newErrors: FormErrors = {}

    const trimmedEmail = email.trim()
    if (!trimmedEmail) {
      newErrors.email = 'Email address is required.'
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(trimmedEmail)) {
      newErrors.email = 'Please enter a valid email address.'
    }

    if (!password) {
      newErrors.password = 'Password is required.'
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    if (validateForm()) {
      loginMutation.mutate()
    }
  }

  return (
    <div className="min-h-screen w-full bg-[#0A0A09] text-[#F5F2EB] flex flex-col lg:flex-row font-sans-ui selection:bg-[#E8E0D0] selection:text-[#0A0A09]">
      {/* 50% Desktop Left Column - Editorial Visual */}
      <EditorialVisual />

      {/* 50% Desktop Right Column - Sign In Form */}
      <main className="w-full lg:w-1/2 flex flex-col justify-between min-h-screen p-6 sm:p-12 lg:p-20 bg-[#0A0A09]">
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
        <div className="w-full max-w-md mx-auto my-auto py-8">
          <div className="mb-8 space-y-2">
            <p className="text-xs uppercase tracking-widest text-[#B8AD9A] font-medium">Welcome Back</p>
            <h1 className="font-serif-editorial text-4xl sm:text-5xl font-normal text-[#F5F2EB] tracking-wide">
              Sign in to your wardrobe
            </h1>
            <p className="text-sm text-[#B8AD9A] pt-1">
              Enter your credentials to access your smart closet and AI recommendations.
            </p>
          </div>

          {errors.general && (
            <div
              className="mb-6 border border-amber-500/30 bg-amber-950/20 px-4 py-3 text-xs text-amber-300 animate-fade-in font-sans-ui"
              role="alert"
            >
              {errors.general}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-6" noValidate>
            <AuthInput
              label="Email Address"
              type="email"
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

          <div className="mt-8 text-center pt-6 border-t border-white/5">
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
