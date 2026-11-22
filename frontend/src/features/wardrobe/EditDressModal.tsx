import React, { useState } from 'react'
import { X, Loader2, AlertCircle } from 'lucide-react'
import type { UpdateDressMetadataInput, WardrobeItem } from '../../types/wardrobe'
import { GARMENT_GROUPS, OCCASIONS, SEASONS, toOccasion } from '../../lib/vocabulary'

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

/** Matches a stored colour to a list entry, case-insensitively; anything else is "Other". */
function toColorOption(stored?: string): string {
  if (!stored) return 'Blue'
  const known = COLOR_OPTIONS.find((opt) => opt.toLowerCase() === stored.trim().toLowerCase())
  return known ?? 'Other'
}

/** The free-text colour to seed the input with: empty unless the colour is a custom one. */
function toCustomColor(stored?: string): string {
  if (!stored) return ''
  return toColorOption(stored) === 'Other' ? stored.trim() : ''
}

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

/** The pattern option a stored value belongs to, matched case-insensitively.
 *  A pattern that is not in the list (zari, block print...) is kept as its own
 *  option rather than being silently replaced. */
function toPatternOption(stored?: string): string {
  if (!stored) return 'Solid'
  return PATTERN_OPTIONS.find((opt) => opt.toLowerCase() === stored.trim().toLowerCase()) ?? stored
}

function storedOccasions(item: WardrobeItem | null): string[] {
  const values = (item?.occasion ?? []).map(toOccasion).filter((o): o is string => Boolean(o))
  return values.length ? [...new Set(values)] : ['casual']
}

function storedSeasons(item: WardrobeItem | null): string[] {
  const values = (item?.season ?? []).filter((s) => SEASONS.some((opt) => opt.value === s))
  return values.length ? values : ['all_season']
}

function toggle(values: string[], value: string): string[] {
  return values.includes(value) ? values.filter((v) => v !== value) : [...values, value]
}

