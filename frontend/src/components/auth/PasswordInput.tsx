import { Eye, EyeOff } from 'lucide-react'
import { useState, type InputHTMLAttributes } from 'react'

interface PasswordInputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string
  error?: string
}

export function PasswordInput({ label = 'Password', error, id, className = '', ...props }: PasswordInputProps) {
  const [showPassword, setShowPassword] = useState(false)
  const inputId = id || 'auth-password-input'

  return (
    <div className="space-y-1.5 text-left">
      <div className="flex items-center justify-between">
        <label htmlFor={inputId} className="block text-xs font-medium uppercase tracking-wider text-[#B8AD9A]">
          {label}
        </label>
      </div>
      <div className="relative flex items-center">
        <input
          id={inputId}
          type={showPassword ? 'text' : 'password'}
          className={`w-full rounded-none border border-white/10 bg-[#141412] pl-4 pr-11 py-3.5 text-sm text-[#F5F2EB] placeholder-[#62605A] transition-all duration-200 focus:border-[#E8E0D0] focus:bg-[#1A1A17] focus:outline-none focus:ring-1 focus:ring-[#E8E0D0]/30 disabled:opacity-50 ${
            error ? 'border-amber-600/60 focus:border-amber-500' : ''
          } ${className}`}
          {...props}
        />
        <button
          type="button"
          tabIndex={0}
          onClick={() => setShowPassword((prev) => !prev)}
          aria-label={showPassword ? 'Hide password' : 'Show password'}
          className="absolute right-3.5 text-[#B8AD9A]/70 hover:text-[#E8E0D0] transition-colors focus:outline-none focus:text-[#E8E0D0] p-1"
        >
          {showPassword ? (
            <EyeOff className="h-4 w-4" aria-hidden="true" />
          ) : (
            <Eye className="h-4 w-4" aria-hidden="true" />
          )}
        </button>
      </div>
      {error && (
        <p className="mt-1.5 text-xs text-amber-400/90 font-sans-ui animate-fade-in" role="alert">
          {error}
        </p>
      )}
    </div>
  )
}
