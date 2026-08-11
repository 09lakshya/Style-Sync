import type { InputHTMLAttributes } from 'react'

interface AuthInputProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string
  error?: string
}

export function AuthInput({ label, error, id, className = '', ...props }: AuthInputProps) {
  const inputId = id || `auth-input-${label.toLowerCase().replace(/\s+/g, '-')}`

  return (
    <div className="space-y-1.5 text-left">
      <label htmlFor={inputId} className="block text-xs font-medium uppercase tracking-wider text-[#B8AD9A]">
        {label}
      </label>
      <div className="relative">
        <input
          id={inputId}
          className={`w-full rounded-none border border-white/10 bg-[#141412] px-4 py-3.5 text-sm text-[#F5F2EB] placeholder-[#62605A] transition-all duration-200 focus:border-[#E8E0D0] focus:bg-[#1A1A17] focus:outline-none focus:ring-1 focus:ring-[#E8E0D0]/30 disabled:opacity-50 ${
            error ? 'border-amber-600/60 focus:border-amber-500' : ''
          } ${className}`}
          {...props}
        />
      </div>
      {error && (
        <p className="mt-1.5 text-xs text-amber-400/90 font-sans-ui flex items-center gap-1 animate-fade-in" role="alert">
          <span>{error}</span>
        </p>
      )}
    </div>
  )
}
