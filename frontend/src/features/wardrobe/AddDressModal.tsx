import React, { useState } from 'react'
import { CloudUpload, X, AlertCircle, Loader2 } from 'lucide-react'
import type { CreateDressInput } from '../../types/wardrobe'

interface AddDressModalProps {
  isOpen: boolean
  onClose: () => void
  onSubmit: (data: CreateDressInput) => void
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

export function AddDressModal({ isOpen, onClose, onSubmit, isSubmitting }: AddDressModalProps) {
  const [file, setFile] = useState<File | null>(null)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [name, setName] = useState('')
  const [color, setColor] = useState('Blue')
  const [pattern, setPattern] = useState('Solid')
  const [brand, setBrand] = useState('')
  const [purchaseDate, setPurchaseDate] = useState('')
  const [occasion, setOccasion] = useState('Casual')
  const [lastWornDate, setLastWornDate] = useState('')
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  if (!isOpen) return null

  function handleFileSelect(selected: File | null) {
    if (!selected) return
    if (!selected.type.startsWith('image/')) {
      setErrorMessage('Please select a valid image file (JPG, PNG, or WebP).')
      return
    }
    if (selected.size > 10 * 1024 * 1024) {
      setErrorMessage('Image size must be less than 10MB.')
      return
    }
    setErrorMessage(null)
    setFile(selected)
    const url = URL.createObjectURL(selected)
    setPreviewUrl(url)
  }

  function handleDrop(e: React.DragEvent<HTMLLabelElement>) {
    e.preventDefault()
    e.stopPropagation()
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelect(e.dataTransfer.files[0])
    }
  }

  function handleDragOver(e: React.DragEvent<HTMLLabelElement>) {
    e.preventDefault()
    e.stopPropagation()
  }

  function removeFile() {
    setFile(null)
    if (previewUrl) {
      URL.revokeObjectURL(previewUrl)
      setPreviewUrl(null)
    }
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!file) {
      setErrorMessage('Please select a dress image.')
      return
    }
    if (!name.trim()) {
      setErrorMessage('Please enter a dress name.')
      return
    }

    onSubmit({
      file,
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
      <div className="relative w-full max-w-2xl rounded-xl border border-[#38332c] bg-[#1a1917] text-[#f7f4ef] shadow-2xl p-6 sm:p-8">
        <button
          onClick={onClose}
          disabled={isSubmitting}
          className="absolute right-4 top-4 rounded-full p-2 text-stone-400 hover:bg-stone-800 hover:text-white transition-colors"
        >
          <X className="h-5 w-5" />
        </button>

        <div className="mb-6">
          <h2 className="text-2xl font-semibold tracking-tight text-[#f7f4ef]">Add Dress to Wardrobe</h2>
          <p className="mt-1 text-sm text-stone-400">
            Upload your dress photo and enter metadata details.
          </p>
        </div>

        {errorMessage && (
          <div className="mb-6 flex items-center gap-2 rounded-lg border border-rose-900/50 bg-rose-950/30 p-3 text-sm text-rose-300">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span>{errorMessage}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Image Dropzone & Preview */}
          <div>
            <label className="block text-xs font-medium uppercase tracking-wider text-stone-400 mb-2">
              Dress Image *
            </label>
            {previewUrl ? (
              <div className="relative h-64 w-full overflow-hidden rounded-lg border border-[#38332c] bg-stone-900">
                <img src={previewUrl} alt="Preview" className="h-full w-full object-contain" />
                <div className="absolute right-3 top-3 flex gap-2">
                  <label className="cursor-pointer rounded-md bg-stone-900/90 px-3 py-1.5 text-xs font-medium text-white backdrop-blur-md hover:bg-stone-800">
                    Replace
                    <input
                      type="file"
                      accept="image/png,image/jpeg,image/webp"
                      className="sr-only"
                      onChange={(e) => handleFileSelect(e.target.files?.[0] ?? null)}
                    />
                  </label>
                  <button
                    type="button"
                    onClick={removeFile}
                    className="rounded-md bg-rose-900/80 px-3 py-1.5 text-xs font-medium text-white backdrop-blur-md hover:bg-rose-800"
                  >
                    Remove
                  </button>
                </div>
              </div>
            ) : (
              <label
                onDrop={handleDrop}
                onDragOver={handleDragOver}
                className="flex min-h-[180px] cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed border-[#38332c] bg-[#211f1c] hover:bg-[#282622] hover:border-[#a15c38] transition-colors p-6 text-center"
              >
                <div className="grid h-12 w-12 place-items-center rounded-full bg-[#2a2723] text-[#a15c38]">
                  <CloudUpload className="h-6 w-6" />
                </div>
                <p className="mt-3 text-sm font-medium text-stone-200">
                  Drag and drop image here, or <span className="text-[#a15c38] underline">browse</span>
                </p>
                <p className="mt-1 text-xs text-stone-400">Supports JPG, PNG, or WebP up to 10MB</p>
                <input
                  type="file"
                  accept="image/png,image/jpeg,image/webp"
                  className="sr-only"
                  onChange={(e) => handleFileSelect(e.target.files?.[0] ?? null)}
                />
              </label>
            )}
          </div>

          {/* Form Grid */}
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="block text-xs font-medium uppercase tracking-wider text-stone-400 mb-1.5">
                Dress Name *
              </label>
              <input
                type="text"
                required
                placeholder="e.g. Blue Floral Summer Dress"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full rounded-md border border-[#38332c] bg-[#211f1c] px-3.5 py-2.5 text-sm text-stone-100 placeholder-stone-500 focus:border-[#a15c38] focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-medium uppercase tracking-wider text-stone-400 mb-1.5">
                Brand
              </label>
              <input
                type="text"
                placeholder="e.g. Zara, Mango, H&M"
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
                  Uploading...
                </>
              ) : (
                'Add to Wardrobe'
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
