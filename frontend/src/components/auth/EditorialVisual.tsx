export function EditorialVisual() {
  return (
    <aside className="relative hidden lg:flex flex-col justify-between w-full h-full min-h-screen overflow-hidden bg-[#0A0A09] p-12 lg:p-16 border-r border-white/10 select-none">
      {/* A drawn clothes rail rather than a photo of a real person. */}
      <div className="absolute inset-0 z-0 overflow-hidden">
        <ClothesRail />
        <div className="absolute inset-0 bg-gradient-to-t from-[#0A0A09] via-[#0A0A09]/30 to-transparent" />
        <div className="absolute inset-0 bg-gradient-to-r from-transparent via-transparent to-[#0A0A09]/60" />
      </div>

      {/* Bottom Editorial Copy */}
      <div className="relative z-10 max-w-lg space-y-4 mt-auto">
        <h2 className="font-serif-editorial text-4xl xl:text-5xl font-light text-[#F5F2EB] leading-tight tracking-wide">
          Curate your wardrobe with precision.
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

/** Garments on hangers: a kurta, a shirt, a dress, a jacket and trousers. */
export function ClothesRail() {
  const hanger = (x: number) => (
    <path
      d={`M${x} 150 q0 -14 10 -14 q10 0 10 10 M${x + 10} 156 L${x - 40} 182 L${x + 60} 182 Z`}
      fill="none"
      stroke="#8f8574"
      strokeWidth="3"
      strokeLinejoin="round"
    />
  )
  return (
    <svg
      viewBox="0 0 600 900"
      preserveAspectRatio="xMidYMid slice"
      className="h-full w-full opacity-90"
      role="img"
      aria-label="Illustration of clothes hanging on a rail"
    >
      <defs>
        <linearGradient id="rail-bg" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#2b2620" />
          <stop offset="1" stopColor="#0a0a09" />
        </linearGradient>
      </defs>
      <rect width="600" height="900" fill="url(#rail-bg)" />
      <rect x="20" y="128" width="560" height="6" rx="3" fill="#a89c86" />

      {/* Kurta */}
      {hanger(60)}
      <path d="M30 182 L100 182 L118 230 L104 236 L100 214 L106 520 L24 520 L30 214 L26 236 L12 230 Z" fill="#b5532f" />
      <path d="M65 182 L65 250" stroke="#e2b04a" strokeWidth="4" />

      {/* Shirt */}
      {hanger(170)}
      <path d="M138 182 L212 182 L236 250 L218 258 L210 226 L212 400 L138 400 L140 226 L132 258 L114 250 Z" fill="#e9e2d3" />
      <path d="M175 182 L175 400" stroke="#c9bfab" strokeWidth="2" />

      {/* Dress */}
      {hanger(290)}
      <path d="M262 182 L318 182 L322 280 L372 600 L208 600 L258 280 Z" fill="#6d1f2a" />
      <path d="M258 280 L322 280" stroke="#4d141d" strokeWidth="6" />

      {/* Jacket */}
      {hanger(410)}
      <path d="M372 182 L448 182 L474 250 L470 460 L446 460 L446 260 L446 470 L374 470 L374 260 L374 460 L350 460 L346 250 Z" fill="#1f2f57" />
      <path d="M410 182 L392 290 M410 182 L428 290" stroke="#2f4374" strokeWidth="5" />

      {/* Trousers */}
      {hanger(525)}
      <path d="M492 182 L558 182 L566 560 L534 560 L525 260 L516 560 L484 560 Z" fill="#c9b48f" />
    </svg>
  )
}
