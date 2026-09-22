import React, { useState } from 'react'
import { CloudUpload, X, AlertCircle, Loader2, Sparkles } from 'lucide-react'
import { detectDressMetadata } from '../../api/wardrobeApi'
import type { CreateDressInput, DetectedDressMetadata } from '../../types/wardrobe'

interface AddDressModalProps {
  isOpen: boolean
  onClose: () => void
  onSubmit: (data: CreateDressInput) => void
  isSubmitting: boolean
  error?: Error | null
  token: string
  /** Garment words worth offering this user, from their styling profile. */
  suggestedGarments?: string[]
}

// Kept in step with CANDIDATE_COLORS in the backend's ai service, so a detected
// colour lands on a real option instead of falling through to "Other".
const COLOR_OPTIONS = [
  'Black',
  'White',
  'Cream',
  'Grey',
  'Silver',
  'Blue',
  'Navy',
  'Teal',
  'Green',
  'Olive',
  'Red',
  'Maroon',
  'Pink',
  'Magenta',
  'Peach',
  'Purple',
  'Yellow',
  'Mustard',
  'Orange',
  'Gold',
  'Beige',
  'Brown',
  'Other',
]

// Likewise CANDIDATE_PATTERNS: the lower block is the surface work that defines
// most Indian occasion wear.
const PATTERN_OPTIONS = [
  'Solid',
  'Floral',
  'Striped',
  'Checked',
  'Plaid',
  'Polka Dot',
  'Geometric',
  'Graphic',
  'Animal Print',
  'Paisley',
  'Embroidered',
  'Zari',
  'Sequined',
  'Bandhani',
  'Block Print',
  'Ikat',
  'Other',
]

