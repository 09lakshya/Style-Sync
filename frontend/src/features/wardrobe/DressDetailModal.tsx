import React, { useState } from 'react'
import { X, Edit2, RefreshCw, Trash2, AlertTriangle, Check, Loader2 } from 'lucide-react'
import type { WardrobeItem } from '../../types/wardrobe'
import { occasionLabel, seasonLabel } from '../../lib/vocabulary'

/** Where the item's details came from, in words. */
function detectedByLabel(modelVersion?: string): string {
  if (modelVersion?.toLowerCase().startsWith('gemini')) {
    return 'Details detected by Gemini. Edit them if anything is off.'
  }
  if (modelVersion) {
    return 'Details detected by the backup model, which is less accurate. Worth checking them.'
  }
  return 'Details entered by hand.'
}

interface DressDetailModalProps {
  item: WardrobeItem | null
  isOpen: boolean
  onClose: () => void
  onEdit: (item: WardrobeItem) => void
  onReplaceImage: (item: WardrobeItem, file: File) => void
  onDelete: (itemId: string) => void
  /** Records one wearing: the server adds 1 and stamps today as the last worn date. */
  onMarkWorn?: (item: WardrobeItem) => void
  isReplacingImage?: boolean
  isDeleting?: boolean
  isMarkingWorn?: boolean
}

/** One axis of the classifier's reading.
 *
 *  An axis with nothing above its threshold prints "No reading" rather than an
 *  empty space: the model declining to answer is a real outcome and looks
 *  identical to a bug if it renders as blank.
 */
function AxisReading({ label, value }: { label: string; value?: string[] | string | null }) {
  const readings = Array.isArray(value) ? value : value ? [value] : []
  return (
    <div>
      <span className="text-stone-400">{label}</span>
      {readings.length > 0 ? (
        <div className="mt-1 flex flex-wrap gap-1">
          {readings.map((reading) => (
            <span
              key={reading}
              className="rounded-full border border-[var(--accent)]/40 px-2 py-0.5 font-medium capitalize text-stone-200"
            >
              {reading.replace(/_/g, ' ')}
            </span>
          ))}
        </div>
      ) : (
        <p className="mt-0.5 font-medium text-stone-500">No reading</p>
      )}
    </div>
  )
}

