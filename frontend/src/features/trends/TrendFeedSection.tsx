import { useQuery } from '@tanstack/react-query'
import { Check, Loader2, Plus, TrendingUp } from 'lucide-react'
import { useState } from 'react'
import { fetchTrendFeed } from '../../api/trendsApi'
import type { Trend, TrendFilters, TrendSort } from '../../types/trends'

interface TrendFeedSectionProps {
  token: string
  onViewItem: (itemId: string) => void
}

const STATUS_LABELS: Record<Trend['status'], string> = {
  peaking: 'Peaking',
  rising: 'Rising',
  steady: 'Steady',
  cooling: 'Cooling',
}

// Enough to read at a glance; the rest are one click away.
const INITIAL_COUNT = 4

/**
 * The season's curated looks, each scored against what the user already owns:
 * which key pieces they have (and which item covers each), and what is missing.
 * The catalogue is editorial data kept in the backend (trends/catalog.py).
 */
export function TrendFeedSection({ token, onViewItem }: TrendFeedSectionProps) {
  const [sort, setSort] = useState<TrendSort>('match')
  const [showAll, setShowAll] = useState(false)
  const filters: TrendFilters = { season: 'All', occasion: 'All', sort, allGenders: false }

  const feedQuery = useQuery({
    queryKey: ['trend-feed', sort],
    queryFn: () => fetchTrendFeed(token, filters),
    enabled: Boolean(token),
  })

  const feed = feedQuery.data
  const trends = feed?.trends ?? []
  const shown = showAll ? trends : trends.slice(0, INITIAL_COUNT)

  return (
    <section id="season-trends" className="scroll-mt-4 space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h2 className="flex items-center gap-2 text-2xl font-bold text-[#1f2328]">
            <TrendingUp className="h-5 w-5 text-[var(--accent)]" />
            This season&rsquo;s trends
          </h2>
          <p className="text-sm text-[#687068]">
            {feed
              ? `${feed.season} looks, scored against the ${feed.wardrobe_size} piece${feed.wardrobe_size === 1 ? '' : 's'} you own.`
              : 'Current looks, scored against what you already own.'}
          </p>
        </div>
        <label className="flex items-center gap-2 text-sm text-[#687068]">
          Sort by
          <select
            value={sort}
            onChange={(event) => setSort(event.target.value as TrendSort)}
            className="rounded-md border border-[var(--border)] bg-[var(--surface)] px-2 py-1 text-sm text-[#1f2328]"
          >
            <option value="match">Best match for you</option>
            <option value="momentum">Hottest right now</option>
          </select>
          {feedQuery.isFetching && <Loader2 className="h-4 w-4 animate-spin text-[var(--accent)]" />}
        </label>
      </div>

      {feedQuery.isError && (
        <p className="rounded-lg border border-[#e6cfc5] bg-[#fbf3ef] px-4 py-3 text-sm text-[#8c3f27]">
          {feedQuery.error instanceof Error ? feedQuery.error.message : 'Could not load the trends right now.'}
        </p>
      )}

      {feedQuery.isLoading ? (
        <div className="grid gap-4 lg:grid-cols-2">
          {[0, 1].map((key) => (
            <div key={key} className="h-48 animate-pulse rounded-xl border border-[var(--border)] bg-[var(--surface-raised)]" />
          ))}
        </div>
      ) : (
        <>
          <div className="grid items-start gap-4 lg:grid-cols-2">
            {shown.map((trend) => (
              <TrendCard key={trend.id} trend={trend} onViewItem={onViewItem} />
            ))}
          </div>
          {trends.length > INITIAL_COUNT && (
            <button
              type="button"
              onClick={() => setShowAll((prev) => !prev)}
              className="rounded-md border border-[var(--border)] bg-[var(--surface)] px-4 py-2 text-sm font-medium text-[#1f2328] hover:border-[var(--accent)]"
            >
              {showAll ? 'Show fewer' : `Show all ${trends.length} trends`}
            </button>
          )}
        </>
      )}
    </section>
  )
}

function TrendCard({ trend, onViewItem }: { trend: Trend; onViewItem: (itemId: string) => void }) {
  const { match } = trend
  return (
    <article className="rounded-xl border border-[var(--border)] bg-[var(--surface-raised)] p-4 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="text-lg font-semibold text-[#1f2328]">{trend.title}</h3>
          <p className="mt-0.5 text-xs text-[#687068]">
            <span className="rounded-full bg-[var(--accent-soft)] px-2 py-0.5 font-medium text-[var(--accent-ink)]">
              {STATUS_LABELS[trend.status]}
            </span>{' '}
            You own {match.owned_count} of {match.total_pieces} key pieces &middot; {match.verdict}
          </p>
        </div>
        <div className="shrink-0 text-right">
          <p className="text-2xl font-semibold text-[var(--accent)]">{match.score}</p>
          <p className="text-[11px] text-[#687068]">match</p>
        </div>
      </div>

      <p className="mt-3 text-sm leading-6 text-[#4f554f]">{trend.summary}</p>

      <ul className="mt-3 space-y-1.5">
        {match.pieces.map((piece) => (
          <li key={piece.label} className="flex items-start gap-2 text-sm">
            {piece.owned ? (
              <Check className="mt-0.5 h-4 w-4 shrink-0 text-[#4a6540]" aria-label="Owned" />
            ) : (
              <Plus className="mt-0.5 h-4 w-4 shrink-0 text-[#8a8f89]" aria-label="Missing" />
            )}
            <span className="min-w-0">
              <span className="font-medium text-[#1f2328]">{piece.label}</span>
              {piece.owned && piece.match ? (
                <>
                  {' '}
                  &ndash;{' '}
                  <button
                    type="button"
                    onClick={() => onViewItem(piece.match!.id)}
                    className="text-[var(--accent-ink)] underline decoration-dotted underline-offset-2 hover:text-[var(--accent)]"
                  >
                    {piece.match.name}
                  </button>
                </>
              ) : piece.note.startsWith('Closest') ? (
                // A near miss: the right garment without the look's pattern.
                <span className="text-[#8a8f89]"> &ndash; {piece.note}</span>
              ) : (
                <span className="text-[#8a8f89]"> &ndash; not in your wardrobe yet</span>
              )}
            </span>
          </li>
        ))}
      </ul>

      {trend.styling_tips[0] && (
        <p className="mt-3 rounded-lg bg-[var(--surface)] px-3 py-2 text-xs leading-5 text-[#5e645e]">
          <span className="font-semibold text-[#1f2328]">Styling tip: </span>
          {trend.styling_tips[0]}
        </p>
      )}
    </article>
  )
}
