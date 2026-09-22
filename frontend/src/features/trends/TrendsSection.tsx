import { useQuery } from '@tanstack/react-query'
import { ArrowDownRight, ArrowUpRight, ChevronDown, Loader2, Sparkles } from 'lucide-react'
import { useState } from 'react'
import { fetchOutfits } from '../../api/outfitsApi'
import { fetchTrendSignals } from '../../api/trendsApi'
import type { Outfit, OutfitFilters, OutfitGrouping, OutfitSort } from '../../types/outfits'
import {
  OCCASION_ORDER,
  OUTFIT_OCCASIONS,
  OUTFIT_SEASONS,
  OUTFIT_STYLES,
  STYLE_ORDER,
} from '../../types/outfits'
import { OutfitCard } from './OutfitCard'

const SORT_LABELS: Record<OutfitSort, string> = {
  score: 'Best combinations',
  fresh: 'Things you never wear',
}

/** Collect the outfits into sections along one axis.
 *
 *  An outfit appears under every value it covers, not just its headline one. On
 *  the occasion axis, a shirt and jeans logged casual and day-out belong in both
 *  sections. On the style axis, a kurta with jeans is indo-western and, a
 *  little, traditional - so it is findable in both, while a kurta with a
 *  churidar is traditional outright. A value the wardrobe cannot fill gets no
 *  heading at all. */
function groupOutfits(outfits: Outfit[], axis: OutfitGrouping) {
  const order: readonly string[] = axis === 'style' ? STYLE_ORDER : OCCASION_ORDER
  const groups = new Map<string, { label: string; outfits: Outfit[] }>()

  for (const outfit of outfits) {
    const keys =
      axis === 'style'
        ? (outfit.styles?.length ? outfit.styles : [outfit.style])
        : (outfit.occasions?.length ? outfit.occasions : [outfit.occasion])

    for (const key of keys) {
      const label =
        axis === 'style'
          ? (outfit.style_labels?.[key] ?? key)
          : (outfit.occasion_labels?.[key] ?? outfit.occasion_label)

      const group = groups.get(key)
      if (group) {
        group.outfits.push(outfit)
      } else {
        groups.set(key, { label, outfits: [outfit] })
      }
    }
  }

  return [...groups.entries()]
    .sort(([a], [b]) => {
      const rank = (key: string) => {
        const index = order.indexOf(key)
        return index === -1 ? order.length : index
      }
      return rank(a) - rank(b)
    })
    .map(([key, group]) => ({ key, ...group }))
}

interface TrendsSectionProps {
  token: string
  onViewItem: (itemId: string) => void
}

/**
 * Outfits built from the user's own wardrobe: what goes with what, and where to
 * wear it. The pairings and the reasoning come from the backend's rule set, so
 * every card can say why it is on screen.
 */
