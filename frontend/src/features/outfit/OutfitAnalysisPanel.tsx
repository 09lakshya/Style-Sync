import { useEffect, useState } from 'react'
import { CloudUpload, Loader2 } from 'lucide-react'
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
      setError(err instanceof Error ? err.message : 'Unable to analyze this outfit. Please try again.')
    } finally {
      setIsAnalyzing(false)
    }
  }

  // Optional-chained: a backend older than gender detection omits the field.
  const gender = result?.gender

  return (
    <section
      id="outfit-analysis"
      className="scroll-mt-4 rounded-xl border border-[#ded8ce] bg-white p-5 shadow-sm"
    >
      <div className="mb-4">
        <div>
          <h2 className="text-lg font-semibold text-[#1f2328]">Outfit analysis</h2>
          <p className="text-xs text-[#687068]">
            Upload an outfit to detect its attributes and get styling suggestions.
          </p>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-[minmax(0,260px)_1fr]">
        {/* Controls */}
        <div className="space-y-3">
          <label className="flex min-h-24 cursor-pointer flex-col items-center justify-center rounded-lg border border-dashed border-[#cfc7bb] bg-[#fbfaf7] px-3 py-4 text-center text-sm text-[#5d655e]">
            <CloudUpload className="mb-2 h-5 w-5 text-[#a15c38]" />
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
            <img
              src={previewUrl}
              alt="Outfit awaiting analysis"
              className="max-h-64 w-full rounded-lg border border-[#e2dcd1] object-contain"
            />
          )}

          <button
            type="button"
            onClick={handleAnalyze}
            disabled={!file || isAnalyzing}
            className="inline-flex w-full items-center justify-center gap-2 rounded-md bg-[#a15c38] px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-[#b56942] disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isAnalyzing && <Loader2 className="h-4 w-4 animate-spin" />}
            {isAnalyzing ? 'Analyzing outfit...' : 'Analyze outfit'}
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
            <div className="flex h-full min-h-[140px] items-center justify-center rounded-lg border border-dashed border-[#e2dcd1] bg-[#fbfaf7] px-4 py-6 text-center text-sm text-[#7d847d]">
              {isAnalyzing ? 'Reading the image...' : 'Results will appear here once you analyze an outfit.'}
            </div>
          )}

          {result && (
            <div className="space-y-4">
              {/* Model output */}
              <div className="rounded-lg border border-[#e2dcd1] bg-[#fbfaf7] p-4">
                <p className="text-[11px] font-semibold uppercase tracking-wide text-[#895035]">
                  Detected by the model
                </p>

                {result.classification.available ? (
                  <p className="mt-2 text-xl font-semibold capitalize text-[#1f2328]">
                    {result.classification.predicted_category}
                  </p>
                ) : (
                  <p className="mt-2 text-sm text-[#687068]">Classification unavailable.</p>
                )}

                <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-2 text-xs sm:grid-cols-3">
                  <Attribute label="Type" value={result.attributes.type} />
                  <Attribute label="Primary color" value={result.attributes.primary_color} />
                  <Attribute label="Pattern" value={result.attributes.pattern} />
                  <Attribute label="Sleeves" value={result.attributes.sleeve_type} />
                  <Attribute label="Season" value={result.attributes.season.join(', ')} />
                  <Attribute label="Occasion" value={result.attributes.occasion.join(', ')} />
                  <Attribute
                    label="Gender"
                    value={gender && (GENDER_LABELS[gender.value] ?? gender.value)}
                  />
                </dl>

                {result.attributes.secondary_colors.length > 0 && (
                  <p className="mt-2 text-xs text-[#687068]">
                    Also detected: {result.attributes.secondary_colors.join(', ')}
                  </p>
                )}
              </div>

              {/* Rule-based styling */}
              <div className="rounded-lg border border-[#e2dcd1] bg-white p-4">
                <p className="text-[11px] font-semibold uppercase tracking-wide text-[#5e645e]">
                  Styling suggestions
                </p>

                {result.styling.available ? (
                  <>
                    {result.styling.style && (
                      <p className="mt-1 text-sm font-medium text-[#1f2328]">{result.styling.style}</p>
                    )}

                    <div className="mt-3 grid gap-x-6 gap-y-3 sm:grid-cols-2">
                      {STYLING_SLOTS.filter((slot) => result.styling.slots[slot]?.length).map((slot) => (
                        <div key={slot}>
                          <p className="text-xs font-semibold capitalize text-[#4f574f]">{slot}</p>
                          <ul className="mt-1 space-y-0.5">
                            {result.styling.slots[slot].map((option) => (
                              <li key={option} className="text-xs text-[#687068]">
                                • {option}
                              </li>
                            ))}
                          </ul>
                        </div>
                      ))}
                    </div>

                    {result.styling.reasoning && (
                      <ul className="mt-3 space-y-0.5 border-t border-[#ece6dc] pt-3">
                        {result.styling.reasoning.map((reason) => (
                          <li key={reason} className="text-[11px] text-[#8a918a]">
                            {reason}
                          </li>
                        ))}
                      </ul>
                    )}
                  </>
                ) : (
                  <p className="mt-2 text-sm text-[#687068]">
                    {result.styling.reason ?? 'No styling suggestions available.'}
                  </p>
                )}
              </div>

              <p className="text-[11px] leading-4 text-[#8a918a]">{result.source_note}</p>
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