// Mirrors TYPE_PROMPTS in the backend's ai service. Grouped so the traditional
// wear is findable rather than buried among the western names.
const GARMENT_GROUPS: { label: string; types: string[] }[] = [
  {
    label: 'Western',
    types: [
      'dress', 'gown', 'shirt', 'blouse', 'top', 't-shirt', 'skirt', 'pants',
      'jeans', 'shorts', 'jumpsuit', 'romper', 'jacket', 'coat', 'blazer',
      'sweater', 'hoodie', 'cardigan', 'waistcoat',
    ],
  },
  {
    label: 'Indian traditional',
    types: [
      'saree', 'lehenga', 'choli', 'anarkali', 'salwar kameez', 'patiala salwar',
      'churidar', 'palazzo', 'sharara', 'gharara', 'kurta', 'kurti', 'angrakha',
      'sherwani', 'bandhgala', 'nehru jacket', 'pathani suit', 'dhoti', 'lungi',
      'mekhela chador', 'pattu pavadai', 'phiran', 'indo-western gown', 'dupatta',
    ],
  },
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

function formatConfidence(value: number | undefined): string {
  return typeof value === 'number' ? `${Math.round(value * 100)}%` : ''
}

export function AddDressModal({
  isOpen,
  onClose,
  onSubmit,
  isSubmitting,
  error,
  token,
  suggestedGarments = [],
}: AddDressModalProps) {
  const [file, setFile] = useState<File | null>(null)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [name, setName] = useState('')
  const [color, setColor] = useState('Blue')
  // Free-text colour, used only while the select sits on "Other".
  const [customColor, setCustomColor] = useState('')
  const [pattern, setPattern] = useState('Solid')
  // Detection gets the garment wrong often enough on full-body photos that this
  // has to be correctable: a loose linen trouser reads as a churidar.
  const [itemType, setItemType] = useState('')
  const [brand, setBrand] = useState('')
  const [purchaseDate, setPurchaseDate] = useState('')
  const [occasion, setOccasion] = useState('Casual')
  const [lastWornDate, setLastWornDate] = useState('')
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  // What the model read off the photo. Kept so the form can show what it filled
  // in and the user can see what to correct.
  const [detection, setDetection] = useState<DetectedDressMetadata | null>(null)
  const [isDetecting, setIsDetecting] = useState(false)

  React.useEffect(() => {
    if (!isOpen) {
      setFile(null)
      if (previewUrl) {
        URL.revokeObjectURL(previewUrl)
        setPreviewUrl(null)
      }
      setName('')
      setColor('Blue')
      setPattern('Solid')
      setItemType('')
      setBrand('')
      setPurchaseDate('')
      setOccasion('Casual')
      setLastWornDate('')
      setErrorMessage(null)
      setDetection(null)
      setIsDetecting(false)
    }
  }, [isOpen])

  if (!isOpen) return null

  const displayedError = errorMessage || (error ? error.message : null)

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
    void runDetection(selected)
  }

  /** Match a detected value to one of the select's options, case-insensitively. */
  function toOption(options: string[], value: string | null): string | null {
    if (!value) return null
    const normalised = value.replace(/_/g, ' ').trim().toLowerCase()
    return options.find((option) => option.toLowerCase() === normalised) ?? null
  }

  async function runDetection(selected: File) {
    setIsDetecting(true)
    setDetection(null)
    try {
      const detected = await detectDressMetadata(selected, token)
      setDetection(detected)
      if (detected.type) setItemType(detected.type)

      // Only fill fields the user has not already set by hand.
      if (detected.name) setName((prev) => (prev.trim() ? prev : detected.name ?? ''))

      const detectedColor = toOption(COLOR_OPTIONS, detected.color)
      if (detectedColor) {
        setColor(detectedColor)
      } else if (detected.color) {
        setColor('Other')
        setCustomColor(detected.color)
      }

      // Surface work is the more useful label when both are present.
      const detectedPattern =
        toOption(PATTERN_OPTIONS, detected.embellishment) ??
        toOption(PATTERN_OPTIONS, detected.pattern)
      if (detectedPattern) setPattern(detectedPattern)

      const detectedOccasion = detected.occasion
        .map((entry) => toOption(OCCASION_OPTIONS, entry))
        .find(Boolean)
      if (detectedOccasion) setOccasion(detectedOccasion)
    } catch (err) {
      // Detection is a convenience, never a blocker: the form still submits.
      setDetection(null)
      console.warn('Attribute detection failed:', err)
    } finally {
      setIsDetecting(false)
    }
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
    setDetection(null)
    setIsDetecting(false)
    if (previewUrl) {
      URL.revokeObjectURL(previewUrl)
      setPreviewUrl(null)
    }
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!name.trim() && !file) {
      setErrorMessage('Add a photo, or enter a name for this piece.')
      return
    }

    const resolvedColor = color === 'Other' ? customColor.trim() : color
    if (!resolvedColor) {
      setErrorMessage('Please type a color, or pick one from the list.')
      return
    }

    setErrorMessage(null)
    onSubmit({
      file,
      // Blank is fine with a photo attached: the backend names it from what it detected.
      name: name.trim(),
      itemType,
      color: resolvedColor,
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

        {displayedError && (
          <div className="mb-6 flex items-center gap-2 rounded-lg border border-rose-900/50 bg-rose-950/30 p-3 text-sm text-rose-300">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span>{displayedError}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Image Dropzone & Preview */}
          <div>
            <label className="block text-xs font-medium uppercase tracking-wider text-stone-400 mb-2">
              Dress Image (Optional)
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
                className="flex min-h-[180px] cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed border-[#38332c] bg-[#211f1c] hover:bg-[#282622] hover:border-[var(--accent)] transition-colors p-6 text-center"
              >
                <div className="grid h-12 w-12 place-items-center rounded-full bg-[#2a2723] text-[var(--accent)]">
                  <CloudUpload className="h-6 w-6" />
                </div>
                <p className="mt-3 text-sm font-medium text-stone-200">
                  Drag and drop image here, or <span className="text-[var(--accent)] underline">browse</span>
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

          {/* What the model read off the photo. Shown so the filled-in values are
              attributable, and so a wrong read is obvious before saving. */}
          {(isDetecting || detection) && (
            <div className="rounded-lg border border-[#38332c] bg-[#211f1c] p-3">
              {isDetecting ? (
                <p className="flex items-center gap-2 text-sm text-stone-300">
                  <Loader2 className="h-4 w-4 animate-spin text-[var(--accent)]" />
                  Reading the photo...
                </p>
              ) : detection ? (
                <>
                  <p className="flex items-center gap-2 text-sm font-medium text-stone-200">
                    <Sparkles className="h-4 w-4 text-[var(--accent)]" />
                    Detected automatically
                    <span className="ml-auto text-xs font-normal text-stone-500">
                      edit anything below
                    </span>
                  </p>
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {[
                      { label: detection.type, hint: `type ${formatConfidence(detection.confidence.type)}` },
                      { label: detection.color, hint: `colour ${formatConfidence(detection.confidence.color)}` },
                      { label: detection.embellishment ?? detection.pattern, hint: `pattern ${formatConfidence(detection.confidence.pattern)}` },
                      { label: detection.fabric === 'user_review_needed' ? null : detection.fabric, hint: 'fabric' },
                      { label: detection.sleeve_type, hint: 'sleeves' },
                      { label: detection.is_ethnic ? 'ethnic wear' : null, hint: 'category' },
                    ]
                      .filter((chip) => Boolean(chip.label))
                      .map((chip) => (
                        <span
                          key={`${chip.hint}-${chip.label}`}
                          title={chip.hint}
                          className="rounded-full border border-[#443d34] bg-[#2a2723] px-2.5 py-1 text-xs capitalize text-stone-300"
                        >
                          {String(chip.label).replace(/_/g, ' ')}
                        </span>
                      ))}
                  </div>
                </>
              ) : null}
            </div>
          )}

          {/* Form Grid */}
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="block text-xs font-medium uppercase tracking-wider text-stone-400 mb-1.5">
                Dress Name {file ? '' : '*'}
              </label>
              <input
                type="text"
                placeholder={file ? 'Detected from the photo' : 'e.g. Blue Floral Summer Dress'}
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full rounded-md border border-[#38332c] bg-[#211f1c] px-3.5 py-2.5 text-sm text-stone-100 placeholder-stone-500 focus:border-[var(--accent)] focus:outline-none"
              />
              {/* Garment words for this user's profile, so naming by hand does
                  not mean typing "kurta" from scratch every time. */}
              {!detection && suggestedGarments.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {suggestedGarments.map((garment) => (
                    <button
                      key={garment}
                      type="button"
                      onClick={() =>
                        setName((prev) => (prev.trim() ? `${prev.trim()} ${garment}` : garment))
                      }
                      className="rounded-full border border-[#443d34] bg-[#2a2723] px-2.5 py-1 text-xs text-stone-300 hover:border-[var(--accent)] hover:text-stone-100"
                    >
                      {garment}
                    </button>
                  ))}
                </div>
              )}
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
                className="w-full rounded-md border border-[#38332c] bg-[#211f1c] px-3.5 py-2.5 text-sm text-stone-100 placeholder-stone-500 focus:border-[var(--accent)] focus:outline-none"
              />
            </div>

            <div>
              <label
                htmlFor="add-dress-type"
                className="block text-xs font-medium uppercase tracking-wider text-stone-400 mb-1.5"
              >
                Garment type {detection ? '(detected)' : ''}
              </label>
              <select
                id="add-dress-type"
                value={itemType}
                onChange={(e) => setItemType(e.target.value)}
                className="w-full rounded-md border border-[#38332c] bg-[#211f1c] px-3.5 py-2.5 text-sm text-stone-100 capitalize focus:border-[var(--accent)] focus:outline-none"
              >
                <option value="">Let the model decide</option>
                {GARMENT_GROUPS.map((group) => (
                  <optgroup key={group.label} label={group.label}>
                    {group.types.map((type) => (
                      <option key={type} value={type}>
                        {type}
                      </option>
                    ))}
                  </optgroup>
                ))}
              </select>
              {/* The runners-up, one click away. On an ambiguous photo the right
                  answer is usually second or third, not absent. */}
              {detection && detection.type_alternatives.length > 1 && (
                <div className="mt-2 flex flex-wrap items-center gap-1.5">
                  <span className="text-[11px] text-stone-500">Not right?</span>
                  {detection.type_alternatives
                    .filter(([type]) => type !== itemType)
                    .slice(0, 3)
                    .map(([type, score]) => (
                      <button
                        key={type}
                        type="button"
                        onClick={() => setItemType(type)}
                        className="rounded-full border border-[#443d34] bg-[#2a2723] px-2.5 py-1 text-xs capitalize text-stone-300 hover:border-[var(--accent)] hover:text-stone-100"
                      >
                        {type} {formatConfidence(score)}
                      </button>
                    ))}
                </div>
              )}
            </div>

            <div>
              <label
                htmlFor="add-dress-color"
                className="block text-xs font-medium uppercase tracking-wider text-stone-400 mb-1.5"
              >
                Color *
              </label>
              <select
                id="add-dress-color"
                value={color}
                onChange={(e) => setColor(e.target.value)}
                className="w-full rounded-md border border-[#38332c] bg-[#211f1c] px-3.5 py-2.5 text-sm text-stone-100 focus:border-[var(--accent)] focus:outline-none"
              >
                {COLOR_OPTIONS.map((opt) => (
                  <option key={opt} value={opt}>
                    {opt}
                  </option>
                ))}
              </select>
              {color === 'Other' && (
                <input
                  type="text"
                  value={customColor}
                  onChange={(e) => setCustomColor(e.target.value)}
                  placeholder="Type a color, e.g. Mustard"
                  aria-label="Custom color"
                  className="mt-2 w-full rounded-md border border-[#38332c] bg-[#211f1c] px-3.5 py-2.5 text-sm text-stone-100 placeholder-stone-500 focus:border-[var(--accent)] focus:outline-none"
                />
              )}
            </div>

            <div>
              <label className="block text-xs font-medium uppercase tracking-wider text-stone-400 mb-1.5">
                Pattern *
              </label>
              <select
                value={pattern}
                onChange={(e) => setPattern(e.target.value)}
                className="w-full rounded-md border border-[#38332c] bg-[#211f1c] px-3.5 py-2.5 text-sm text-stone-100 focus:border-[var(--accent)] focus:outline-none"
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
                className="w-full rounded-md border border-[#38332c] bg-[#211f1c] px-3.5 py-2.5 text-sm text-stone-100 focus:border-[var(--accent)] focus:outline-none"
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
                className="w-full rounded-md border border-[#38332c] bg-[#211f1c] px-3.5 py-2.5 text-sm text-stone-100 focus:border-[var(--accent)] focus:outline-none"
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
                className="w-full rounded-md border border-[#38332c] bg-[#211f1c] px-3.5 py-2.5 text-sm text-stone-100 focus:border-[var(--accent)] focus:outline-none"
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
              className="inline-flex items-center gap-2 rounded-md bg-[var(--accent)] px-5 py-2 text-sm font-medium text-white hover:bg-[var(--accent-hover)] transition-colors disabled:opacity-50"
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
