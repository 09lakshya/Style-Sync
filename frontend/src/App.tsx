import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Activity,
  AlertCircle,
  BarChart3,
  CalendarDays,
  CheckCircle2,
  CloudUpload,
  Layers3,
  Palette,
  Search,
  Shirt,
  Sparkles,
  TrendingUp,
  WandSparkles,
} from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import type { FormEvent, ReactNode } from 'react'
import { LoginPage } from './features/auth/LoginPage'
import { SignupPage } from './features/auth/SignupPage'
import type { AuthSession, AuthUser } from './features/auth/authTypes'
import { getAuthHeader, readStoredSession, removeStoredSession, saveStoredSession } from './lib/auth'
import { cn } from './lib/utils'

type ApiWardrobeItem = {
  id: string
  name: string
  image_url: string
  thumbnail_url?: string
  medium_url?: string
  public_id?: string
  format?: string
  width?: number
  height?: number
  bytes?: number
  type: string
  category: string
  primary_color: string
  pattern: string
  fabric: string
  season: string[]
  occasion: string[]
  wear_count: number
  last_worn_at: string | null
}

type WardrobeItem = {
  id: string
  name: string
  imageUrl: string
  thumbnailUrl?: string
  type: string
  category: string
  primaryColor: string
  pattern: string
  fabric: string
  season: string[]
  occasion: string[]
  wearCount: number
  lastWorn: string
}

type SimilarItem = {
  id: string
  name: string
  imageUrl: string
  similarity: number
  reason: string
}

type Recommendation = {
  items: { id: string; name: string }[]
  score: number
  reasons: string[]
}

