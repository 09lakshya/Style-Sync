export function EditorialVisual() {
  return (
    <aside className="relative hidden lg:flex flex-col justify-between w-full h-full min-h-screen overflow-hidden bg-[#0A0A09] p-12 lg:p-16 border-r border-white/10 select-none">
      {/* Background Image with subtle dark gradient overlay */}
      <div className="absolute inset-0 z-0 overflow-hidden">
        <img
          src="/anushka.jpg"
          alt="StyleSync Haute Couture Editorial Visual"
          className="h-full w-full object-cover object-top opacity-85 scale-105 transition-transform duration-1000 ease-out hover:scale-100"
        />
        <div className="absolute inset-0 bg-gradient-to-t from-[#0A0A09] via-[#0A0A09]/30 to-transparent" />
        <div className="absolute inset-0 bg-gradient-to-r from-transparent via-transparent to-[#0A0A09]/60" />
      </div>

      {/* Bottom Editorial Copy */}
      <div className="relative z-10 max-w-lg space-y-4 mt-auto">
        <h2 className="font-serif-editorial text-4xl xl:text-5xl font-light text-[#F5F2EB] leading-tight tracking-wide">
          Curate your wardrobe with surgical precision.
        </h2>
        <p className="text-sm font-sans-ui text-[#B8AD9A] leading-relaxed tracking-wide">
          Digital closet organization, duplicate purchase prevention, and AI-tailored outfit curation designed for modern elegance.
        </p>

        <div className="pt-6 border-t border-white/10 flex items-center gap-8 text-xs text-[#B8AD9A]/80 uppercase tracking-widest font-sans-ui">
          <div>
            <span className="block text-[#F5F2EB] font-serif-editorial text-lg font-normal">01</span>
            Smart Wardrobe
          </div>
          <div>
            <span className="block text-[#F5F2EB] font-serif-editorial text-lg font-normal">02</span>
            CLIP AI Matching
          </div>
          <div>
            <span className="block text-[#F5F2EB] font-serif-editorial text-lg font-normal">03</span>
            Tailored Scoring
          </div>
        </div>
      </div>
    </aside>
  )
}
