import { AlertTriangle, Plus } from 'lucide-react'
import type { Outfit } from '../../types/outfits'
import { ROLE_LABELS } from '../../types/outfits'

interface OutfitCardProps {
  outfit: Outfit
  onViewItem: (itemId: string) => void
}

export function OutfitCard({ outfit, onViewItem }: OutfitCardProps) {
  return (
    <article className="flex flex-col rounded-xl border border-[var(--border)] bg-[var(--surface-raised)] p-4 shadow-sm">
      <div className="mb-3 flex items-start gap-3">
        <div className="min-w-0 flex-1">
          {/* The occasion lives on the section heading, so the card names the
              outfit by its pieces instead of repeating it. */}
          <h3 className="truncate text-base font-semibold text-[#1f2328]">
            {outfit.pieces
              .filter((piece) => piece.role === 'top' || piece.role === 'bottom' || piece.role === 'one_piece')
              .map((piece) => piece.name)
              .join(' + ')}
          </h3>
          <p className="mt-0.5 flex flex-wrap items-center gap-1.5 text-xs capitalize text-[#687068]">
            <span className="rounded-full bg-[var(--accent-soft)] px-2 py-0.5 font-medium text-[var(--accent-ink)]">
              {outfit.style_labels?.[outfit.style] ?? outfit.style}
            </span>
            {outfit.seasons.map((season) => season.replace(/_/g, ' ')).join(' · ')}
            {outfit.total_wears === 0 ? ' · never worn' : ''}
          </p>
        </div>
        <div className="shrink-0 text-right">
          <div className="text-xl font-semibold text-[var(--accent)]">{outfit.score}</div>
          <div className="text-[11px] text-[#687068]">match</div>
        </div>
      </div>

      {/* The pieces themselves, in the order you would put them on. */}
      <div className="flex flex-wrap items-stretch gap-2">
        {outfit.pieces.map((piece, index) => (
          <div key={piece.id} className="flex items-stretch gap-2">
            {index > 0 && (
              <span className="self-center text-[#b9b3a8]">
                <Plus className="h-3.5 w-3.5" />
              </span>
            )}
            <button
              type="button"
              onClick={() => onViewItem(piece.id)}
              className="group w-[104px] text-left"
              title={`${piece.color} ${piece.pattern} ${piece.type}`}
            >
              {piece.image_url ? (
                <img
                  src={piece.image_url}
                  alt={piece.name}
                  className="h-28 w-[104px] rounded-lg border border-[var(--border-soft)] object-cover transition-transform group-hover:scale-[1.02]"
                />
              ) : (
                <div className="grid h-28 w-[104px] place-items-center rounded-lg border border-dashed border-[var(--border)] text-xs text-[#a9a49b]">
                  No photo
                </div>
              )}
              <p className="mt-1 text-[10px] font-medium uppercase tracking-wide text-[#8a8f89]">
                {ROLE_LABELS[piece.role]}
              </p>
              <p className="truncate text-xs font-medium text-[#1f2328]">{piece.name}</p>
            </button>
          </div>
        ))}
      </div>

      {/* Why this pairing, in the app's own words. */}
      {outfit.reasons.length > 0 && (
        <ul className="mt-3 space-y-1.5 text-sm leading-6 text-[#646b64]">
          {outfit.reasons.slice(0, 3).map((reason) => (
            <li key={reason} className="flex gap-2">
              <span className="mt-2.5 h-1 w-1 shrink-0 rounded-full bg-[var(--accent)]" />
              {reason}
            </li>
          ))}
        </ul>
      )}

      {outfit.warnings.length > 0 && (
        <p className="mt-2 flex gap-2 rounded-lg bg-[var(--accent-soft)] px-3 py-2 text-xs leading-5 text-[var(--accent-ink)]">
          <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
          {outfit.warnings[0]}
        </p>
      )}
    </article>
  )
}
