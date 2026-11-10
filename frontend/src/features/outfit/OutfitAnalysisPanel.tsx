import { useEffect, useState } from 'react'
import {
  CheckCircle2,
  CloudUpload,
  Layers,
  Lightbulb,
  Loader2,
  Palette,
  Sparkles,
} from 'lucide-react'
import { analyzeOutfit } from '../../api/outfitApi'
import type { OutfitAnalysis, OutfitGender } from '../../types/outfit'
import { STYLING_SLOTS } from '../../types/outfit'

interface OutfitAnalysisPanelProps {
  token: string
}

const GENDER_LABELS: Record<OutfitGender, string> = {
  female: 'Female',
  male: 'Male',
  unisex: 'Unisex',
}

export function OutfitAnalysisPanel({ token }: OutfitAnalysisPanelProps) {
  const [file, setFile] = useState<File | null>(null)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [result, setResult] = useState<OutfitAnalysis | null>(null)
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!file) {
      setPreviewUrl(null)
      return
    }
    const url = URL.createObjectURL(file)
    setPreviewUrl(url)
    return () => URL.revokeObjectURL(url)
  }, [file])

  async function handleAnalyze() {
    if (!file || isAnalyzing) return
    setIsAnalyzing(true)
    setError(null)
    try {
      setResult(await analyzeOutfit(file, token))
    } catch (err) {
      setResult(null)
      setError(
        err instanceof Error ? err.message : 'Unable to analyze this outfit. Please try again.'
      )
    } finally {
      setIsAnalyzing(false)
    }
  }

  const gender = result?.gender
  const isGemini = result?.engine === 'gemini_multimodal_vision'

  return (
    <section
      id="outfit-analysis"
      className="scroll-mt-4 rounded-xl border border-[var(--border)] bg-[var(--surface-raised)] p-5 shadow-sm"
    >
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-lg font-semibold text-[#1f2328]">AI Outfit Analysis</h2>
            {isGemini && (
              <span className="inline-flex items-center gap-1 rounded-full bg-amber-50 px-2.5 py-0.5 text-[11px] font-medium text-amber-800 border border-amber-200">
                <Sparkles className="h-3 w-3 text-amber-600" />
                Gemini Vision AI
              </span>
            )}
          </div>
          <p className="text-xs text-[#687068]">
            Upload an outfit to analyze individual garments, color harmony, silhouette, and get personalized stylist advice.
          </p>
        </div>
      </div>

      <div className="grid gap-5 md:grid-cols-[minmax(0,280px)_1fr]">
        {/* Controls */}
        <div className="space-y-3">
          <label className="flex min-h-28 cursor-pointer flex-col items-center justify-center rounded-lg border border-dashed border-[var(--border)] bg-[var(--surface)] px-3 py-4 text-center text-sm text-[#5d655e] transition-colors hover:border-[var(--accent)] hover:bg-[#faf7f2]">
            <CloudUpload className="mb-2 h-6 w-6 text-[var(--accent)]" />
            <span className="font-medium">{file ? file.name : 'Choose outfit image'}</span>
            <span className="mt-1 text-xs text-[#7d847d]">JPG, PNG, or WebP</span>
            <input
              id="outfit-file"
              className="sr-only"
              type="file"
              accept="image/png,image/jpeg,image/webp"
              onChange={(event) => {
                setFile(event.target.files?.[0] ?? null)
                setResult(null)
                setError(null)
              }}
            />
          </label>

          {previewUrl && (
            <div className="overflow-hidden rounded-lg border border-[var(--border-soft)] bg-black/5">
              <img
                src={previewUrl}
                alt="Outfit awaiting analysis"
                className="max-h-72 w-full object-contain"
              />
            </div>
          )}

          <button
            type="button"
            onClick={handleAnalyze}
            disabled={!file || isAnalyzing}
            className="inline-flex w-full items-center justify-center gap-2 rounded-md bg-[var(--accent)] px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-[var(--accent-hover)] disabled:cursor-not-allowed disabled:opacity-60 shadow-sm"
          >
            {isAnalyzing && <Loader2 className="h-4 w-4 animate-spin" />}
            {isAnalyzing ? 'Analyzing outfit...' : 'Analyze Outfit with AI'}
          </button>
        </div>

        {/* Results */}
        <div className="min-w-0">
          {error && (
            <div className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">
              {error}
            </div>
          )}

          {!error && !result && (
            <div className="flex h-full min-h-[180px] flex-col items-center justify-center rounded-lg border border-dashed border-[var(--border-soft)] bg-[var(--surface)] px-4 py-8 text-center text-sm text-[#7d847d]">
              <Sparkles className="mb-2 h-6 w-6 text-[#9a918a] opacity-60" />
              {isAnalyzing
                ? 'Deconstructing outfit pieces and consulting the AI stylist...'
                : 'Upload an outfit photo to view score, piece breakdown, color palette, and stylist advice.'}
            </div>
          )}

          {result && (
            <div className="space-y-4">
              {/* Top Aesthetic Header & Score */}
              <div className="rounded-lg border border-[var(--border-soft)] bg-[var(--surface)] p-4 shadow-xs">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="space-y-1">
                    <p className="text-[11px] font-semibold uppercase tracking-wider text-[#895035]">
                      Overall Aesthetic
                    </p>
                    <h3 className="text-xl font-bold capitalize text-[#1f2328]">
                      {result.aesthetic ||
                        result.styling.style ||
                        (result.classification.labels.length
                          ? result.classification.labels.join(' · ')
                          : result.classification.predicted_category || 'Outfit')}
                    </h3>
                    {result.summary && (
                      <p className="text-xs text-[#525a52] leading-relaxed max-w-xl">
                        {result.summary}
                      </p>
                    )}
                  </div>

                  {typeof result.outfit_score === 'number' && (
                    <div className="flex flex-col items-center justify-center rounded-xl bg-[#f4ece1] border border-[#e5d8c6] px-4 py-2 text-center min-w-[90px]">
                      <span className="text-[10px] font-bold uppercase tracking-wider text-[#7a4830]">
                        Outfit Score
                      </span>
                      <span className="text-2xl font-extrabold text-[#895035]">
                        {result.outfit_score}
                        <span className="text-xs font-normal text-[#895035]/70">/100</span>
                      </span>
                    </div>
                  )}
                </div>

                {/* Tags */}
                {result.tags && result.tags.length > 0 && (
                  <div className="mt-3 flex flex-wrap gap-1.5 pt-2 border-t border-[var(--border-soft)]">
                    {result.tags.map((tag) => (
                      <span
                        key={tag}
                        className="rounded-md bg-[#eee7de] px-2 py-0.5 text-[11px] font-medium text-[#4f574f]"
                      >
                        {tag}
                      </span>
                    ))}
                  </div>
                )}
              </div>

              {/* Detected Pieces / Ensemble Deconstruction */}
              {result.detected_pieces && result.detected_pieces.length > 0 && (
                <div className="rounded-lg border border-[var(--border-soft)] bg-[var(--surface)] p-4">
                  <div className="mb-3 flex items-center gap-1.5">
                    <Layers className="h-4 w-4 text-[var(--accent)]" />
                    <h4 className="text-xs font-semibold uppercase tracking-wider text-[#4f574f]">
                      Detected Ensemble Pieces
                    </h4>
                  </div>
                  <div className="grid gap-2 sm:grid-cols-2">
                    {result.detected_pieces.map((piece, idx) => (
                      <div
                        key={idx}
                        className="rounded-md border border-[var(--border-soft)] bg-[var(--surface-raised)] p-2.5 text-xs"
                      >
                        <div className="flex items-center justify-between gap-1 mb-1">
                          <span className="font-semibold text-[#1f2328]">{piece.name}</span>
                          <span className="rounded bg-[#e8e2d8] px-1.5 py-0.5 text-[10px] font-bold uppercase text-[#5a625a]">
                            {piece.slot}
                          </span>
                        </div>
                        <div className="text-[11px] text-[#687068] space-y-0.5">
                          {piece.color && <p>Color: <span className="font-medium text-[#333] capitalize">{piece.color}</span></p>}
                          {piece.details && <p className="italic">{piece.details}</p>}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Legacy or Local Attributes fallback if no detected_pieces */}
              {(!result.detected_pieces || result.detected_pieces.length === 0) && (
                <div className="rounded-lg border border-[var(--border-soft)] bg-[var(--surface)] p-4">
                  <p className="text-[11px] font-semibold uppercase tracking-wide text-[#895035]">
                    Detected Attributes
                  </p>
                  {result.attributes.available ? (
                    <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-2 text-xs sm:grid-cols-3">
                      <Attribute label="Type" value={result.attributes.type} />
                      <Attribute label="Primary color" value={result.attributes.primary_color} />
                      <Attribute label="Pattern" value={result.attributes.pattern} />
                      <Attribute label="Sleeves" value={result.attributes.sleeve_type} />
                      <Attribute label="Season" value={result.attributes.season.join(', ')} />
                      <Attribute label="Occasion" value={result.attributes.occasion.join(', ')} />
                      <Attribute
                        label="Gender"
                        value={
                          gender && gender.source !== 'unavailable'
                            ? (GENDER_LABELS[gender.value] ?? gender.value)
                            : null
                        }
                      />
                    </dl>
                  ) : (
                    <p className="mt-3 text-sm text-[#687068]">
                      {result.attributes.reason ?? 'Attributes unavailable.'}
                    </p>
                  )}
                </div>
              )}

              {/* Color Palette & Harmony */}
              {result.color_palette && (
                <div className="rounded-lg border border-[var(--border-soft)] bg-[var(--surface)] p-4">
                  <div className="mb-2.5 flex items-center gap-1.5">
                    <Palette className="h-4 w-4 text-[var(--accent)]" />
                    <h4 className="text-xs font-semibold uppercase tracking-wider text-[#4f574f]">
                      Color Palette & Harmony
                    </h4>
                  </div>

                  {result.color_palette.color_chips && result.color_palette.color_chips.length > 0 && (
                    <div className="flex flex-wrap gap-2 mb-3">
                      {result.color_palette.color_chips.map((chip, idx) => (
                        <div
                          key={idx}
                          className="flex items-center gap-2 rounded-md border border-[var(--border-soft)] bg-[var(--surface-raised)] px-2.5 py-1 text-xs"
                        >
                          <span
                            className="h-3.5 w-3.5 rounded-full border border-black/20 shadow-xs"
                            style={{ backgroundColor: chip.hex }}
                          />
                          <span className="font-medium text-[#2d332d]">{chip.name}</span>
                          <span className="text-[10px] text-[#8a918a] font-mono">{chip.hex}</span>
                        </div>
                      ))}
                    </div>
                  )}

                  {result.color_palette.harmony_type && (
                    <div className="text-xs text-[#525a52]">
                      <span className="font-semibold text-[#1f2328]">
                        {result.color_palette.harmony_type}
                      </span>
                      {result.color_palette.harmony_evaluation && (
                        <span> — {result.color_palette.harmony_evaluation}</span>
                      )}
                    </div>
                  )}
                </div>
              )}

              {/* Stylist Critique (Strengths & Elevation Tips) */}
              {result.stylist_critique && (
                <div className="grid gap-3 sm:grid-cols-2">
                  {result.stylist_critique.strengths && result.stylist_critique.strengths.length > 0 && (
                    <div className="rounded-lg border border-emerald-200/80 bg-emerald-50/50 p-3.5">
                      <div className="mb-2 flex items-center gap-1.5 text-emerald-800">
                        <CheckCircle2 className="h-4 w-4" />
                        <h4 className="text-xs font-semibold uppercase tracking-wider">
                          Why This Look Works
                        </h4>
                      </div>
                      <ul className="space-y-1.5 text-xs text-emerald-950">
                        {result.stylist_critique.strengths.map((point, idx) => (
                          <li key={idx} className="flex items-start gap-1.5">
                            <span className="text-emerald-600">•</span>
                            <span>{point}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {result.stylist_critique.elevation_tips && result.stylist_critique.elevation_tips.length > 0 && (
                    <div className="rounded-lg border border-amber-200/80 bg-amber-50/50 p-3.5">
                      <div className="mb-2 flex items-center gap-1.5 text-amber-800">
                        <Lightbulb className="h-4 w-4" />
                        <h4 className="text-xs font-semibold uppercase tracking-wider">
                          How to Elevate This Outfit
                        </h4>
                      </div>
                      <ul className="space-y-1.5 text-xs text-amber-950">
                        {result.stylist_critique.elevation_tips.map((tip, idx) => (
                          <li key={idx} className="flex items-start gap-1.5">
                            <span className="text-amber-600 font-bold">→</span>
                            <span>{tip}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}

              {/* Curated Styling Recommendations */}
              <div className="rounded-lg border border-[var(--border-soft)] bg-[var(--surface-raised)] p-4">
                <div className="mb-3 flex items-center justify-between">
                  <p className="text-[11px] font-semibold uppercase tracking-wider text-[#5e645e]">
                    Recommended Pairings & Accessories
                  </p>
                  {result.styling.metal_tone && (
                    <span className="text-xs font-medium text-[#7a4830]">
                      Metal tone: <span className="capitalize font-bold">{result.styling.metal_tone}</span>
                    </span>
                  )}
                </div>

                {result.styling.available ? (
                  <div className="grid gap-x-6 gap-y-3 sm:grid-cols-2">
                    {STYLING_SLOTS.filter((slot) => result.styling.slots[slot]?.length).map((slot) => (
                      <div key={slot} className="rounded-md bg-[var(--surface)] p-2.5 border border-[var(--border-soft)]">
                        <p className="text-xs font-semibold capitalize text-[#4f574f] mb-1">
                          {slot === 'other' ? 'Layers & extras' : slot}
                        </p>
                        <ul className="space-y-1">
                          {result.styling.slots[slot].map((option) => (
                            <li key={option} className="text-xs text-[#687068] flex items-start gap-1.5">
                              <span className="text-[var(--accent)]">•</span>
                              <span>{option}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="mt-2 text-sm text-[#687068]">
                    {result.styling.reason ?? 'No styling suggestions available.'}
                  </p>
                )}
              </div>

              {/* Source Note Footer */}
              <p className="text-[11px] leading-4 text-[#8a918a] italic">
                {result.source_note}
              </p>
            </div>
          )}
        </div>
      </div>
    </section>
  )
}

function Attribute({ label, value }: { label: string; value: string | null | undefined }) {
  return (
    <div>
      <dt className="text-[#8a918a]">{label}</dt>
      <dd className="font-medium capitalize text-[#1f2328]">
        {value ? value.replace(/_/g, ' ') : '—'}
      </dd>
    </div>
  )
}
