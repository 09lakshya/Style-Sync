import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  AlertCircle,
  BarChart3,
  CalendarDays,
  CheckCircle2,
  CloudUpload,
  Layers3,
  Palette,
  Plus,
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

import {
  createWardrobeItem,
  deleteWardrobeItem,
  fetchWardrobeItems,
  markWardrobeItemWorn,
  replaceWardrobeItemImage,
  updateWardrobeItem,
} from './api/wardrobeApi'
import { AddDressModal } from './features/wardrobe/AddDressModal'
import { DressDetailModal } from './features/wardrobe/DressDetailModal'
import { EditDressModal } from './features/wardrobe/EditDressModal'
import { WardrobeFilterBar } from './features/wardrobe/WardrobeFilterBar'
import { WardrobeGrid } from './features/wardrobe/WardrobeGrid'
import { DuplicateAlertModal } from './features/shopping/DuplicateAlertModal'
import { OutfitAnalysisPanel } from './features/outfit/OutfitAnalysisPanel'
import type { DuplicateCheckResult, DuplicateDecision, SimilarItem } from './types/shopping'
import type {
  CreateDressInput,
  UpdateDressMetadataInput,
  WardrobeFilterState,
  WardrobeItem,
} from './types/wardrobe'

type Analytics = {
  total_items: number
  most_common_color: string
  least_used_items: number
}

type Recommendation = {
  items: { id: string; name: string }[]
  score: number
  reasons: string[]
}

const API_BASE_URL =
  (import.meta.env.VITE_API_URL as string | undefined)?.replace(/\/$/, '') ||
  'http://localhost:8000/api/v1'

const colorHints: Record<string, string> = {
  blue: 'Pair blue items with warm tan, cream, or silver accessories for an effortless visual balance.',
  white: 'White pieces act as ideal anchors—combine them with high-contrast accent pieces.',
  black: 'Black builds sleek structural outfits. Use textured fabrics to add subtle depth.',
  green: 'Earth tones like sage and olive perform best alongside beige, white, or deep brown.',
  red: 'A bold red works best when isolated as the main focal point against neutral tones.',
}