type Analytics = {
  total_items: number
  most_common_color: string | null
  category_distribution: Record<string, number>
  least_used_items: number
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000/api/v1'

const colorHints: Record<string, string> = {
  blue: 'Pair with white, charcoal, silver, soft yellow, or denim neutrals.',
  white: 'Works with almost everything; use texture or contrast to avoid a flat outfit.',
  black: 'Strong anchor color; balance it with cream, metallics, or one saturated accent.',
  green: 'Looks sharp with white, denim blue, tan, or muted pink.',
}

function App() {
  const queryClient = useQueryClient()
  const [session, setSession] = useState<AuthSession | null>(() => readStoredSession())
  const [currentPath, setCurrentPath] = useState<string>(() => window.location.pathname)

  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [shoppingFile, setShoppingFile] = useState<File | null>(null)
  const [newItemName, setNewItemName] = useState('')
  const [activeType, setActiveType] = useState('all')
  const [similarItems, setSimilarItems] = useState<SimilarItem[]>([])
  const [duplicateChecks, setDuplicateChecks] = useState(0)
  const [notice, setNotice] = useState('Connected to the StyleSync FastAPI backend.')

  // Listen for browser navigation popstate
  useEffect(() => {
    const handlePopState = () => setCurrentPath(window.location.pathname)
    window.addEventListener('popstate', handlePopState)
    return () => window.removeEventListener('popstate', handlePopState)
  }, [])

  function navigate(path: string) {
    if (window.location.pathname !== path) {
      window.history.pushState({}, '', path)
    }
    setCurrentPath(path)
  }

  const wardrobeQuery = useQuery({
    queryKey: ['wardrobe-items', session?.token],
    queryFn: () => fetchWardrobeItems(session?.token ?? ''),
    enabled: Boolean(session?.token),
  })

  const analyticsQuery = useQuery({
    queryKey: ['wardrobe-analytics', session?.token],
    queryFn: () => fetchAnalytics(session?.token ?? ''),
    enabled: Boolean(session?.token),
  })

  const recommendationsQuery = useQuery({
    queryKey: ['outfit-recommendations', session?.token],
    queryFn: () => fetchRecommendations(session?.token ?? ''),
    enabled: Boolean(session?.token),
  })

  const addItemMutation = useMutation({
    mutationFn: (payload: { file: File; name: string }) => uploadWardrobeItem(payload, session?.token ?? ''),
    onSuccess: (item) => {
      setNewItemName('')
      setSelectedFile(null)
      setNotice(`Added "${item.name}" with backend-generated metadata.`)
      queryClient.setQueryData<WardrobeItem[]>(['wardrobe-items', session?.token], (current = []) => [item, ...current])
      void queryClient.invalidateQueries({ queryKey: ['wardrobe-analytics', session?.token] })
      void queryClient.invalidateQueries({ queryKey: ['outfit-recommendations', session?.token] })
    },
    onError: (error) => setNotice(error instanceof Error ? error.message : 'Upload failed.'),
  })

  const duplicateMutation = useMutation({
    mutationFn: (file: File) => checkShoppingImage(file, session?.token ?? ''),
    onSuccess: (result) => {
      setSimilarItems(result.similarItems)
      setDuplicateChecks((count) => count + 1)
      setNotice(
        result.highestSimilarity >= 0.85
          ? 'Strong duplicate risk found. Review your wardrobe before buying.'
          : 'No exact duplicate found, but these are the closest wardrobe matches.',
      )
    },
    onError: (error) => setNotice(error instanceof Error ? error.message : 'Duplicate check failed.'),
  })

  const items = wardrobeQuery.data ?? []
  const analytics = analyticsQuery.data
  const recommendations = recommendationsQuery.data ?? []

  const filteredItems = useMemo(() => {
    if (activeType === 'all') return items
    return items.filter((item) => item.type === activeType)
  }, [activeType, items])

  const topColor = analytics?.most_common_color ?? 'n/a'
  const underused = analytics?.least_used_items ?? items.filter((item) => item.wearCount <= 2).length

  function handleAddItem(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!selectedFile) {
      setNotice('Choose a clothing photo before adding an item.')
      return
    }

    addItemMutation.mutate({ file: selectedFile, name: newItemName })
  }

  function handleDuplicateCheck(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!shoppingFile) {
      setNotice('Upload a shopping image to run the duplicate check.')
      return
    }

    duplicateMutation.mutate(shoppingFile)
  }

  function handleSessionChange(nextSession: AuthSession) {
    saveStoredSession(nextSession)
    setSession(nextSession)
    setNotice(`Signed in as ${nextSession.user.name}.`)
    navigate('/dashboard')
  }

  function handleSignOut() {
    removeStoredSession()
    setSession(null)
    setSimilarItems([])
    queryClient.clear()
    navigate('/login')
  }

  // Routing Guard logic
  if (!session) {
    if (currentPath === '/signup') {
      return <SignupPage onSessionSuccess={handleSessionChange} onNavigateToLogin={() => navigate('/login')} />
    }
    return <LoginPage onSessionSuccess={handleSessionChange} onNavigateToSignup={() => navigate('/signup')} />
  }

  // Authenticated user trying to access /login or /signup
  if (currentPath === '/login' || currentPath === '/signup') {
    // Smoothly ensure URL displays /dashboard
    window.history.replaceState({}, '', '/dashboard')
  }

  return (
    <main className="min-h-screen bg-[#f7f4ef] text-[#1f2328]">
      <div className="mx-auto flex w-full max-w-[1440px] flex-col gap-6 px-4 py-4 sm:px-6 lg:px-8">
        <TopBar user={session.user} onSignOut={handleSignOut} />

        <section className="grid gap-4 lg:grid-cols-[1.05fr_0.95fr]">
          <div className="overflow-hidden rounded-lg border border-[#ded8ce] bg-[#fbfaf7]">
            <div className="grid min-h-[380px] lg:grid-cols-[0.95fr_1.05fr]">
              <div className="flex flex-col justify-between p-6 sm:p-8">
                <div>
                  <div className="mb-5 inline-flex items-center gap-2 rounded-full border border-[#dad0c1] bg-white px-3 py-1 text-sm text-[#5c625d]">
                    <Sparkles className="h-4 w-4 text-[#a15c38]" />
                    Smart wardrobe intelligence
                  </div>
                  <h1 className="max-w-xl text-4xl font-semibold leading-tight text-[#20231f] sm:text-5xl">
                    StyleSync
                  </h1>
                  <p className="mt-4 max-w-xl text-base leading-7 text-[#626760]">
                    Upload clothing photos, detect similar purchases, and turn unused wardrobe pieces
                    into outfit recommendations with explainable AI scoring.
                  </p>
                </div>
                <div className="mt-8 grid grid-cols-3 gap-3">
                  <Metric label="Items" value={(analytics?.total_items ?? items.length).toString()} />
                  <Metric label="Underused" value={underused.toString()} />
                  <Metric label="Top color" value={topColor} />
                </div>
              </div>
              <div className="relative min-h-[320px] bg-[#d8d0c3]">
                <img
                  className="h-full w-full object-cover"
                  src="/virat.jpg"
                  alt="StyleSync Showcase"
                />
              </div>
            </div>
          </div>

          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-1">
            <WorkflowCard
              icon={CloudUpload}
              title="Add wardrobe item"
              description="Create metadata for a new clothing photo."
            >
              <form className="space-y-3" onSubmit={handleAddItem}>
                <input
                  className="w-full rounded-md border border-[#d9d3c8] bg-white px-3 py-2 text-sm text-[#1f2328]"
                  placeholder="Item name"
                  value={newItemName}
                  onChange={(event) => setNewItemName(event.target.value)}
                />
                <FileInput file={selectedFile} onChange={setSelectedFile} label="Choose clothing photo" />
                <button
                  className="inline-flex w-full items-center justify-center gap-2 rounded-md bg-[#1f2328] px-4 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-60"
                  disabled={addItemMutation.isPending}
                >
                  <CloudUpload className="h-4 w-4" />
                  {addItemMutation.isPending ? 'Adding...' : 'Add to wardrobe'}
                </button>
              </form>
            </WorkflowCard>

            <WorkflowCard
              icon={Search}
              title="Duplicate purchase check"
              description="Compare a shopping image against your wardrobe."
            >
              <form className="space-y-3" onSubmit={handleDuplicateCheck}>
                <FileInput file={shoppingFile} onChange={setShoppingFile} label="Choose shopping image" />
                <button
                  className="inline-flex w-full items-center justify-center gap-2 rounded-md bg-[#a15c38] px-4 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-60"
                  disabled={duplicateMutation.isPending}
                >
                  <Search className="h-4 w-4" />
                  {duplicateMutation.isPending ? 'Checking...' : 'Check similarity'}
                </button>
              </form>
            </WorkflowCard>
          </div>
        </section>

        <div className="rounded-md border border-[#ded8ce] bg-white px-4 py-3 text-sm text-[#5e645e]">
          {wardrobeQuery.isError ? 'Backend connection failed or token expired. Try signing out and back in.' : notice}
        </div>

        <section className="grid gap-4 lg:grid-cols-[0.72fr_0.28fr]">
          <div className="rounded-lg border border-[#ded8ce] bg-[#fbfaf7] p-4 sm:p-5">
            <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <h2 className="text-xl font-semibold">Digital wardrobe</h2>
                <p className="text-sm text-[#687068]">
                  {wardrobeQuery.isLoading
                    ? 'Loading backend wardrobe...'
                    : 'AI-predicted attributes remain editable by the user.'}
                </p>
              </div>
              <div className="flex flex-wrap gap-2">
                {['all', 'dress', 'top', 'bottom', 'outerwear'].map((type) => (
                  <button
                    key={type}
                    className={cn(
                      'rounded-md border px-3 py-1.5 text-sm capitalize',
                      activeType === type
                        ? 'border-[#1f2328] bg-[#1f2328] text-white'
                        : 'border-[#d9d3c8] bg-white text-[#555c56]',
                    )}
                    onClick={() => setActiveType(type)}
                  >
                    {type}
                  </button>
                ))}
              </div>
            </div>
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
              {filteredItems.map((item) => (
                <WardrobeCard key={item.id} item={item} />
              ))}
            </div>
          </div>

          <aside className="space-y-4">
            <Panel title="Recommendations" icon={WandSparkles}>
              {recommendations.slice(0, 3).map((recommendation) => (
                <RecommendationCard key={recommendation.items.map((item) => item.id).join('-')} recommendation={recommendation} />
              ))}
            </Panel>

            <Panel title="Analytics" icon={BarChart3}>
              <StatLine label="Duplicate risk checks" value={`${duplicateChecks} today`} />
              <StatLine label="Most common color" value={topColor} />
              <StatLine label="Long-unused pieces" value={underused.toString()} />
            </Panel>

            <Panel title="Color guidance" icon={Palette}>
              <p className="text-sm leading-6 text-[#646b64]">
                {colorHints[topColor] ?? 'Use one anchor color, one neutral, and one accent.'}
              </p>
            </Panel>
          </aside>
        </section>

        {similarItems.length > 0 && (
          <section className="rounded-lg border border-[#ded8ce] bg-[#fbfaf7] p-4 sm:p-5">
            <div className="mb-4 flex items-center gap-2">
              {similarItems[0].similarity >= 0.85 ? (
                <AlertCircle className="h-5 w-5 text-[#a15c38]" />
              ) : (
                <CheckCircle2 className="h-5 w-5 text-[#557660]" />
              )}
              <h2 className="text-xl font-semibold">Similarity report</h2>
            </div>
            <div className="grid gap-4 md:grid-cols-3">
              {similarItems.map((item) => (
                <div key={item.id} className="rounded-lg border border-[#e2dcd1] bg-white p-3">
                  <img className="h-40 w-full rounded-md object-cover" src={item.imageUrl} alt={item.name} />
                  <div className="mt-3 flex items-start justify-between gap-3">
                    <div>
                      <p className="font-medium">{item.name}</p>
                      <p className="mt-1 text-sm text-[#687068]">{item.reason}</p>
                    </div>
                    <span className="rounded-full bg-[#f0e8dd] px-2 py-1 text-sm font-semibold text-[#7f4b2f]">
                      {Math.round(item.similarity * 100)}%
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}
      </div>
    </main>
  )
}

async function fetchWardrobeItems(token: string) {
  const response = await fetch(`${API_BASE_URL}/wardrobe/items`, {
    headers: getAuthHeader(token),
  })
  const payload = await parseResponse<{ items: ApiWardrobeItem[] }>(response)
  return payload.items.map(toWardrobeItem)
}

async function fetchAnalytics(token: string) {
  const response = await fetch(`${API_BASE_URL}/analytics/wardrobe`, {
    headers: getAuthHeader(token),
  })
  return parseResponse<Analytics>(response)
}

async function fetchRecommendations(token: string) {
  const response = await fetch(`${API_BASE_URL}/recommendations/outfits`, {
    headers: getAuthHeader(token),
  })
  const payload = await parseResponse<{ recommendations: Recommendation[] }>(response)
  return payload.recommendations
}

async function uploadWardrobeItem({ file, name }: { file: File; name: string }, token: string) {
  const formData = new FormData()
  formData.append('image', file)
  if (name.trim()) formData.append('name', name.trim())

  const response = await fetch(`${API_BASE_URL}/wardrobe/items`, {
    method: 'POST',
    headers: getAuthHeader(token),
    body: formData,
  })
  const payload = await parseResponse<{ item: ApiWardrobeItem }>(response)
  return toWardrobeItem(payload.item)
}

async function checkShoppingImage(file: File, token: string) {
  const formData = new FormData()
  formData.append('image', file)

  const response = await fetch(`${API_BASE_URL}/shopping/check`, {
    method: 'POST',
    headers: getAuthHeader(token),
    body: formData,
  })
  const payload = await parseResponse<{
    highest_similarity: number
    similar_items: Array<{ id: string; name: string; image_url: string; similarity: number; reason: string }>
  }>(response)

  return {
    highestSimilarity: payload.highest_similarity,
    similarItems: payload.similar_items.map((item) => ({
      id: item.id,
      name: item.name,
      imageUrl: item.image_url,
      similarity: item.similarity,
      reason: item.reason,
    })),
  }
}

async function parseResponse<T>(response: Response): Promise<T> {
  const payload = await response.json().catch(() => null)
  if (!response.ok) {
    throw new Error(payload?.detail ?? `Request failed with status ${response.status}`)
  }
  return payload as T
}

function toWardrobeItem(item: ApiWardrobeItem): WardrobeItem {
  return {
    id: item.id,
    name: item.name,
    imageUrl: item.image_url || 'https://images.unsplash.com/photo-1483985988355-763728e1935b?auto=format&fit=crop&w=800&q=80',
    thumbnailUrl: item.thumbnail_url || item.image_url || 'https://images.unsplash.com/photo-1483985988355-763728e1935b?auto=format&fit=crop&w=800&q=80',
    type: item.type,
    category: item.category.replace(/_/g, ' '),
    primaryColor: item.primary_color,
    pattern: item.pattern,
    fabric: item.fabric.replace(/_/g, ' '),
    season: item.season.map((value) => value.replace(/_/g, ' ')),
    occasion: item.occasion.map((value) => value.replace(/_/g, ' ')),
    wearCount: item.wear_count,
    lastWorn: item.last_worn_at ?? 'not worn yet',
  }
}

function TopBar({ user, onSignOut }: { user: AuthUser; onSignOut: () => void }) {
  return (
    <header className="flex flex-col gap-3 rounded-lg border border-[#ded8ce] bg-white px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
      <div className="flex items-center gap-3">
        <div className="grid h-10 w-10 place-items-center rounded-md bg-[#1f2328] text-white">
          <Shirt className="h-5 w-5" />
        </div>
        <div>
          <p className="font-semibold">StyleSync</p>
          <p className="text-sm text-[#697169]">Smart dress wardrobe system</p>
        </div>
      </div>
      <nav className="flex flex-wrap gap-2 text-sm text-[#4f574f]">
        <NavPill icon={Layers3} label="Wardrobe" />
        <NavPill icon={Sparkles} label="AI Engine" />
        <NavPill icon={TrendingUp} label="Trends" />
        <NavPill icon={CalendarDays} label="Reminders" />
        <button
          className="rounded-md border border-[#e1dbd0] bg-[#fbfaf7] hover:bg-[#f0e8dd] transition-colors px-3 py-2 cursor-pointer font-medium"
          onClick={onSignOut}
        >
          {user.name} / Sign out
        </button>
      </nav>
    </header>
  )
}

function NavPill({ icon: Icon, label }: { icon: typeof Shirt; label: string }) {
  return (
    <span className="inline-flex items-center gap-2 rounded-md border border-[#e1dbd0] bg-[#fbfaf7] px-3 py-2">
      <Icon className="h-4 w-4" />
      {label}
    </span>
  )
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-[#ded8ce] bg-white p-3 text-left">
      <p className="text-sm text-[#697169]">{label}</p>
      <p className="mt-1 text-xl font-semibold capitalize">{value}</p>
    </div>
  )
}

function WorkflowCard({
  icon: Icon,
  title,
  description,
  children,
}: {
  icon: typeof Shirt
  title: string
  description: string
  children: ReactNode
}) {
  return (
    <section className="rounded-lg border border-[#ded8ce] bg-white p-5">
      <div className="mb-4 flex items-start gap-3">
        <div className="grid h-10 w-10 shrink-0 place-items-center rounded-md bg-[#f0e8dd] text-[#895035]">
          <Icon className="h-5 w-5" />
        </div>
        <div>
          <h2 className="text-lg font-semibold">{title}</h2>
          <p className="text-sm text-[#687068]">{description}</p>
        </div>
      </div>
      {children}
    </section>
  )
}

function FileInput({
  file,
  label,
  onChange,
}: {
  file: File | null
  label: string
  onChange: (file: File | null) => void
}) {
  return (
    <label className="flex min-h-24 cursor-pointer flex-col items-center justify-center rounded-md border border-dashed border-[#cfc7bb] bg-[#fbfaf7] px-3 py-4 text-center text-sm text-[#5d655e]">
      <CloudUpload className="mb-2 h-5 w-5" />
      <span className="font-medium">{file ? file.name : label}</span>
      <span className="mt-1 text-xs text-[#7d847d]">JPG, PNG, or WebP up to 5 MB</span>
      <input
        className="sr-only"
        type="file"
        accept="image/png,image/jpeg,image/webp"
        onChange={(event) => onChange(event.target.files?.[0] ?? null)}
      />
    </label>
  )
}

function WardrobeCard({ item }: { item: WardrobeItem }) {
  return (
    <article className="overflow-hidden rounded-lg border border-[#e2dcd1] bg-white">
      <img className="h-48 w-full object-cover" src={item.thumbnailUrl || item.imageUrl} alt={item.name} loading="lazy" />
      <div className="space-y-3 p-3">
        <div>
          <h3 className="font-semibold">{item.name}</h3>
          <p className="text-sm capitalize text-[#687068]">
            {item.type} / {item.fabric}
          </p>
        </div>
        <div className="flex flex-wrap gap-1.5">
          {[item.primaryColor, item.pattern, ...item.occasion.slice(0, 1), ...item.season.slice(0, 1)].map((tag) => (
            <span key={tag} className="rounded-full bg-[#f0ede7] px-2 py-1 text-xs capitalize text-[#555c56]">
              {tag}
            </span>
          ))}
        </div>
        <div className="flex items-center justify-between text-sm text-[#687068]">
          <span className="inline-flex items-center gap-1">
            <Activity className="h-4 w-4" />
            {item.wearCount} wears
          </span>
          <span>{item.lastWorn}</span>
        </div>
      </div>
    </article>
  )
}

function Panel({ title, icon: Icon, children }: { title: string; icon: typeof Shirt; children: ReactNode }) {
  return (
    <section className="rounded-lg border border-[#ded8ce] bg-white p-4">
      <div className="mb-3 flex items-center gap-2">
        <Icon className="h-5 w-5 text-[#895035]" />
        <h2 className="font-semibold">{title}</h2>
      </div>
      <div className="space-y-3">{children}</div>
    </section>
  )
}

function RecommendationCard({ recommendation }: { recommendation: Recommendation }) {
  const title = recommendation.items.map((item) => item.name).join(' + ')
  return (
    <div className="rounded-md border border-[#e3ddd2] bg-[#fbfaf7] p-3">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="font-medium">{title}</p>
          <p className="mt-1 text-sm leading-5 text-[#687068]">{recommendation.reasons.join(' / ')}</p>
        </div>
        <span className="rounded-full bg-white px-2 py-1 text-xs font-semibold text-[#557660]">
          {Math.round(recommendation.score * 100)}%
        </span>
      </div>
    </div>
  )
}

function StatLine({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-3 text-sm">
      <span className="text-[#687068]">{label}</span>
      <span className="font-medium capitalize">{value}</span>
    </div>
  )
}

export default App