export function EditDressModal({ item, isOpen, onClose, onSubmit, isSubmitting }: EditDressModalProps) {
  const [name, setName] = useState(item?.name || '')
  // A colour saved as free text is not in the list, so the select shows "Other"
  // and the text field is seeded with it.
  const [color, setColor] = useState(() => toColorOption(item?.color))
  const [customColor, setCustomColor] = useState(() => toCustomColor(item?.color))
  const [pattern, setPattern] = useState(() => toPatternOption(item?.pattern))
  const [itemType, setItemType] = useState(item?.type || '')
  const [brand, setBrand] = useState(item?.brand || '')
  const [purchaseDate, setPurchaseDate] = useState(item?.purchaseDate || '')
  const [occasions, setOccasions] = useState(() => storedOccasions(item))
  const [seasons, setSeasons] = useState(() => storedSeasons(item))
  const [lastWornDate, setLastWornDate] = useState(item?.lastWornDate !== 'Not worn yet' ? item?.lastWornDate || '' : '')
  // Kept as a string so the field can be cleared while typing.
  const [wearCount, setWearCount] = useState(String(item?.wearCount ?? 0))
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  // Sync state if item changes
  React.useEffect(() => {
    if (item) {
      setName(item.name)
      setColor(toColorOption(item.color))
      setCustomColor(toCustomColor(item.color))
      setPattern(toPatternOption(item.pattern))
      setItemType(item.type)
      setBrand(item.brand || '')
      setPurchaseDate(item.purchaseDate || '')
      setOccasions(storedOccasions(item))
      setSeasons(storedSeasons(item))
      setLastWornDate(item.lastWornDate !== 'Not worn yet' ? item.lastWornDate : '')
      setWearCount(String(item.wearCount ?? 0))
    }
  }, [item])

  if (!isOpen || !item) return null

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!name.trim()) {
      setErrorMessage('Please enter a name.')
      return
    }

    const parsedWearCount = Number(wearCount)
    if (!Number.isInteger(parsedWearCount) || parsedWearCount < 0) {
      setErrorMessage('Times worn must be a whole number of 0 or more.')
      return
    }

    const resolvedColor = color === 'Other' ? customColor.trim() : color
    if (!resolvedColor) {
      setErrorMessage('Please type a color, or pick one from the list.')
      return
    }

    if (occasions.length === 0) {
      setErrorMessage('Pick at least one occasion.')
      return
    }
    if (seasons.length === 0) {
      setErrorMessage('Pick at least one season.')
      return
    }

    setErrorMessage(null)
    onSubmit({
      id: item!.id,
      name: name.trim(),
      color: resolvedColor,
      pattern,
      brand: brand.trim(),
      purchaseDate,
      occasions,
      seasons,
      itemType,
      lastWornDate,
      wearCount: parsedWearCount,
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
          <h2 className="text-2xl font-semibold tracking-tight text-[#f7f4ef]">Edit item</h2>
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
              Name *
            </label>
            <input
              type="text"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full rounded-md border border-[#38332c] bg-[#211f1c] px-3.5 py-2.5 text-sm text-stone-100 placeholder-stone-500 focus:border-[var(--accent)] focus:outline-none"
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
                className="w-full rounded-md border border-[#38332c] bg-[#211f1c] px-3.5 py-2.5 text-sm text-stone-100 placeholder-stone-500 focus:border-[var(--accent)] focus:outline-none"
              />
            </div>

            <div>
              <label
                htmlFor="edit-dress-color"
                className="block text-xs font-medium uppercase tracking-wider text-stone-400 mb-1.5"
              >
                Color *
              </label>
              <select
                id="edit-dress-color"
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
                {(PATTERN_OPTIONS.includes(pattern) ? PATTERN_OPTIONS : [pattern, ...PATTERN_OPTIONS]).map((opt) => (
                  <option key={opt} value={opt}>
                    {opt}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label
                htmlFor="edit-dress-type"
                className="block text-xs font-medium uppercase tracking-wider text-stone-400 mb-1.5"
              >
                Garment type *
              </label>
              <select
                id="edit-dress-type"
                value={itemType}
                onChange={(e) => setItemType(e.target.value)}
                className="w-full rounded-md border border-[#38332c] bg-[#211f1c] px-3.5 py-2.5 text-sm text-stone-100 capitalize focus:border-[var(--accent)] focus:outline-none"
              >
                {!GARMENT_GROUPS.some((group) => group.types.includes(itemType)) && (
                  <option value={itemType}>{itemType || 'Pick a type'}</option>
                )}
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

            <div>
              <label
                htmlFor="edit-wear-count"
                className="block text-xs font-medium uppercase tracking-wider text-stone-400 mb-1.5"
              >
                Times Worn
              </label>
              <input
                id="edit-wear-count"
                type="number"
                min={0}
                step={1}
                value={wearCount}
                onChange={(e) => setWearCount(e.target.value)}
                className="w-full rounded-md border border-[#38332c] bg-[#211f1c] px-3.5 py-2.5 text-sm text-stone-100 focus:border-[var(--accent)] focus:outline-none"
              />
              <p className="mt-1.5 text-xs text-stone-500">
                Correct the running total. Use &ldquo;Mark as worn today&rdquo; to log a single wearing.
              </p>
            </div>
          </div>

          <ChipGroup
            label="Occasions *"
            options={OCCASIONS}
            selected={occasions}
            onToggle={(value) => setOccasions((prev) => toggle(prev, value))}
          />

          <ChipGroup
            label="Seasons *"
            options={SEASONS}
            selected={seasons}
            onToggle={(value) => setSeasons((prev) => toggle(prev, value))}
          />

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

function ChipGroup({
  label,
  options,
  selected,
  onToggle,
}: {
  label: string
  options: readonly { value: string; label: string }[]
  selected: string[]
  onToggle: (value: string) => void
}) {
  return (
    <fieldset>
      <legend className="block text-xs font-medium uppercase tracking-wider text-stone-400 mb-1.5">
        {label}
      </legend>
      <div className="flex flex-wrap gap-1.5">
        {options.map((option) => {
          const active = selected.includes(option.value)
          return (
            <button
              key={option.value}
              type="button"
              aria-pressed={active}
              onClick={() => onToggle(option.value)}
              className={
                active
                  ? 'rounded-full border border-[var(--accent)] bg-[var(--accent)] px-3 py-1 text-xs font-medium text-white'
                  : 'rounded-full border border-[#443d34] bg-[#2a2723] px-3 py-1 text-xs text-stone-300 hover:border-[var(--accent)] hover:text-stone-100'
              }
            >
              {option.label}
            </button>
          )
        })}
      </div>
    </fieldset>
  )
}
