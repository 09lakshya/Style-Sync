import { Plus } from 'lucide-react'
import type { WardrobeItem } from '../../types/wardrobe'
import { formatScore } from '../../lib/utils'

interface WardrobeGridProps {
  items: WardrobeItem[]
  isLoading: boolean
  onSelectItem: (item: WardrobeItem) => void
  onAddDressClick: () => void
}

export function WardrobeGrid({ items, isLoading, onSelectItem, onAddDressClick }: WardrobeGridProps) {
  if (isLoading) {
    return (
      <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {Array.from({ length: 8 }).map((_, idx) => (
          <div key={idx} className="animate-pulse rounded-xl border border-[#38332c] bg-[#1a1917] overflow-hidden">
            <div className="h-56 w-full bg-[#26231f]" />
            <div className="p-4 space-y-3">
              <div className="h-4 w-3/4 bg-[#26231f] rounded" />
              <div className="h-3 w-1/2 bg-[#26231f] rounded" />
              <div className="flex gap-2 pt-2">
                <div className="h-5 w-14 bg-[#26231f] rounded-full" />
                <div className="h-5 w-14 bg-[#26231f] rounded-full" />
              </div>
            </div>
          </div>
        ))}
      </div>
    )
  }

  if (items.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-[#38332c] bg-[#141311] py-16 px-6 text-center shadow-inner">
        <h3 className="text-2xl font-bold text-[#f7f4ef]">Your wardrobe is waiting.</h3>
        <p className="mt-2 max-w-md text-sm text-stone-400 leading-relaxed">
          Add your first piece and start building your digital wardrobe.
        </p>
        <button
          type="button"
          onClick={onAddDressClick}
          className="mt-6 inline-flex items-center gap-2 rounded-lg bg-[#a15c38] px-6 py-3 text-sm font-semibold text-white shadow-lg hover:bg-[#b56942] transition-all hover:scale-105"
        >
          <Plus className="h-5 w-5" />
          Add Dress
        </button>
      </div>
    )
  }

  return (
    <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
      {items.map((item) => (
        <article
          key={item.id}
          onClick={() => onSelectItem(item)}
          className="group relative cursor-pointer overflow-hidden rounded-xl border border-[#38332c] bg-[#1a1917] text-[#f7f4ef] transition-all duration-300 hover:-translate-y-1 hover:border-[#a15c38] hover:shadow-xl hover:shadow-black/40"
        >
          {/* Card Image */}
          <div className="relative h-60 w-full overflow-hidden bg-[#11100f]">
            <img
              src={item.thumbnailUrl || item.imageUrl}
              alt={item.name}
              loading="lazy"
              className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-105"
            />
            <div className="absolute inset-0 bg-gradient-to-t from-[#1a1917] via-transparent to-transparent opacity-60" />
            
            {item.brand && (
              <span className="absolute left-3 top-3 rounded-md bg-black/70 px-2.5 py-1 text-xs font-medium text-stone-200 backdrop-blur-md">
                {item.brand}
              </span>
            )}
            
            {item.predictedCategory && (
              <span
                className="absolute right-3 top-3 inline-flex items-center gap-1 rounded-md border border-[#a15c38]/50 bg-[#241a14]/80 px-2.5 py-1 text-xs font-medium text-[#d99b77] backdrop-blur-md"
                title={`AI classified as ${item.predictedCategory}`}
              >
                <span className="capitalize">{item.predictedCategory}</span>
                {formatScore(item.predictionConfidence) && (
                  <span className="text-[11px] text-[#d99b77]/70">
                    {formatScore(item.predictionConfidence)}
                  </span>
                )}
              </span>
            )}
          </div>

          {/* Card Info */}
          <div className="p-4 space-y-3">
            <div>
              <h3 className="font-semibold text-base text-[#f7f4ef] line-clamp-1 group-hover:text-[#d99b77] transition-colors">
                {item.name}
              </h3>
              <p className="mt-0.5 text-xs text-stone-400 capitalize">
                {item.color} • {item.pattern}
              </p>
            </div>

            {/* Tags */}
            <div className="flex flex-wrap gap-1.5">
              {item.occasion.slice(0, 2).map((occ) => (
                <span
                  key={occ}
                  className="rounded-full border border-[#332b21] bg-[#241f19] px-2.5 py-0.5 text-[11px] font-medium text-stone-300 capitalize"
                >
                  {occ}
                </span>
              ))}
            </div>

            {/* Footer */}
            <div className="flex items-center justify-between text-xs text-stone-400 pt-2 border-t border-[#2b2722]">
              <span>{item.wearCount} wears</span>
              <span>{item.lastWornDate}</span>
            </div>
          </div>
        </article>
      ))}
    </div>
  )
}
