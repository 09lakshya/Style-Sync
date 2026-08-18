import React, { useState } from 'react'
import { X, Loader2, AlertCircle } from 'lucide-react'
import type { UpdateDressMetadataInput, WardrobeItem } from '../../types/wardrobe'

interface EditDressModalProps {
  item: WardrobeItem | null
  isOpen: boolean
  onClose: () => void
  onSubmit: (data: UpdateDressMetadataInput) => void
  isSubmitting: boolean
}

const COLOR_OPTIONS = [
  'Black',
  'White',
  'Blue',
  'Red',
  'Green',
  'Yellow',
  'Pink',
  'Purple',
  'Brown',
  'Beige',
  'Grey',
  'Other',
]

const PATTERN_OPTIONS = [
  'Solid',
  'Floral',
  'Striped',
  'Checked',
  'Printed',
  'Polka Dot',
  'Geometric',
  'Embroidered',
  'Other',
]

const OCCASION_OPTIONS = [
  'Casual',
  'Formal',
  'Party',
  'College',
  'Office',
  'Wedding',
  'Sports',
  'Travel',
  'Traditional',
  'Other',
]

export function EditDressModal({ item, isOpen, onClose, onSubmit, isSubmitting }: EditDressModalProps) {
  const [name, setName] = useState(item?.name || '')
  const [color, setColor] = useState(item?.color || 'Blue')
  const [pattern, setPattern] = useState(item?.pattern || 'Solid')
  const [brand, setBrand] = useState(item?.brand || '')
  const [purchaseDate, setPurchaseDate] = useState(item?.purchaseDate || '')
  const [occasion, setOccasion] = useState(item?.occasion[0] || 'Casual')
  const [lastWornDate, setLastWornDate] = useState(item?.lastWornDate !== 'Not worn yet' ? item?.lastWornDate || '' : '')
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  // Sync state if item changes
  React.useEffect(() => {
    if (item) {
      setName(item.name)
      setColor(item.color)
      setPattern(item.pattern)
      setBrand(item.brand || '')
      setPurchaseDate(item.purchaseDate || '')
      setOccasion(item.occasion[0] || 'Casual')
      setLastWornDate(item.lastWornDate !== 'Not worn yet' ? item.lastWornDate : '')
    }
  }, [item])

  if (!isOpen || !item) return null

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!name.trim()) {
      setErrorMessage('Please enter a dress name.')
      return
    }

    onSubmit({
      id: item!.id,
      name: name.trim(),
      color,
      pattern,
      brand: brand.trim(),
      purchaseDate,
      occasion,
      lastWornDate,
    })
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 overflow-y-auto">
      <div className="relative w-full max-w-xl rounded-xl border border-[#38332c] bg-[#1a1917] text-[#f7f4ef] shadow-2xl p-6 sm:p-8">
        <button
          onClick={onClose}
          disabled={isSubmitting}
          className="absolute right-4 top-4 rounded-full p-2 text-stone-400 hover:bg-stone-800 hover:text-white transition-colors"
        >
          <X className="h-5 w-5" />
        </button>

        <div className="mb-6">
          <h2 className="text-2xl font-semibold tracking-tight text-[#f7f4ef]">Edit Dress Metadata</h2>
          <p className="mt-1 text-sm text-stone-400">
            Update attributes for &ldquo;{item.name}&rdquo;.
          </p>
        </div>

        {errorMessage && (
          <div className="mb-6 flex items-center gap-2 rounded-lg border border-rose-900/50 bg-rose-950/30 p-3 text-sm text-rose-300">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span>{errorMessage}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-medium uppercase tracking-wider text-stone-400 mb-1.5">
              Dress Name *
            </label>
            <input
              type="text"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full rounded-md border border-[#38332c] bg-[#211f1c] px-3.5 py-2.5 text-sm text-stone-100 placeholder-stone-500 focus:border-[#a15c38] focus:outline-none"
            />
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="block text-xs font-medium uppercase tracking-wider text-stone-400 mb-1.5">
                Brand
              </label>
              <input
                type="text"
                value={brand}
                onChange={(e) => setBrand(e.target.value)}
                className="w-full rounded-md border border-[#38332c] bg-[#211f1c] px-3.5 py-2.5 text-sm text-stone-100 placeholder-stone-500 focus:border-[#a15c38] focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-medium uppercase tracking-wider text-stone-400 mb-1.5">
                Color *
              </label>
              <select
                value={color}
                onChange={(e) => setColor(e.target.value)}
                className="w-full rounded-md border border-[#38332c] bg-[#211f1c] px-3.5 py-2.5 text-sm text-stone-100 focus:border-[#a15c38] focus:outline-none"
              >
                {COLOR_OPTIONS.map((opt) => (
                  <option key={opt} value={opt}>
                    {opt}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-medium uppercase tracking-wider text-stone-400 mb-1.5">
                Pattern *
              </label>
              <select
                value={pattern}
                onChange={(e) => setPattern(e.target.value)}
                className="w-full rounded-md border border-[#38332c] bg-[#211f1c] px-3.5 py-2.5 text-sm text-stone-100 focus:border-[#a15c38] focus:outline-none"
              >
                {PATTERN_OPTIONS.map((opt) => (
                  <option key={opt} value={opt}>
                    {opt}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-medium uppercase tracking-wider text-stone-400 mb-1.5">
                Occasion *
              </label>
              <select
                value={occasion}
                onChange={(e) => setOccasion(e.target.value)}
                className="w-full rounded-md border border-[#38332c] bg-[#211f1c] px-3.5 py-2.5 text-sm text-stone-100 focus:border-[#a15c38] focus:outline-none"
              >
                {OCCASION_OPTIONS.map((opt) => (
                  <option key={opt} value={opt}>
                    {opt}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-medium uppercase tracking-wider text-stone-400 mb-1.5">
                Purchase Date
              </label>
              <input
                type="date"
                value={purchaseDate}
                onChange={(e) => setPurchaseDate(e.target.value)}
                className="w-full rounded-md border border-[#38332c] bg-[#211f1c] px-3.5 py-2.5 text-sm text-stone-100 focus:border-[#a15c38] focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-medium uppercase tracking-wider text-stone-400 mb-1.5">
                Last Worn Date
              </label>
              <input
                type="date"
                value={lastWornDate}
                onChange={(e) => setLastWornDate(e.target.value)}
                className="w-full rounded-md border border-[#38332c] bg-[#211f1c] px-3.5 py-2.5 text-sm text-stone-100 focus:border-[#a15c38] focus:outline-none"
              />
            </div>
          </div>

          <div className="flex items-center justify-end gap-3 pt-4 border-t border-[#38332c]">
            <button
              type="button"
              onClick={onClose}
              disabled={isSubmitting}
              className="rounded-md border border-[#38332c] bg-stone-900 px-4 py-2 text-sm font-medium text-stone-300 hover:bg-stone-800 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="inline-flex items-center gap-2 rounded-md bg-[#a15c38] px-5 py-2 text-sm font-medium text-white hover:bg-[#b56942] transition-colors disabled:opacity-50"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Saving...
                </>
              ) : (
                'Save Changes'
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
