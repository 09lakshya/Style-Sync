import { useMutation } from '@tanstack/react-query'
import { ArrowRight, Loader2 } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { AuthInput } from '../../components/auth/AuthInput'
import { EditorialVisual } from '../../components/auth/EditorialVisual'
import { PasswordInput } from '../../components/auth/PasswordInput'
import { registerApi } from './authApi'
import { GENDER_OPTIONS } from './authTypes'
import type { AuthSession, FormErrors, ProfileGender } from './authTypes'

interface SignupPageProps {
  onSessionSuccess: (session: AuthSession) => void
  onNavigateToLogin: () => void
}

export function SignupPage({ onSessionSuccess, onNavigateToLogin }: SignupPageProps) {
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  // Asked here because it decides the trend mix and styling rules from the
  // first session; there is no sensible way to infer it later.
  const [gender, setGender] = useState<ProfileGender | ''>('')
  const [errors, setErrors] = useState<FormErrors>({})

  const registerMutation = useMutation({
    mutationFn: (payload: { name: string; email: string; password: string; gender: ProfileGender }) =>
      registerApi(payload),
    onSuccess: (session) => {
      setErrors({})
      onSessionSuccess(session)
    },
    onError: (error) => {
      setErrors({
        general: error instanceof Error ? error.message : 'Registration failed. Please try again.',
      })
    },
  })

  function validateFormWithValues(
    nameVal: string,
    emailVal: string,
    passwordVal: string,
    genderVal: ProfileGender | '',
  ): boolean {
    const newErrors: FormErrors = {}

    const trimmedName = nameVal.trim()
    if (!trimmedName) {
      newErrors.name = 'Full name is required.'
    } else if (trimmedName.length < 2) {
      newErrors.name = 'Name must be at least 2 characters.'
    }

    const trimmedEmail = emailVal.trim()
    if (!trimmedEmail) {
      newErrors.email = 'Email address is required.'
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(trimmedEmail)) {
      newErrors.email = 'Please enter a valid email address.'
    }

    if (!passwordVal) {
      newErrors.password = 'Password is required.'
    } else if (passwordVal.length < 8) {
      newErrors.password = 'Password must be at least 8 characters long.'
    }

    if (!genderVal) {
      newErrors.gender = 'Choose an option so your trends and styling can be tailored.'
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()

    const formData = new FormData(e.currentTarget)
    const formName = ((formData.get('name') as string) || name).trim()
    const formEmail = ((formData.get('email') as string) || email).trim()
    const formPassword = (formData.get('password') as string) || password

    if (formName !== name) setName(formName)
    if (formEmail !== email) setEmail(formEmail)
    if (formPassword !== password) setPassword(formPassword)

    if (validateFormWithValues(formName, formEmail, formPassword, gender)) {
      registerMutation.mutate({
        name: formName,
        email: formEmail,
        password: formPassword,
        gender: gender as ProfileGender,
      })
    }
  }

  return (
    <div className="min-h-screen w-full bg-[#0A0A09] text-[#F5F2EB] flex flex-col lg:flex-row font-sans-ui selection:bg-[#E8E0D0] selection:text-[#0A0A09]">
      {/* 50% Desktop Left Column - Editorial Visual */}
      <EditorialVisual />

      {/* 50% Desktop Right Column - Sign Up Form */}
      <main className="w-full lg:w-1/2 flex flex-col justify-between min-h-screen p-6 sm:p-12 lg:p-20 bg-[#0A0A09]">
        {/* Brand Header */}
        <header className="flex items-center justify-between">
          <div className="flex items-baseline gap-2">
            <span className="font-serif-editorial text-2xl tracking-widest font-normal text-[#F5F2EB] uppercase">
              Style<span className="italic font-light text-[#E8E0D0]">Sync</span>
            </span>
          </div>
          <button
            onClick={onNavigateToLogin}
            type="button"
            className="text-xs uppercase tracking-widest text-[#B8AD9A] hover:text-[#E8E0D0] transition-colors py-1 focus:outline-none focus:underline"
          >
            Sign In
          </button>
        </header>

        {/* Form Container */}
        <div className="w-full max-w-md mx-auto my-auto py-8">
          <div className="mb-8 space-y-2">
            <p className="text-xs uppercase tracking-widest text-[#B8AD9A] font-medium">Join StyleSync</p>
            <h1 className="font-serif-editorial text-4xl sm:text-5xl font-normal text-[#F5F2EB] tracking-wide">
              Create your account
            </h1>
            <p className="text-sm text-[#B8AD9A] pt-1">
              Begin digitalizing your wardrobe with AI-powered fashion recommendations.
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

          <form onSubmit={handleSubmit} className="space-y-5" noValidate>
            <AuthInput
              label="Full Name"
              type="text"
              name="name"
              id="name"
              placeholder="E.g. Virat Kohli"
              value={name}
              onChange={(e) => {
                setName(e.target.value)
                if (errors.name) setErrors((prev) => ({ ...prev, name: undefined }))
              }}
              error={errors.name}
              autoComplete="name"
              disabled={registerMutation.isPending}
            />

            <AuthInput
              label="Email Address"
              type="email"
              name="email"
              id="email"
              placeholder="viratkohli@example.com"
              value={email}
              onChange={(e) => {
                setEmail(e.target.value)
                if (errors.email) setErrors((prev) => ({ ...prev, email: undefined }))
              }}
              error={errors.email}
              autoComplete="email"
              disabled={registerMutation.isPending}
            />

            <PasswordInput
              label="Password (min. 8 characters)"
              name="password"
              id="password"
              placeholder="••••••••"
              value={password}
              onChange={(e) => {
                setPassword(e.target.value)
                if (errors.password) setErrors((prev) => ({ ...prev, password: undefined }))
              }}
              error={errors.password}
              autoComplete="new-password"
              disabled={registerMutation.isPending}
            />

            <fieldset disabled={registerMutation.isPending}>
              <legend className="block text-xs uppercase tracking-widest text-[#B8AD9A] mb-3">
                Style profile
              </legend>
              <div className="grid grid-cols-2 gap-2">
                {GENDER_OPTIONS.map((option) => (
                  <label
                    key={option.value}
                    className={`cursor-pointer border px-3 py-2.5 text-xs uppercase tracking-widest transition-colors ${
                      gender === option.value
                        ? 'border-[#E8E0D0] bg-[#E8E0D0]/10 text-[#F5F2EB]'
                        : 'border-white/10 text-[#B8AD9A] hover:border-white/25'
                    }`}
                  >
                    <input
                      type="radio"
                      name="gender"
                      value={option.value}
                      checked={gender === option.value}
                      onChange={() => {
                        setGender(option.value)
                        if (errors.gender) setErrors((prev) => ({ ...prev, gender: undefined }))
                      }}
                      className="sr-only"
                    />
                    {option.label}
                  </label>
                ))}
              </div>
              <p className="mt-2 text-[11px] leading-5 text-[#62605A]">
                This selects which trends and styling conventions you are shown. Your theme comes
                from your own wardrobe, not from this answer.
              </p>
              {errors.gender && (
                <p className="mt-1.5 text-[11px] text-amber-300">{errors.gender}</p>
              )}
            </fieldset>

            <button
              type="submit"
              disabled={registerMutation.isPending}
              className="group relative w-full flex items-center justify-center gap-3 bg-[#E8E0D0] hover:bg-[#F5F2EB] text-[#0A0A09] py-4 px-6 text-xs font-semibold uppercase tracking-widest transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer focus:outline-none focus:ring-2 focus:ring-[#E8E0D0] focus:ring-offset-2 focus:ring-offset-[#0A0A09]"
            >
              {registerMutation.isPending ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin text-[#0A0A09]" />
                  <span>Creating Account...</span>
                </>
              ) : (
                <>
                  <span>Create Account</span>
                  <ArrowRight className="h-4 w-4 text-[#0A0A09] transition-transform duration-300 group-hover:translate-x-1" />
                </>
              )}
            </button>
          </form>

          <div className="mt-8 text-center pt-6 border-t border-white/5">
            <p className="text-xs text-[#B8AD9A]">
              Already have an account?{' '}
              <button
                type="button"
                onClick={onNavigateToLogin}
                className="text-[#E8E0D0] hover:underline font-medium focus:outline-none"
              >
                Sign in to your closet
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
