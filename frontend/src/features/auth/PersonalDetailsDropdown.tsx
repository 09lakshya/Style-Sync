import { useEffect, useRef, useState } from 'react'
import { ChevronDown, LogOut } from 'lucide-react'
import type { AuthUser } from './authTypes'
import { updateProfileApi } from './authApi'

const GENDER_DISPLAY: Record<string, string> = {
  male: 'Male',
  female: 'Female',
  'non-binary': 'Non-binary',
  unspecified: 'Prefer not to say',
}

interface PersonalDetailsDropdownProps {
  user: AuthUser
  token: string
  onSignOut: () => void
  onUpdateUser: (updated: AuthUser) => void
}

export function PersonalDetailsDropdown({
  user,
  token,
  onSignOut,
  onUpdateUser,
}: PersonalDetailsDropdownProps) {
  const [open, setOpen] = useState(false)
  const [name, setName] = useState(user.name)
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)
  const [saved, setSaved] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  // Sync name when user prop changes
  useEffect(() => {
    setName(user.name)
  }, [user.name])

  // Close on outside click
  useEffect(() => {
    if (!open) return
    function handler(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [open])

  // Close on Escape
  useEffect(() => {
    if (!open) return
    function handler(e: KeyboardEvent) {
      if (e.key === 'Escape') setOpen(false)
    }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [open])

  const initial = user.name.charAt(0).toUpperCase()
  const genderLabel = GENDER_DISPLAY[user.gender ?? 'unspecified'] ?? 'Prefer not to say'

  async function handleSave() {
    const trimmed = name.trim()
    if (!trimmed || trimmed === user.name) {
      setOpen(false)
      return
    }
    setSaving(true)
    setSaveError(null)
    try {
      const updated = await updateProfileApi(token, { name: trimmed })
      onUpdateUser(updated)
      setSaved(true)
      setTimeout(() => {
        setSaved(false)
        setOpen(false)
      }, 1000)
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : 'Failed to save.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div ref={ref} className="relative">
      {/* Trigger */}
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="inline-flex items-center gap-2 rounded-lg border border-[#e1dbd0] bg-[var(--surface)] hover:bg-[var(--accent-soft)] transition-colors px-3 py-2 cursor-pointer font-medium text-xs text-[#1f2328]"
        aria-expanded={open}
      >
        <span className="grid h-6 w-6 place-items-center rounded-full bg-[var(--accent)] text-white text-[11px] font-bold shrink-0">
          {initial}
        </span>
        <span className="hidden sm:inline">{user.name}</span>
        <span className="hidden sm:inline text-[#9a918a]">· {genderLabel}</span>
        <ChevronDown className={`h-3.5 w-3.5 text-[#9a918a] transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>

      {/* Dropdown panel */}
      {open && (
        <div className="absolute right-0 top-full z-50 mt-2 w-72 rounded-xl border border-[var(--border)] bg-[var(--surface-raised)] shadow-xl">
          <div className="p-4 space-y-4">
            {/* Name */}
            <div>
              <label className="block text-[10px] uppercase tracking-widest text-[#9a918a] mb-1">
                Name
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => {
                  setName(e.target.value)
                  setSaveError(null)
                  setSaved(false)
                }}
                className="w-full rounded-lg border border-[var(--border)] bg-[var(--surface)] px-3 py-2 text-sm text-[#1f2328] focus:outline-none focus:ring-2 focus:ring-[var(--accent)]"
                placeholder="Your name"
                maxLength={80}
              />
            </div>

            {/* Email — read-only */}
            <div>
              <label className="block text-[10px] uppercase tracking-widest text-[#9a918a] mb-1">
                Email <span className="normal-case text-[#b8b0a4]">(cannot be changed)</span>
              </label>
              <input
                type="email"
                value={user.email}
                disabled
                className="w-full rounded-lg border border-[var(--border)] bg-[var(--surface)] px-3 py-2 text-sm text-[#9a918a] cursor-not-allowed opacity-70"
              />
            </div>

            {/* Gender — read-only */}
            <div>
              <label className="block text-[10px] uppercase tracking-widest text-[#9a918a] mb-1">
                Gender <span className="normal-case text-[#b8b0a4]">(set during sign up)</span>
              </label>
              <div className="w-full rounded-lg border border-[var(--border)] bg-[var(--surface)] px-3 py-2 text-sm text-[#9a918a] opacity-70">
                {genderLabel}
              </div>
            </div>

            {/* Error */}
            {saveError && (
              <p className="text-xs text-red-500">{saveError}</p>
            )}

            {/* Save button */}
            <button
              type="button"
              onClick={handleSave}
              disabled={saving || !name.trim()}
              className="w-full rounded-lg bg-[var(--accent)] px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-[var(--accent-hover)] disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {saving ? 'Saving…' : saved ? 'Saved ✓' : 'Save changes'}
            </button>
          </div>

          {/* Sign out */}
          <div className="border-t border-[var(--border)] px-4 py-3">
            <button
              type="button"
              onClick={onSignOut}
              className="inline-flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-[#c0392b] hover:bg-red-50 transition-colors"
            >
              <LogOut className="h-4 w-4" />
              Sign out
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