export function DressDetailModal({
  item,
  isOpen,
  onClose,
  onEdit,
  onReplaceImage,
  onDelete,
  onMarkWorn,
  isReplacingImage,
  isDeleting,
  isMarkingWorn,
}: DressDetailModalProps) {
  const [showConfirmDelete, setShowConfirmDelete] = useState(false)

  if (!isOpen || !item) return null

  function handleImageChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (file && item) {
      onReplaceImage(item, file)
    }
  }

  function confirmDelete() {
    if (item) {
      onDelete(item.id)
      setShowConfirmDelete(false)
      onClose()
    }
  }

  return (
    <>
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/65 backdrop-blur-md p-4 overflow-y-auto">
        <div className="relative w-full max-w-3xl rounded-xl border border-[#38332c] bg-[#1a1917] text-[#f7f4ef] shadow-2xl overflow-hidden">
          <button
            onClick={onClose}
            className="absolute right-4 top-4 z-10 rounded-full bg-black/60 p-2 text-stone-300 backdrop-blur-md hover:bg-black/80 hover:text-white transition-colors"
          >
            <X className="h-5 w-5" />
          </button>

          <div className="grid md:grid-cols-2">
            {/* Left: Image Container */}
            <div className="relative min-h-[320px] bg-stone-900 flex items-center justify-center border-b md:border-b-0 md:border-r border-[#38332c]">
              <img
                src={item.imageUrl || item.mediumUrl || item.thumbnailUrl}
                alt={item.name}
                className="h-full max-h-[460px] w-full object-contain p-2"
              />
              <label className="absolute bottom-4 left-4 cursor-pointer inline-flex items-center gap-2 rounded-lg bg-black/75 px-3 py-1.5 text-xs font-medium text-white backdrop-blur-md hover:bg-stone-800 transition-colors">
                <RefreshCw className={`h-3.5 w-3.5 ${isReplacingImage ? 'animate-spin' : ''}`} />
                {isReplacingImage ? 'Uploading...' : 'Replace Image'}
                <input
                  type="file"
                  accept="image/png,image/jpeg,image/webp"
                  className="sr-only"
                  disabled={isReplacingImage}
                  onChange={handleImageChange}
                />
              </label>
            </div>

            {/* Right: Details & Meta */}
            <div className="flex flex-col justify-between p-6 sm:p-8 space-y-6">
              <div>
                <div className="flex items-center gap-2">
                  <span className="inline-flex items-center rounded-full bg-[#332b21] px-2.5 py-0.5 text-xs font-medium text-[#d99b77] capitalize">
                    {item.type}
                  </span>
                  {item.brand && (
                    <span className="rounded-full bg-stone-800 px-2.5 py-0.5 text-xs font-medium text-stone-300">
                      {item.brand}
                    </span>
                  )}
                </div>

                <h2 className="mt-3 text-2xl font-bold tracking-tight text-[#f7f4ef]">{item.name}</h2>

                {/* Attributes Grid */}
                <div className="mt-6 grid grid-cols-2 gap-4 text-sm">
                  <div className="rounded-lg border border-[#2b2722] bg-[#211f1c] p-3">
                    <span className="text-xs text-stone-400">Color</span>
                    <p className="mt-1 font-semibold text-stone-200 capitalize">{item.color}</p>
                  </div>
                  <div className="rounded-lg border border-[#2b2722] bg-[#211f1c] p-3">
                    <span className="text-xs text-stone-400">Pattern</span>
                    <p className="mt-1 font-semibold text-stone-200 capitalize">{item.pattern}</p>
                  </div>
                  <div className="rounded-lg border border-[#2b2722] bg-[#211f1c] p-3">
                    <span className="text-xs text-stone-400">Occasion</span>
                    <p className="mt-1 font-semibold text-stone-200 capitalize">
                      {item.occasion.map(occasionLabel).join(', ')}
                    </p>
                  </div>
                  <div className="rounded-lg border border-[#2b2722] bg-[#211f1c] p-3">
                    <span className="text-xs text-stone-400">Wear Count</span>
                    <p className="mt-1 font-semibold text-stone-200">
                      {item.wearCount} {item.wearCount === 1 ? 'time' : 'times'}
                    </p>
                    {onMarkWorn && (
                      <button
                        type="button"
                        onClick={() => onMarkWorn(item)}
                        disabled={isMarkingWorn}
                        className="mt-2 inline-flex items-center gap-1.5 rounded-md border border-[#38332c] bg-stone-900 px-2.5 py-1 text-xs font-medium text-stone-300 transition-colors hover:bg-stone-800 disabled:opacity-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
                      >
                        {isMarkingWorn ? (
                          <Loader2 className="h-3.5 w-3.5 animate-spin" />
                        ) : (
                          <Check className="h-3.5 w-3.5" />
                        )}
                        Mark as worn today
                      </button>
                    )}
                  </div>
                </div>

                {/* The item's own season, which the user can correct. The local
                    classifier's separate reading used to sit here with a high
                    confidence score, and it often contradicted these details. */}
                <div className="mt-4 rounded-lg border border-[#2b2722] bg-[#211f1c] p-3 text-sm">
                  <AxisReading label="Season" value={item.season.map(seasonLabel)} />
                  <p className="mt-3 border-t border-[#38332c] pt-2 text-xs text-stone-400">
                    {detectedByLabel(item.modelVersion)}
                  </p>
                </div>

                {/* Dates Section */}
                <div className="mt-4 space-y-2 text-xs text-stone-400">
                  {item.purchaseDate && (
                    <p>Purchased on: <strong className="text-stone-200">{item.purchaseDate}</strong></p>
                  )}
                  <p>Last worn: <strong className="text-stone-200">{item.lastWornDate}</strong></p>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex items-center justify-between pt-4 border-t border-[#38332c]">
                <button
                  type="button"
                  onClick={() => setShowConfirmDelete(true)}
                  disabled={isDeleting}
                  className="inline-flex items-center gap-1.5 text-xs font-medium text-rose-400 hover:text-rose-300 transition-colors disabled:opacity-50"
                >
                  <Trash2 className="h-4 w-4" />
                  Delete item
                </button>

                <button
                  type="button"
                  onClick={() => onEdit(item)}
                  className="inline-flex items-center gap-2 rounded-md bg-[var(--accent)] px-4 py-2 text-sm font-medium text-white hover:bg-[var(--accent-hover)] transition-colors"
                >
                  <Edit2 className="h-4 w-4" />
                  Edit Metadata
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Delete Confirmation Modal */}
      {showConfirmDelete && (
        <div className="fixed inset-0 z-60 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4">
          <div className="w-full max-w-md rounded-xl border border-rose-900/50 bg-[#1c1917] p-6 text-[#f7f4ef] shadow-2xl">
            <div className="flex items-center gap-3 text-rose-400 mb-3">
              <AlertTriangle className="h-6 w-6" />
              <h3 className="text-lg font-semibold">Delete this item?</h3>
            </div>
            <p className="text-sm text-stone-300">
              This will remove &ldquo;{item.name}&rdquo; from your digital wardrobe and delete its image asset permanently.
            </p>
            <div className="mt-6 flex items-center justify-end gap-3">
              <button
                type="button"
                onClick={() => setShowConfirmDelete(false)}
                className="rounded-md border border-[#38332c] bg-stone-900 px-4 py-2 text-sm font-medium text-stone-300 hover:bg-stone-800"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={confirmDelete}
                disabled={isDeleting}
                className="inline-flex items-center gap-2 rounded-md bg-rose-700 px-4 py-2 text-sm font-medium text-white hover:bg-rose-600 disabled:opacity-50"
              >
                {isDeleting ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Delete'}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