export function App() {
  const [session, setSession] = useState<AuthSession | null>(() => readStoredSession())
  const [currentPath, setCurrentPath] = useState<string>(() => window.location.pathname)

  // Wardrobe Modals & State
  const [isAddModalOpen, setIsAddModalOpen] = useState(false)
  const [selectedDetailItem, setSelectedDetailItem] = useState<WardrobeItem | null>(null)
  const [editingItem, setEditingItem] = useState<WardrobeItem | null>(null)

  // Filters State
  const [filters, setFilters] = useState<WardrobeFilterState>({
    searchQuery: '',
    color: 'All',
    pattern: 'All',
    occasion: 'All',
    sortBy: 'recently_added',
  })

  // Duplicate Check State
  const [shoppingFile, setShoppingFile] = useState<File | null>(null)
  const [shoppingPreviewUrl, setShoppingPreviewUrl] = useState<string | null>(null)
  const [similarItems, setSimilarItems] = useState<SimilarItem[]>([])
  const [duplicateDecision, setDuplicateDecision] = useState<DuplicateDecision | null>(null)
  const [isDuplicateAlertOpen, setIsDuplicateAlertOpen] = useState(false)
  const [duplicateChecks, setDuplicateChecks] = useState<number>(0)
  const [notice, setNotice] = useState<string>(
    'Upload clothing photos or check new shopping finds for duplicates.'
  )
  const queryClient = useQueryClient()

  useEffect(() => {
    function handlePopState() {
      setCurrentPath(window.location.pathname)
    }

    window.addEventListener('popstate', handlePopState)
    return () => window.removeEventListener('popstate', handlePopState)
  }, [])

  // Local preview of the intent-to-buy image, shown beside the wardrobe match.
  useEffect(() => {
    if (!shoppingFile) {
      setShoppingPreviewUrl(null)
      return
    }
    const objectUrl = URL.createObjectURL(shoppingFile)
    setShoppingPreviewUrl(objectUrl)
    return () => URL.revokeObjectURL(objectUrl)
  }, [shoppingFile])

  function navigate(path: string) {
    if (window.location.pathname !== path) {
      window.history.pushState({}, '', path)
    }
    setCurrentPath(path)
  }

  // TanStack Queries
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

  // TanStack Mutations
  const addDressMutation = useMutation({
    mutationFn: (input: CreateDressInput) => createWardrobeItem(input, session?.token ?? ''),
    onSuccess: (item) => {
      setIsAddModalOpen(false)
      setNotice(`Added "${item.name}" to your digital wardrobe.`)
      setFilters((prev) => ({
        ...prev,
        searchQuery: '',
        color: 'All',
        pattern: 'All',
        occasion: 'All',
      }))
      queryClient.setQueryData<WardrobeItem[]>(
        ['wardrobe-items', session?.token],
        (current = []) => [item, ...current]
      )
      void queryClient.invalidateQueries({ queryKey: ['wardrobe-items', session?.token] })
      void queryClient.invalidateQueries({ queryKey: ['wardrobe-analytics', session?.token] })
      void queryClient.invalidateQueries({ queryKey: ['outfit-recommendations', session?.token] })
    },
    onError: (error) => setNotice(error instanceof Error ? error.message : 'Upload failed.'),
  })

  const updateMetadataMutation = useMutation({
    mutationFn: (input: UpdateDressMetadataInput) => updateWardrobeItem(input, session?.token ?? ''),
    onSuccess: (updatedItem) => {
      setEditingItem(null)
      if (selectedDetailItem?.id === updatedItem.id) {
        setSelectedDetailItem(updatedItem)
      }
      setNotice(`Updated metadata for "${updatedItem.name}".`)
      queryClient.setQueryData<WardrobeItem[]>(
        ['wardrobe-items', session?.token],
        (current = []) => current.map((i) => (i.id === updatedItem.id ? updatedItem : i))
      )
      void queryClient.invalidateQueries({ queryKey: ['wardrobe-items', session?.token] })
    },
    onError: (error) => setNotice(error instanceof Error ? error.message : 'Update failed.'),
  })

  const markWornMutation = useMutation({
    mutationFn: (itemId: string) => markWardrobeItemWorn(itemId, session?.token ?? ''),
    onSuccess: (updatedItem) => {
      if (selectedDetailItem?.id === updatedItem.id) {
        setSelectedDetailItem(updatedItem)
      }
      setNotice(
        `Logged a wearing of "${updatedItem.name}" — now ${updatedItem.wearCount} ${
          updatedItem.wearCount === 1 ? 'time' : 'times'
        }.`
      )
      queryClient.setQueryData<WardrobeItem[]>(
        ['wardrobe-items', session?.token],
        (current = []) => current.map((i) => (i.id === updatedItem.id ? updatedItem : i))
      )
      void queryClient.invalidateQueries({ queryKey: ['wardrobe-items', session?.token] })
      void queryClient.invalidateQueries({ queryKey: ['wardrobe-analytics', session?.token] })
    },
    onError: (error) =>
      setNotice(error instanceof Error ? error.message : 'Could not record the wearing.'),
  })

  const replaceImageMutation = useMutation({
    mutationFn: ({ itemId, file }: { itemId: string; file: File }) =>
      replaceWardrobeItemImage(itemId, file, session?.token ?? ''),
    onSuccess: (updatedItem) => {
      if (selectedDetailItem?.id === updatedItem.id) {
        setSelectedDetailItem(updatedItem)
      }
      setNotice(`Replaced image for "${updatedItem.name}".`)
      queryClient.setQueryData<WardrobeItem[]>(
        ['wardrobe-items', session?.token],
        (current = []) => current.map((i) => (i.id === updatedItem.id ? updatedItem : i))
      )
      void queryClient.invalidateQueries({ queryKey: ['wardrobe-items', session?.token] })
    },
    onError: (error) => setNotice(error instanceof Error ? error.message : 'Image replacement failed.'),
  })

  const deleteItemMutation = useMutation({
    mutationFn: (itemId: string) => deleteWardrobeItem(itemId, session?.token ?? ''),
    onSuccess: (data) => {
      setNotice('Item removed from wardrobe.')
      if (selectedDetailItem?.id === data.deleted_item_id) {
        setSelectedDetailItem(null)
      }
      queryClient.setQueryData<WardrobeItem[]>(
        ['wardrobe-items', session?.token],
        (current = []) => current.filter((item) => item.id !== data.deleted_item_id)
      )
      void queryClient.invalidateQueries({ queryKey: ['wardrobe-items', session?.token] })
      void queryClient.invalidateQueries({ queryKey: ['wardrobe-analytics', session?.token] })
      void queryClient.invalidateQueries({ queryKey: ['outfit-recommendations', session?.token] })
    },
    onError: (error) => setNotice(error instanceof Error ? error.message : 'Delete failed.'),
  })

  const duplicateMutation = useMutation({
    mutationFn: (file: File) => checkShoppingImage(file, session?.token ?? ''),
    onSuccess: (result) => {
      setSimilarItems(result.similarItems)
      setDuplicateDecision(result.decision)
      setDuplicateChecks((count) => count + 1)

      const hasMatch = result.decision !== 'no_strong_duplicate' && result.similarItems.length > 0
      setIsDuplicateAlertOpen(hasMatch)
      setNotice(
        result.decision === 'similar_found'
          ? 'Strong duplicate risk found. Review your wardrobe before buying.'
          : hasMatch
            ? 'A similar wardrobe item turned up. Review the comparison before buying.'
            : 'No similar item found in your wardrobe.'
      )
    },
    onError: (error) => {
      setIsDuplicateAlertOpen(false)
      setDuplicateDecision(null)
      setSimilarItems([])
      setNotice(
        error instanceof Error
          ? error.message
          : 'Unable to check for similar items. Please try again.'
      )
    },
  })

  const items = wardrobeQuery.data ?? []
  const analytics = analyticsQuery.data
  const recommendations = recommendationsQuery.data ?? []

  // Filtered & Sorted Items
  const filteredItems = useMemo(() => {
    const uniqueItems: WardrobeItem[] = []
    const seenIds = new Set<string>()
    for (const item of items) {
      if (!seenIds.has(item.id)) {
        seenIds.add(item.id)
        uniqueItems.push(item)
      }
    }

    return uniqueItems
      .filter((item) => {
        // Search query
        if (filters.searchQuery.trim()) {
          const q = filters.searchQuery.trim().toLowerCase()
          const nameMatch = item.name.toLowerCase().includes(q)
          const brandMatch = item.brand ? item.brand.toLowerCase().includes(q) : false
          if (!nameMatch && !brandMatch) return false
        }

        // Color
        if (filters.color !== 'All') {
          if (item.color.toLowerCase() !== filters.color.toLowerCase()) return false
        }

        // Pattern
        if (filters.pattern !== 'All') {
          if (item.pattern.toLowerCase() !== filters.pattern.toLowerCase()) return false
        }

        // Occasion
        if (filters.occasion !== 'All') {
          const hasOccasion = item.occasion.some(
            (o) => o.toLowerCase() === filters.occasion.toLowerCase()
          )
          if (!hasOccasion) return false
        }

        return true
      })
      .sort((a, b) => {
        if (filters.sortBy === 'oldest_added') {
          return (a.createdAt || a.id).localeCompare(b.createdAt || b.id)
        }
        if (filters.sortBy === 'recently_worn') {
          return (b.lastWornDate || '').localeCompare(a.lastWornDate || '')
        }
        if (filters.sortBy === 'least_recently_worn') {
          return a.wearCount - b.wearCount
        }
        // default recently_added
        return (b.createdAt || b.id).localeCompare(a.createdAt || a.id)
      })
  }, [filters, items])

  const topColor = analytics?.most_common_color ?? 'n/a'
  const underused =
    analytics?.least_used_items ?? items.filter((item) => item.wearCount <= 2).length

  function handleDuplicateCheck(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!shoppingFile) {
      setNotice('Upload a shopping image to run the duplicate check.')
      return
    }
    if (duplicateMutation.isPending) return
    duplicateMutation.mutate(shoppingFile)
  }

  function scrollTo(id: string) {
    document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  function handleShowWardrobe() {
    scrollTo('wardrobe')
  }

  function handleShowTrends() {
    scrollTo('insights')
  }

  // Reminders surfaces what you own but rarely wear, using the existing sort.
  function handleShowReminders() {
    setFilters((prev) => ({ ...prev, sortBy: 'least_recently_worn' }))
    setNotice('Showing your least-worn pieces first — these are worth planning an outfit around.')
    scrollTo('wardrobe')
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
    setDuplicateDecision(null)
    setIsDuplicateAlertOpen(false)
    setShoppingFile(null)
    queryClient.clear()
    navigate('/login')
  }

  // Routing Guard logic
  if (!session) {
    if (currentPath === '/signup') {
      return (
        <SignupPage
          onSessionSuccess={handleSessionChange}
          onNavigateToLogin={() => navigate('/login')}
        />
      )
    }
    return (
      <LoginPage
        onSessionSuccess={handleSessionChange}
        onNavigateToSignup={() => navigate('/signup')}
      />
    )
  }

  if (currentPath === '/login' || currentPath === '/signup') {
    window.history.replaceState({}, '', '/dashboard')
  }

  return (
    <main className="min-h-screen bg-[#f7f4ef] text-[#1f2328]">
      <div className="mx-auto flex w-full max-w-[1440px] flex-col gap-6 px-4 py-4 sm:px-6 lg:px-8">
        <TopBar
          user={session.user}
          onSignOut={handleSignOut}
          onShowWardrobe={handleShowWardrobe}
          onShowTrends={handleShowTrends}
          onShowReminders={handleShowReminders}
        />

        {/* Hero Section */}
        <section className="grid gap-4 lg:grid-cols-[1.05fr_0.95fr]">
          <div className="overflow-hidden rounded-xl border border-[#ded8ce] bg-[#fbfaf7] shadow-sm">
            <div className="grid min-h-[380px] lg:grid-cols-[0.95fr_1.05fr]">
              <div className="flex flex-col justify-between p-6 sm:p-8">
                <div>
                  <div className="mb-5 inline-flex items-center gap-2 rounded-full border border-[#dad0c1] bg-white px-3.5 py-1 text-xs font-medium text-[#5c625d]">
                    <Sparkles className="h-4 w-4 text-[#a15c38]" />
                    Digital Wardrobe Module
                  </div>
                  <h1 className="max-w-xl text-4xl font-semibold leading-tight text-[#20231f] sm:text-5xl">
                    StyleSync
                  </h1>
                  <p className="mt-4 max-w-xl text-base leading-7 text-[#626760]">
                    Upload dress photos, organize clothing metadata, view your digital wardrobe,
                    and perform duplicate purchase checks seamlessly.
                  </p>
                </div>

                <div className="pt-6">
                  <button
                    onClick={() => setIsAddModalOpen(true)}
                    className="inline-flex items-center gap-2 rounded-lg bg-[#a15c38] px-5 py-2.5 text-sm font-semibold text-white shadow-md hover:bg-[#b56942] transition-colors"
                  >
                    <Plus className="h-4 w-4" />
                    Add Dress to Wardrobe
                  </button>
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

          <div className="flex flex-col gap-4">
            <WorkflowCard
              icon={Search}
              title="Duplicate purchase check"
              description="Compare a new shopping image against your current digital wardrobe items."
            >
              <form className="space-y-3" onSubmit={handleDuplicateCheck}>
                <FileInput file={shoppingFile} onChange={setShoppingFile} label="Choose shopping image" />
                <button
                  className="inline-flex w-full items-center justify-center gap-2 rounded-md bg-[#a15c38] px-4 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-60"
                  disabled={duplicateMutation.isPending}
                >
                  <Search className="h-4 w-4" />
                  {duplicateMutation.isPending ? 'Checking your wardrobe...' : 'Check similarity'}
                </button>
              </form>
            </WorkflowCard>

            {/* Fills the space under the check card; absolutely positioned on large
                screens so a long report scrolls instead of stretching the hero. */}
            <div className="lg:relative lg:min-h-0 lg:flex-1">
              <section className="flex flex-col rounded-xl border border-[#ded8ce] bg-[#fbfaf7] p-4 lg:absolute lg:inset-0">
                <div className="mb-3 flex items-center gap-2">
                  {duplicateDecision === 'similar_found' ? (
                    <AlertCircle className="h-5 w-5 text-[#a15c38]" />
                  ) : (
                    <CheckCircle2 className="h-5 w-5 text-[#557660]" />
                  )}
                  <h2 className="text-base font-semibold">Similarity report</h2>
                  {duplicateDecision && (
                    <span className="ml-auto rounded-full bg-[#f0e8dd] px-2 py-0.5 text-xs font-medium text-[#7f4b2f]">
                      {decisionLabels[duplicateDecision]}
                    </span>
                  )}
                </div>

                {similarItems.length > 0 ? (
                  <ul className="min-h-0 flex-1 space-y-2 overflow-y-auto">
                    {similarItems.map((item) => (
                      <li
                        key={item.id}
                        className="flex items-center gap-3 rounded-lg border border-[#e2dcd1] bg-white p-2"
                      >
                        <img
                          className="h-14 w-14 shrink-0 rounded-md object-cover"
                          src={item.imageUrl}
                          alt={item.name}
                        />
                        <div className="min-w-0 flex-1">
                          <p className="truncate text-sm font-medium">{item.name}</p>
                          <p className="truncate text-xs text-[#687068]">{item.reason}</p>
                        </div>
                        <span className="shrink-0 rounded-full bg-[#f0e8dd] px-2 py-1 text-sm font-semibold text-[#7f4b2f]">
                          {Math.round(item.similarity * 100)}%
                        </span>
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="flex flex-1 items-center justify-center rounded-lg border border-dashed border-[#ded8ce] p-4 text-center text-sm text-[#687068]">
                    {duplicateMutation.isPending
                      ? 'Checking your wardrobe...'
                      : 'Run a similarity check to see the closest matches from your wardrobe here.'}
                  </p>
                )}
              </section>
            </div>
          </div>
        </section>

        {/* Notice Banner */}
        <div className="rounded-lg border border-[#ded8ce] bg-white px-4 py-3 text-sm text-[#5e645e]">
          {wardrobeQuery.isError
            ? 'Backend connection failed or token expired. Try signing out and back in.'
            : notice}
        </div>

        <OutfitAnalysisPanel token={session.token} />

        {/* Wardrobe Section */}
        <section id="wardrobe" className="scroll-mt-4 space-y-6">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h2 className="text-2xl font-bold text-[#1f2328]">My Wardrobe</h2>
              <p className="text-sm text-[#687068]">
                Browse, search, and manage your authenticated clothing items.
              </p>
            </div>

            <button
              onClick={() => setIsAddModalOpen(true)}
              className="inline-flex items-center gap-2 rounded-lg bg-[#1f2328] px-4 py-2 text-sm font-medium text-white hover:bg-stone-800 transition-colors"
            >
              <Plus className="h-4 w-4" />
              Add Dress
            </button>
          </div>

          {/* Filter Bar */}
          <WardrobeFilterBar
            filters={filters}
            onChange={setFilters}
            totalCount={filteredItems.length}
          />

          {/* Wardrobe Grid & Sidebar */}
          <div className="grid gap-6 lg:grid-cols-[1fr_300px]">
            <WardrobeGrid
              items={filteredItems}
              isLoading={wardrobeQuery.isLoading}
              onSelectItem={(item) => setSelectedDetailItem(item)}
              onAddDressClick={() => setIsAddModalOpen(true)}
            />

            <aside id="insights" className="scroll-mt-4 space-y-4">
              <Panel title="Recommendations" icon={WandSparkles}>
                {recommendations.slice(0, 3).map((recommendation) => (
                  <RecommendationCard
                    key={recommendation.items.map((item) => item.id).join('-')}
                    recommendation={recommendation}
                  />
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
          </div>
        </section>

      </div>

      {/* Modals */}
      <AddDressModal
        isOpen={isAddModalOpen}
        onClose={() => setIsAddModalOpen(false)}
        onSubmit={(data) => addDressMutation.mutate(data)}
        isSubmitting={addDressMutation.isPending}
        error={addDressMutation.error}
      />

      <DressDetailModal
        item={selectedDetailItem}
        isOpen={Boolean(selectedDetailItem)}
        onClose={() => setSelectedDetailItem(null)}
        onEdit={(item) => {
          setSelectedDetailItem(null)
          setEditingItem(item)
        }}
        onMarkWorn={(item) => markWornMutation.mutate(item.id)}
        isMarkingWorn={markWornMutation.isPending}
        onReplaceImage={(item, file) =>
          replaceImageMutation.mutate({ itemId: item.id, file })
        }
        onDelete={(itemId) => deleteItemMutation.mutate(itemId)}
        isReplacingImage={replaceImageMutation.isPending}
        isDeleting={deleteItemMutation.isPending}
      />

      <DuplicateAlertModal
        isOpen={isDuplicateAlertOpen}
        onClose={() => setIsDuplicateAlertOpen(false)}
        purchaseImageUrl={shoppingPreviewUrl}
        match={similarItems[0] ?? null}
        otherMatches={similarItems.slice(1)}
        decision={duplicateDecision ?? undefined}
        onViewItem={
          items.some((item) => item.id === similarItems[0]?.id)
            ? (itemId) => {
                const matchedItem = items.find((item) => item.id === itemId)
                if (!matchedItem) return
                setIsDuplicateAlertOpen(false)
                setSelectedDetailItem(matchedItem)
              }
            : undefined
        }
      />

      <EditDressModal
        item={editingItem}
        isOpen={Boolean(editingItem)}
        onClose={() => setEditingItem(null)}
        onSubmit={(data) => updateMetadataMutation.mutate(data)}
        isSubmitting={updateMetadataMutation.isPending}
      />
    </main>
  )
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

async function checkShoppingImage(file: File, token: string): Promise<DuplicateCheckResult> {
  const formData = new FormData()
  formData.append('image', file)

  const response = await fetch(`${API_BASE_URL}/shopping/check`, {
    method: 'POST',
    headers: getAuthHeader(token),
    body: formData,
  })
  const payload = await parseResponse<{
    decision: DuplicateDecision
    highest_similarity: number
    similar_items: Array<{
      id: string
      name: string
      image_url: string
      similarity: number
      reason: string
    }>
  }>(response)

  return {
    decision: payload.decision,
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

function TopBar({
  user,
  onSignOut,
  onShowWardrobe,
  onShowTrends,
  onShowReminders,
}: {
  user: AuthUser
  onSignOut: () => void
  onShowWardrobe: () => void
  onShowTrends: () => void
  onShowReminders: () => void
}) {
  return (
    <header className="flex flex-col gap-3 rounded-xl border border-[#ded8ce] bg-white px-5 py-3 sm:flex-row sm:items-center sm:justify-between shadow-sm">
      <div className="flex items-center gap-3">
        <div className="grid h-10 w-10 place-items-center rounded-lg bg-[#1f2328] text-white">
          <Shirt className="h-5 w-5" />
        </div>
        <div>
          <p className="font-bold text-[#1f2328]">StyleSync</p>
          <p className="text-xs text-[#697169]">Digital Dress Wardrobe</p>
        </div>
      </div>
      <nav className="flex flex-wrap gap-2 text-sm text-[#4f574f]">
        <NavPill icon={Layers3} label="My Wardrobe" onClick={onShowWardrobe} />
        <NavPill icon={TrendingUp} label="Trends" onClick={onShowTrends} />
        <NavPill icon={CalendarDays} label="Reminders" onClick={onShowReminders} />
        <button
          className="rounded-lg border border-[#e1dbd0] bg-[#fbfaf7] hover:bg-[#f0e8dd] transition-colors px-3.5 py-2 cursor-pointer font-medium text-xs text-[#1f2328]"
          onClick={onSignOut}
        >
          {user.name} / Sign out
        </button>
      </nav>
    </header>
  )
}

function NavPill({
  icon: Icon,
  label,
  onClick,
}: {
  icon: typeof Shirt
  label: string
  onClick: () => void
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="inline-flex items-center gap-2 rounded-lg border border-[#e1dbd0] bg-[#fbfaf7] px-3 py-2 text-xs font-medium text-[#4f574f] transition-colors hover:bg-[#f0e8dd] hover:text-[#1f2328] focus:outline-none focus-visible:ring-2 focus-visible:ring-[#a15c38]"
    >
      <Icon className="h-3.5 w-3.5 text-[#a15c38]" />
      {label}
    </button>
  )
}

const decisionLabels: Record<DuplicateDecision, string> = {
  similar_found: 'Likely duplicate',
  review_matches: 'Worth a look',
  no_strong_duplicate: 'No strong duplicate',
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
    <section className="rounded-xl border border-[#ded8ce] bg-white p-5 shadow-sm">
      <div className="mb-4 flex items-start gap-3">
        <div className="grid h-10 w-10 shrink-0 place-items-center rounded-lg bg-[#f0e8dd] text-[#895035]">
          <Icon className="h-5 w-5" />
        </div>
        <div>
          <h2 className="text-lg font-semibold text-[#1f2328]">{title}</h2>
          <p className="text-xs text-[#687068]">{description}</p>
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
    <label className="flex min-h-24 cursor-pointer flex-col items-center justify-center rounded-lg border border-dashed border-[#cfc7bb] bg-[#fbfaf7] px-3 py-4 text-center text-sm text-[#5d655e]">
      <CloudUpload className="mb-2 h-5 w-5 text-[#a15c38]" />
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

function Panel({
  title,
  icon: Icon,
  children,
}: {
  title: string
  icon: typeof Shirt
  children: ReactNode
}) {
  return (
    <section className="rounded-xl border border-[#ded8ce] bg-white p-4 shadow-sm">
      <div className="mb-3 flex items-center gap-2">
        <Icon className="h-4 w-4 text-[#895035]" />
        <h2 className="font-semibold text-sm text-[#1f2328]">{title}</h2>
      </div>
      <div className="space-y-3">{children}</div>
    </section>
  )
}

function RecommendationCard({ recommendation }: { recommendation: Recommendation }) {
  const title = recommendation.items.map((item) => item.name).join(' + ')
  return (
    <div className="rounded-lg border border-[#e3ddd2] bg-[#fbfaf7] p-3">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="font-medium text-xs">{title}</p>
          <p className="mt-1 text-xs leading-4 text-[#687068]">
            {recommendation.reasons.join(' / ')}
          </p>
        </div>
        <span className="rounded-full bg-white px-2 py-0.5 text-[11px] font-semibold text-[#557660]">
          {Math.round(recommendation.score * 100)}%
        </span>
      </div>
    </div>
  )
}

function StatLine({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-3 text-xs">
      <span className="text-[#687068]">{label}</span>
      <span className="font-semibold capitalize text-[#1f2328]">{value}</span>
    </div>
  )
}

export default App
