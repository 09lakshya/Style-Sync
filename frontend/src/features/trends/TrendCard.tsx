import { Check, ChevronDown, Minus } from 'lucide-react'
import type { Trend, TrendStatus } from '../../types/trends'
import { COLOR_SWATCHES } from '../../types/trends'

const STATUS_STYLES: Record<TrendStatus, string> = {
  peaking: 'bg-[#f3e2dc] text-[#8c3f27]',
  rising: 'bg-[#e6ece2] text-[#4a6540]',
  steady: 'bg-[#eae6df] text-[#5e645e]',
  cooling: 'bg-[#eceaf0] text-[#5a5470]',
}

function readable(value: string) {
  return value.replace(/_/g, ' ')
}

interface TrendCardProps {
  trend: Trend
  isExpanded: boolean
  onToggle: () => void
  onViewItem: (itemId: string) => void
}

export function TrendCard({ trend, isExpanded, onToggle, onViewItem }: TrendCardProps) {
  const { match } = trend

  return (
    <article className="flex flex-col rounded-xl border border-[#ded8ce] bg-white shadow-sm">
      <div className="flex flex-col gap-3 p-4">
        <div className="flex items-start gap-3">
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <h3 className="text-base font-semibold text-[#1f2328]">{trend.title}</h3>
              <span
                className={`rounded-full px-2 py-0.5 text-xs font-medium capitalize ${STATUS_STYLES[trend.status]}`}
              >
                {trend.status}
              </span>
            </div>
            <p className="mt-1.5 text-sm leading-6 text-[#646b64]">{trend.summary}</p>
          </div>

          {/* Fit score: how much of this look the wardrobe already covers. */}
          <div className="shrink-0 text-right">
            <div className="text-2xl font-semibold text-[var(--accent)]">{match.score}%</div>
            <div className="text-xs text-[#687068]">wardrobe fit</div>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <div className="flex items-center gap-1" title={trend.palette.join(', ')}>
            {trend.palette.map((color) => (
              <span
                key={color}
                className="h-4 w-4 rounded-full border border-[#ded8ce]"
                style={{ backgroundColor: COLOR_SWATCHES[color] ?? '#ccc' }}
                aria-label={color}
              />
            ))}
          </div>
          <span className="text-xs text-[#687068]">
            {match.owned_count} of {match.total_pieces} key pieces owned · {match.verdict}
          </span>
        </div>

        {/* Progress bar mirrors the fit score for a quick scan down the list. */}
        <div className="h-1.5 w-full overflow-hidden rounded-full bg-[#eee8de]">
          <div
            className="h-full rounded-full bg-[var(--accent)] transition-[width] duration-300"
            style={{ width: `${Math.max(match.score, 2)}%` }}
          />
        </div>

        <button
          onClick={onToggle}
          className="inline-flex items-center gap-1 self-start text-sm font-medium text-[var(--accent)] hover:text-[var(--accent-hover)]"
          aria-expanded={isExpanded}
        >
          {isExpanded ? 'Hide details' : 'How to wear it'}
          <ChevronDown
            className={`h-4 w-4 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
          />
        </button>
      </div>

      {isExpanded && (
        <div className="space-y-4 border-t border-[#eee8de] p-4">
          <div>
            <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-[#8a8f89]">
              Key pieces
            </h4>
            <ul className="space-y-2">
              {trend.match.pieces.map((piece) => (
                <li
                  key={piece.label}
                  className="flex items-center gap-3 rounded-lg border border-[#e2dcd1] bg-[#fbfaf7] p-2"
                >
                  {piece.match?.image_url ? (
                    <img
                      src={piece.match.image_url}
                      alt={piece.match.name}
                      className="h-12 w-12 shrink-0 rounded-md object-cover"
                    />
                  ) : (
                    <span className="grid h-12 w-12 shrink-0 place-items-center rounded-md border border-dashed border-[#cfc7bb] text-[#a9a49b]">
                      <Minus className="h-4 w-4" />
                    </span>
                  )}

                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-[#1f2328]">{piece.label}</p>
                    <p className="truncate text-xs text-[#687068]">{piece.note}</p>
                  </div>

                  {piece.owned ? (
                    piece.match ? (
                      <button
                        onClick={() => onViewItem(piece.match!.id)}
                        className="shrink-0 rounded-full bg-[#e6ece2] px-2.5 py-1 text-xs font-medium text-[#4a6540] hover:bg-[#dbe4d5]"
                      >
                        <Check className="mr-1 inline h-3 w-3" />
                        In wardrobe
                      </button>
                    ) : null
                  ) : (
                    <span className="shrink-0 rounded-full bg-[#f3ece4] px-2.5 py-1 text-xs font-medium text-[#8c6a4f]">
                      Gap
                    </span>
                  )}
                </li>
              ))}
            </ul>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-[#8a8f89]">
                Styling
              </h4>
              <ul className="space-y-1.5 text-sm leading-6 text-[#646b64]">
                {trend.styling_tips.map((tip) => (
                  <li key={tip} className="flex gap-2">
                    <span className="mt-2 h-1 w-1 shrink-0 rounded-full bg-[var(--accent)]" />
                    {tip}
                  </li>
                ))}
              </ul>
            </div>

            <div className="space-y-3">
              {trend.avoid.length > 0 && (
                <div>
                  <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-[#8a8f89]">
                    Skip
                  </h4>
                  <p className="text-sm leading-6 text-[#646b64]">{trend.avoid.join(' · ')}</p>
                </div>
              )}

              <div>
                <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-[#8a8f89]">
                  Best for
                </h4>
                <div className="flex flex-wrap gap-1.5">
                  {[...trend.occasions, ...trend.seasons].map((tag) => (
                    <span
                      key={tag}
                      className="rounded-full border border-[#e2dcd1] bg-[#fbfaf7] px-2 py-0.5 text-xs capitalize text-[#5e645e]"
                    >
                      {readable(tag)}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </article>
  )
}
