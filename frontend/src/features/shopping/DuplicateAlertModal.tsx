import { useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import { ImageOff, Sparkles, X } from 'lucide-react'
import type { DuplicateDecision, ShoppingAdvisorInsight, SimilarItem } from '../../types/shopping'
import { formatScore } from '../../lib/utils'

interface DuplicateAlertModalProps {
  isOpen: boolean
  onClose: () => void
  /** Local preview of the image the user is considering buying. */
  purchaseImageUrl: string | null
  /** Best match according to the backend ranking, or null when nothing was close enough. */
  match: SimilarItem | null
  /** Remaining backend-ranked matches, shown on request. Ordering is preserved as returned. */
  otherMatches?: SimilarItem[]
  decision?: DuplicateDecision
  /** AI Stylist Shopping Advice comparing candidate with wardrobe items. */
  advisor?: ShoppingAdvisorInsight | null
  /** Omitted when the matched item is not available in the current wardrobe view. */
  onViewItem?: (itemId: string) => void
}

export function DuplicateAlertModal({
  isOpen,
  onClose,
  purchaseImageUrl,
  match,
  otherMatches = [],
  decision,
  advisor,
  onViewItem,
}: DuplicateAlertModalProps) {
  const [showOtherMatches, setShowOtherMatches] = useState(false)

  useEffect(() => {
    if (!isOpen) {
      setShowOtherMatches(false)
      return
    }
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [isOpen, onClose])

  if (!isOpen) return null

  const similarity = formatScore(match?.similarity)
  const isStrongMatch = decision === 'similar_found'

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center overflow-y-auto bg-black/65 p-4 backdrop-blur-md"
      onClick={onClose}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="duplicate-alert-title"
        onClick={(event) => event.stopPropagation()}
        className="relative w-full max-w-2xl overflow-hidden rounded-xl border border-[#38332c] bg-[#1a1917] text-[var(--bg)] shadow-2xl"
      >
        <button
          type="button"
          onClick={onClose}
          aria-label="Close similarity result"
          className="absolute right-4 top-4 z-10 rounded-full bg-black/60 p-2 text-stone-300 backdrop-blur-md transition-colors hover:bg-black/80 hover:text-white focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
        >
          <X className="h-5 w-5" />
        </button>

        <div className="border-b border-[#38332c] px-6 py-5 sm:px-8">
          <h2 id="duplicate-alert-title" className="text-xl font-semibold tracking-tight">
            {match ? 'Similar item found' : 'No similar item found'}
          </h2>
          <p className="mt-1.5 text-sm text-stone-400">
            {match
              ? isStrongMatch
                ? 'This looks very similar to an item already in your wardrobe.'
                : 'Looks similar to an item in your wardrobe. Worth a second look before buying.'
              : 'Nothing in your wardrobe looks close enough to flag as a duplicate.'}
          </p>
        </div>

        <div className="px-6 py-6 sm:px-8">
          {/* AI Shopping Stylist Advisor */}
          {advisor && (
            <div className="mb-5 rounded-lg border border-[#443828] bg-[#241e17] p-4 text-xs">
              <div className="flex items-center justify-between gap-2 mb-2">
                <div className="flex items-center gap-1.5 text-[#d99b77] font-semibold uppercase tracking-wider text-[11px]">
                  <Sparkles className="h-3.5 w-3.5" />
                  AI Stylist Purchase Advice
                </div>
                {advisor.recommendation && (
                  <span
                    className={`rounded-full px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wide ${
                      advisor.recommendation === 'skip'
                        ? 'bg-rose-950/80 text-rose-300 border border-rose-800'
                        : advisor.recommendation === 'buy'
                        ? 'bg-emerald-950/80 text-emerald-300 border border-emerald-800'
                        : 'bg-amber-950/80 text-amber-300 border border-amber-800'
                    }`}
                  >
                    Verdict: {advisor.recommendation.replace('_', ' ')}
                  </span>
                )}
              </div>
              {advisor.headline && (
                <p className="font-semibold text-stone-100 text-sm mb-1">{advisor.headline}</p>
              )}
              {advisor.stylist_reasoning && (
                <p className="text-stone-300 leading-relaxed mb-2">{advisor.stylist_reasoning}</p>
              )}
              {advisor.wardrobe_gap_insight && (
                <p className="text-[#c4a98a] border-t border-[#383023] pt-2 italic">
                  Wardrobe Insight: {advisor.wardrobe_gap_insight}
                </p>
              )}
            </div>
          )}

          <div className="grid gap-5 sm:grid-cols-2">
            <ComparisonPane
              label="Intent to buy"
              imageUrl={purchaseImageUrl}
              alt="The item you are considering buying"
              caption="New item"
            />
            {match ? (
              <ComparisonPane
                label="Your wardrobe"
                imageUrl={match.imageUrl}
                alt={`Wardrobe item: ${match.name}`}
                caption={match.name}
                detail={
                  similarity ? (
                    <span className="inline-flex items-center rounded-full bg-[#332b21] px-2 py-0.5 text-[11px] font-semibold text-[#d99b77]">
                      {similarity} similarity
                    </span>
                  ) : (
                    <span className="text-[11px] text-stone-400">Similarity unavailable</span>
                  )
                }
                note={match.reason}
              />
            ) : (
              <div className="flex min-h-[180px] items-center justify-center rounded-lg border border-dashed border-[#38332c] bg-[#141311] p-4 text-center text-sm text-stone-400">
                No wardrobe match to compare against.
              </div>
            )}
          </div>

          {match && otherMatches.length > 0 && (
            <div className="mt-5">
              <button
                type="button"
                onClick={() => setShowOtherMatches((prev) => !prev)}
                aria-expanded={showOtherMatches}
                className="text-xs font-medium text-[#d99b77] underline-offset-4 hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
              >
                {showOtherMatches ? 'Hide' : 'Show'} {otherMatches.length} other close{' '}
                {otherMatches.length === 1 ? 'match' : 'matches'}
              </button>

              {showOtherMatches && (
                <ul className="mt-3 space-y-2">
                  {otherMatches.map((other) => (
                    <li
                      key={other.id}
                      className="flex items-center justify-between gap-3 rounded-lg border border-[#2b2722] bg-[#211f1c] px-3 py-2 text-xs"
                    >
                      <span className="truncate text-stone-200">{other.name}</span>
                      <span className="shrink-0 text-stone-400">
                        {formatScore(other.similarity) ?? 'n/a'}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </div>

        <div className="flex items-center justify-end gap-3 border-t border-[#38332c] px-6 py-4 sm:px-8">
          <button
            type="button"
            onClick={onClose}
            className="rounded-md border border-[#38332c] bg-stone-900 px-4 py-2 text-sm font-medium text-stone-300 transition-colors hover:bg-stone-800 focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)]"
          >
            Close
          </button>
          {match && onViewItem && (
            <button
              type="button"
              onClick={() => onViewItem(match.id)}
              className="rounded-md bg-[var(--accent)] px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-[var(--accent-hover)] focus:outline-none focus-visible:ring-2 focus-visible:ring-[#d99b77]"
            >
              View Item
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

function ComparisonPane({
  label,
  imageUrl,
  alt,
  caption,
  detail,
  note,
}: {
  label: string
  imageUrl: string | null
  alt: string
  caption: string
  detail?: ReactNode
  note?: string | null
}) {
  return (
    <div className="rounded-lg border border-[#2b2722] bg-[#211f1c] p-4">
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs font-medium uppercase tracking-wider text-stone-400">
          {label}
        </span>
        {detail}
      </div>

      <div className="mt-3 flex aspect-[3/4] w-full items-center justify-center overflow-hidden rounded-md bg-[#141311]">
        {imageUrl ? (
          <img src={imageUrl} alt={alt} className="h-full w-full object-cover" />
        ) : (
          <div className="flex flex-col items-center gap-1 text-stone-400">
            <ImageOff className="h-8 w-8 text-stone-500" />
            <span className="text-xs">No preview</span>
          </div>
        )}
      </div>

      <div className="mt-3">
        <p className="truncate text-sm font-medium text-stone-200">{caption}</p>
        {note && <p className="mt-1 text-xs text-stone-400">{note}</p>}
      </div>
    </div>
  )
}
