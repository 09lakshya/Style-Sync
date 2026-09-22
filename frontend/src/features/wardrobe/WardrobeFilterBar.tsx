import React from 'react'
import { Search } from 'lucide-react'
import type { WardrobeFilterState } from '../../types/wardrobe'

interface WardrobeFilterBarProps {
  filters: WardrobeFilterState
  onChange: (nextFilters: WardrobeFilterState) => void
  totalCount: number
}

const COLOR_OPTIONS = ['All', 'Black', 'White', 'Blue', 'Red', 'Green', 'Yellow', 'Pink', 'Purple', 'Brown', 'Beige', 'Grey']
const PATTERN_OPTIONS = ['All', 'Solid', 'Floral', 'Striped', 'Checked', 'Printed', 'Polka Dot', 'Geometric', 'Embroidered']
const OCCASION_OPTIONS = ['All', 'Casual', 'Formal', 'Party', 'College', 'Office', 'Wedding', 'Sports', 'Travel', 'Traditional']

export function WardrobeFilterBar({ filters, onChange, totalCount }: WardrobeFilterBarProps) {
  function handleSearchChange(e: React.ChangeEvent<HTMLInputElement>) {
    onChange({ ...filters, searchQuery: e.target.value })
  }

  function handleColorChange(e: React.ChangeEvent<HTMLSelectElement>) {
    onChange({ ...filters, color: e.target.value })
  }

  function handlePatternChange(e: React.ChangeEvent<HTMLSelectElement>) {
    onChange({ ...filters, pattern: e.target.value })
  }

  function handleOccasionChange(e: React.ChangeEvent<HTMLSelectElement>) {
    onChange({ ...filters, occasion: e.target.value })
  }

  function handleSortChange(e: React.ChangeEvent<HTMLSelectElement>) {
    onChange({ ...filters, sortBy: e.target.value as WardrobeFilterState['sortBy'] })
  }

  function clearFilters() {
    onChange({
      searchQuery: '',
      color: 'All',
      pattern: 'All',
      occasion: 'All',
      sortBy: 'recently_added',
    })
  }

  const hasActiveFilters =
    filters.searchQuery.trim() !== '' ||
    filters.color !== 'All' ||
    filters.pattern !== 'All' ||
    filters.occasion !== 'All' ||
    filters.sortBy !== 'recently_added'

  return (
    <div className="rounded-xl border border-[#38332c] bg-[#1a1917] p-4 text-[#f7f4ef] shadow-lg">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        {/* Search Input */}
        <div className="relative flex-1">
          <Search className="absolute left-3.5 top-3 h-4 w-4 text-stone-400" />
          <input
            type="text"
            placeholder="Search dresses by name or brand..."
            value={filters.searchQuery}
            onChange={handleSearchChange}
            className="w-full rounded-lg border border-[#38332c] bg-[#211f1c] pl-10 pr-4 py-2 text-sm text-stone-100 placeholder-stone-400 focus:border-[var(--accent)] focus:outline-none transition-colors"
          />
        </div>

        {/* Filter & Sort Controls */}
        <div className="flex flex-wrap items-center gap-2 sm:gap-3">
          <div className="flex items-center gap-1.5 rounded-lg border border-[#38332c] bg-[#211f1c] px-3 py-1.5 text-xs text-stone-300">
            <span className="hidden sm:inline font-medium">Filters:</span>

            {/* Color */}
            <select
              value={filters.color}
              onChange={handleColorChange}
              className="bg-transparent text-xs text-stone-200 focus:outline-none cursor-pointer"
            >
              <option value="All" className="bg-[#1a1917]">All Colors</option>
              {COLOR_OPTIONS.filter((c) => c !== 'All').map((c) => (
                <option key={c} value={c} className="bg-[#1a1917]">
                  {c}
                </option>
              ))}
            </select>

            <span className="text-stone-600">|</span>

            {/* Pattern */}
            <select
              value={filters.pattern}
              onChange={handlePatternChange}
              className="bg-transparent text-xs text-stone-200 focus:outline-none cursor-pointer"
            >
              <option value="All" className="bg-[#1a1917]">All Patterns</option>
              {PATTERN_OPTIONS.filter((p) => p !== 'All').map((p) => (
                <option key={p} value={p} className="bg-[#1a1917]">
                  {p}
                </option>
              ))}
            </select>

            <span className="text-stone-600">|</span>

            {/* Occasion */}
            <select
              value={filters.occasion}
              onChange={handleOccasionChange}
              className="bg-transparent text-xs text-stone-200 focus:outline-none cursor-pointer"
            >
              <option value="All" className="bg-[#1a1917]">All Occasions</option>
              {OCCASION_OPTIONS.filter((o) => o !== 'All').map((o) => (
                <option key={o} value={o} className="bg-[#1a1917]">
                  {o}
                </option>
              ))}
            </select>
          </div>

          {/* Sort Select */}
          <div className="flex items-center gap-1.5 rounded-lg border border-[#38332c] bg-[#211f1c] px-3 py-1.5 text-xs text-stone-300">
            <span className="hidden sm:inline font-medium">Sort:</span>
            <select
              value={filters.sortBy}
              onChange={handleSortChange}
              className="bg-transparent text-xs text-stone-200 focus:outline-none cursor-pointer"
            >
              <option value="recently_added" className="bg-[#1a1917]">Recently Added</option>
              <option value="oldest_added" className="bg-[#1a1917]">Oldest Added</option>
              <option value="recently_worn" className="bg-[#1a1917]">Recently Worn</option>
              <option value="least_recently_worn" className="bg-[#1a1917]">Least Recently Worn</option>
            </select>
          </div>

          {hasActiveFilters && (
            <button
              onClick={clearFilters}
              className="text-xs text-[var(--accent)] underline hover:text-[var(--accent-hover)] transition-colors"
            >
              Reset
            </button>
          )}
        </div>
      </div>

      <div className="mt-3 flex items-center justify-between text-xs text-stone-400 border-t border-[#2d2924] pt-2.5">
        <span>Showing <strong>{totalCount}</strong> wardrobe piece{totalCount !== 1 ? 's' : ''}</span>
      </div>
    </div>
  )
}
