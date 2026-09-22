import { useQuery } from '@tanstack/react-query'
import { ArrowDownRight, ArrowUpRight, Loader2, TrendingUp } from 'lucide-react'
import { useState } from 'react'
import { fetchTrendFeed, fetchTrendSignals } from '../../api/trendsApi'
import type { TrendFilters, TrendSort } from '../../types/trends'
import { TREND_OCCASIONS, TREND_SEASONS } from '../../types/trends'
import { TrendCard } from './TrendCard'

const SORT_LABELS: Record<TrendSort, string> = {
  momentum: 'Trending now',
  match: 'Best for my wardrobe',
  title: 'A-Z',
}

interface TrendsSectionProps {
  token: string
  onViewItem: (itemId: string) => void
}

export function TrendsSection({ token, onViewItem }: TrendsSectionProps) {
  const [filters, setFilters] = useState<TrendFilters>({
    season: 'All',
    occasion: 'All',
    sort: 'momentum',
    allGenders: false,
  })
  const [expandedId, setExpandedId] = useState<string | null>(null)

  const feedQuery = useQuery({
    queryKey: ['trends', filters],
    queryFn: () => fetchTrendFeed(token, filters),
    enabled: Boolean(token),
  })

  const signalsQuery = useQuery({
    queryKey: ['trend-signals'],
    queryFn: () => fetchTrendSignals(token),
    enabled: Boolean(token),
  })

  const feed = feedQuery.data
  const signals = signalsQuery.data?.signals ?? []

  return (
    <section id="trends" className="scroll-mt-4 space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h2 className="flex items-center gap-2 text-2xl font-bold text-[#1f2328]">
            <TrendingUp className="h-5 w-5 text-[var(--accent)]" />
            Trends
          </h2>
          <p className="text-sm text-[#687068]">
            {feed
              ? `${feed.season} · ${feed.count} looks scored against your ${feed.wardrobe_size} wardrobe item${feed.wardrobe_size === 1 ? '' : 's'}`
              : 'Current-season looks, scored against what you already own.'}
          </p>
        </div>

        {feed && (
          <div className="rounded-lg border border-[#ded8ce] bg-white px-4 py-2 text-sm shadow-sm">
            <span className="text-[#687068]">Average fit </span>
            <span className="font-semibold text-[var(--accent)]">{feed.average_match}%</span>
          </div>
        )}
      </div>

      {/* Wardrobe-derived signals: no editorial input, just the user's own data. */}
      {signals.length > 0 && (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {signals.map((signal) => (
            <div
              key={signal.id}
              className="rounded-xl border border-[#ded8ce] bg-white p-3 shadow-sm"
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
      <div className="flex flex-wrap items-center gap-2 rounded-xl border border-[#ded8ce] bg-white px-3 py-2.5 shadow-sm">
        <label className="flex items-center gap-1.5 text-xs text-[#687068]">
          Season
          <select
            value={filters.season}
            onChange={(event) => setFilters((prev) => ({ ...prev, season: event.target.value }))}
            className="rounded-md border border-[#ded8ce] bg-[#fbfaf7] px-2 py-1 text-sm capitalize text-[#1f2328]"
          >
            {TREND_SEASONS.map((season) => (
              <option key={season} value={season}>
                {season}
              </option>
            ))}
          </select>
        </label>

        <label className="flex items-center gap-1.5 text-xs text-[#687068]">
          Occasion
          <select
            value={filters.occasion}
            onChange={(event) => setFilters((prev) => ({ ...prev, occasion: event.target.value }))}
            className="rounded-md border border-[#ded8ce] bg-[#fbfaf7] px-2 py-1 text-sm capitalize text-[#1f2328]"
          >
            {TREND_OCCASIONS.map((occasion) => (
              <option key={occasion} value={occasion}>
                {occasion.replace(/_/g, ' ')}
              </option>
            ))}
          </select>
        </label>

        <label className="flex items-center gap-1.5 text-xs text-[#687068]">
          Sort
          <select
            value={filters.sort}
            onChange={(event) =>
              setFilters((prev) => ({ ...prev, sort: event.target.value as TrendSort }))
            }
            className="rounded-md border border-[#ded8ce] bg-[#fbfaf7] px-2 py-1 text-sm text-[#1f2328]"
          >
            {(Object.keys(SORT_LABELS) as TrendSort[]).map((sort) => (
              <option key={sort} value={sort}>
                {SORT_LABELS[sort]}
              </option>
            ))}
          </select>
        </label>

        {/* Trends are narrowed to the garments cut for the profile gender.
            Anyone who wants the rest can say so; nothing is hidden for good. */}
        {feed && (feed.gender === 'female' || feed.gender === 'male') && (
          <label className="flex items-center gap-1.5 text-xs text-[#687068]">
            <input
              type="checkbox"
              checked={filters.allGenders}
              onChange={(event) =>
                setFilters((prev) => ({ ...prev, allGenders: event.target.checked }))
              }
              className="h-3.5 w-3.5 accent-[var(--accent)]"
            />
            Show every trend, not just {feed.gender === 'female' ? 'womenswear' : 'menswear'}
          </label>
        )}

        {feedQuery.isFetching && (
          <Loader2 className="ml-auto h-4 w-4 animate-spin text-[var(--accent)]" />
        )}
      </div>

      {feedQuery.isError && (
        <p className="rounded-lg border border-[#e6cfc5] bg-[#fbf3ef] px-4 py-3 text-sm text-[#8c3f27]">
          {feedQuery.error instanceof Error
            ? feedQuery.error.message
            : 'Could not load trends right now.'}
        </p>
      )}

      {feedQuery.isLoading ? (
        <div className="grid gap-4 lg:grid-cols-2">
          {[0, 1, 2, 3].map((key) => (
            <div
              key={key}
              className="h-40 animate-pulse rounded-xl border border-[#ded8ce] bg-white"
            />
          ))}
        </div>
      ) : feed && feed.trends.length > 0 ? (
        <div className="grid items-start gap-4 lg:grid-cols-2">
          {feed.trends.map((trend) => (
            <TrendCard
              key={trend.id}
              trend={trend}
              isExpanded={expandedId === trend.id}
              onToggle={() => setExpandedId((prev) => (prev === trend.id ? null : trend.id))}
              onViewItem={onViewItem}
            />
          ))}
        </div>
      ) : (
        !feedQuery.isError && (
          <p className="rounded-lg border border-dashed border-[#ded8ce] bg-white px-4 py-6 text-center text-sm text-[#687068]">
            No trends match these filters. Try widening the season or occasion.
          </p>
        )
      )}
    </section>
  )
}