export function TrendsSection({ token, onViewItem }: TrendsSectionProps) {
  const [filters, setFilters] = useState<OutfitFilters>({
    occasion: 'All',
    season: 'All',
    style: 'All',
    sort: 'score',
    groupBy: 'occasion',
  })

  const outfitsQuery = useQuery({
    queryKey: ['outfits', filters],
    queryFn: () => fetchOutfits(token, filters),
    enabled: Boolean(token),
  })

  const signalsQuery = useQuery({
    queryKey: ['trend-signals'],
    queryFn: () => fetchTrendSignals(token),
    enabled: Boolean(token),
  })

  const data = outfitsQuery.data
  const signals = signalsQuery.data?.signals ?? []
  const groups = data ? groupOutfits(data.outfits, filters.groupBy) : []

  return (
    <section id="trends" className="scroll-mt-4 space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h2 className="flex items-center gap-2 text-2xl font-bold text-[#1f2328]">
            <Sparkles className="h-5 w-5 text-[var(--accent)]" />
            Outfits from your wardrobe
          </h2>
          <p className="text-sm text-[#687068]">
            {data
              ? `${data.count} combination${data.count === 1 ? '' : 's'} from your ${data.wardrobe_size} piece${data.wardrobe_size === 1 ? '' : 's'}, grouped by ${filters.groupBy === 'style' ? 'how traditional they read' : 'where you would wear them'}.`
              : 'What goes with what, built from the pieces you already own.'}
          </p>
        </div>
      </div>

      {/* Wardrobe signals: colour rotation, momentum, what is going unworn. */}
      {signals.length > 0 && (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {signals.map((signal) => (
            <div
              key={signal.id}
              className="rounded-xl border border-[var(--border)] bg-[var(--surface-raised)] p-3 shadow-sm"
            >
              <div className="flex items-center gap-1.5 text-xs font-medium uppercase tracking-wide text-[#8a8f89]">
                {signal.direction === 'up' ? (
                  <ArrowUpRight className="h-3.5 w-3.5 text-[#4a6540]" />
                ) : (
                  <ArrowDownRight className="h-3.5 w-3.5 text-[#8c3f27]" />
                )}
                {signal.label}
              </div>
              <p className="mt-1 truncate text-lg font-semibold capitalize text-[#1f2328]">
                {signal.value}
              </p>
              <p className="mt-1 text-xs leading-5 text-[#687068]">{signal.detail}</p>
            </div>
          ))}
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-2 rounded-xl border border-[var(--border)] bg-[var(--surface-raised)] px-3 py-2.5 shadow-sm">
        <label className="flex items-center gap-1.5 text-xs text-[#687068]">
          Wearing it for
          <select
            value={filters.occasion}
            onChange={(event) => setFilters((prev) => ({ ...prev, occasion: event.target.value }))}
            className="rounded-md border border-[var(--border)] bg-[var(--surface)] px-2 py-1 text-sm capitalize text-[#1f2328]"
          >
            {OUTFIT_OCCASIONS.map((occasion) => (
              <option key={occasion} value={occasion}>
                {occasion.replace(/_/g, ' ')}
              </option>
            ))}
          </select>
        </label>

        <label className="flex items-center gap-1.5 text-xs text-[#687068]">
          Style
          <select
            value={filters.style}
            onChange={(event) => setFilters((prev) => ({ ...prev, style: event.target.value }))}
            className="rounded-md border border-[var(--border)] bg-[var(--surface)] px-2 py-1 text-sm capitalize text-[#1f2328]"
          >
            {OUTFIT_STYLES.map((style) => (
              <option key={style} value={style}>
                {style === 'fusion' ? 'indo-western' : style}
              </option>
            ))}
          </select>
        </label>

        <label className="flex items-center gap-1.5 text-xs text-[#687068]">
          Season
          <select
            value={filters.season}
            onChange={(event) => setFilters((prev) => ({ ...prev, season: event.target.value }))}
            className="rounded-md border border-[var(--border)] bg-[var(--surface)] px-2 py-1 text-sm capitalize text-[#1f2328]"
          >
            {OUTFIT_SEASONS.map((season) => (
              <option key={season} value={season}>
                {season}
              </option>
            ))}
          </select>
        </label>

        <label className="flex items-center gap-1.5 text-xs text-[#687068]">
          Show
          <select
            value={filters.sort}
            onChange={(event) =>
              setFilters((prev) => ({ ...prev, sort: event.target.value as OutfitSort }))
            }
            className="rounded-md border border-[var(--border)] bg-[var(--surface)] px-2 py-1 text-sm text-[#1f2328]"
          >
            {(Object.keys(SORT_LABELS) as OutfitSort[]).map((sort) => (
              <option key={sort} value={sort}>
                {SORT_LABELS[sort]}
              </option>
            ))}
          </select>
        </label>

        <label className="flex items-center gap-1.5 text-xs text-[#687068]">
          Group by
          <select
            value={filters.groupBy}
            onChange={(event) =>
              setFilters((prev) => ({ ...prev, groupBy: event.target.value as OutfitGrouping }))
            }
            className="rounded-md border border-[var(--border)] bg-[var(--surface)] px-2 py-1 text-sm text-[#1f2328]"
          >
            <option value="occasion">Occasion</option>
            <option value="style">Traditional or western</option>
          </select>
        </label>

        {outfitsQuery.isFetching && (
          <Loader2 className="ml-auto h-4 w-4 animate-spin text-[var(--accent)]" />
        )}
      </div>

      {outfitsQuery.isError && (
        <p className="rounded-lg border border-[#e6cfc5] bg-[#fbf3ef] px-4 py-3 text-sm text-[#8c3f27]">
          {outfitsQuery.error instanceof Error
            ? outfitsQuery.error.message
            : 'Could not build outfits right now.'}
        </p>
      )}

      {outfitsQuery.isLoading ? (
        <div className="grid gap-4 lg:grid-cols-2">
          {[0, 1, 2, 3].map((key) => (
            <div
              key={key}
              className="h-56 animate-pulse rounded-xl border border-[var(--border)] bg-[var(--surface-raised)]"
            />
          ))}
        </div>
      ) : groups.length > 0 ? (
        <div className="space-y-3">
          {/* Each category is its own dropdown. The first opens by default so the
              section is never a wall of closed headings; <details> gives the
              open/close behaviour and keyboard support without extra state. */}
          {groups.map((group, index) => (
            <details
              key={group.key}
              open={index === 0}
              className="group rounded-xl border border-[var(--border)] bg-[var(--surface)] px-4 py-3 shadow-sm"
            >
              <summary className="flex cursor-pointer list-none items-center gap-2 text-[#1f2328] marker:hidden">
                <ChevronDown className="h-4 w-4 shrink-0 text-[#8a8f89] transition-transform group-open:rotate-180" />
                <h3 className="text-lg font-semibold">{group.label}</h3>
                <span className="text-xs text-[#687068]">
                  {group.outfits.length} outfit{group.outfits.length === 1 ? '' : 's'}
                </span>
              </summary>

              <div className="mt-4 grid items-start gap-4 border-t border-[var(--rule)] pt-4 lg:grid-cols-2">
                {group.outfits.map((outfit) => (
                  <OutfitCard
                    key={`${group.key}-${outfit.id}`}
                    outfit={outfit}
                    onViewItem={onViewItem}
                  />
                ))}
              </div>
            </details>
          ))}
        </div>
      ) : (
        !outfitsQuery.isError && (
          <div className="rounded-lg border border-dashed border-[var(--border)] bg-[var(--surface-raised)] px-4 py-6 text-center text-sm text-[#687068]">
            {/* An empty wardrobe is not an error, so say what would fix it. */}
            {data && data.gaps.length > 0 ? (
              <ul className="space-y-1">
                {data.gaps.map((gap) => (
                  <li key={gap}>{gap}</li>
                ))}
              </ul>
            ) : (
              'No outfits match these filters. Try widening the occasion or season.'
            )}
          </div>
        )
      )}
    </section>
  )
}
