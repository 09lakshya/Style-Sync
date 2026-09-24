import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { MutationCache, QueryCache, QueryClient, QueryClientProvider } from '@tanstack/react-query'
import './index.css'
import App from './App.tsx'
import { isAuthError } from './lib/apiError'
import { removeStoredSession } from './lib/auth'

/** Drop a session the server has stopped accepting.
 *
 *  readStoredSession catches the common case -- a token that was already stale
 *  when the tab opened -- but a session can also expire while the app is open.
 *  Without this, every query just keeps failing against a token that will never
 *  work again, which is what filled the console with repeating 401s.
 *
 *  The reload is deliberate: session state lives in App's useState, and a hard
 *  navigation is the one thing guaranteed to clear it along with every cached
 *  query, rather than leaving half the screen populated from stale data.
 */
let handlingAuthFailure = false
function handleAuthFailure(error: unknown) {
  if (!isAuthError(error) || handlingAuthFailure) return
  handlingAuthFailure = true
  removeStoredSession()
  if (window.location.pathname !== '/login') {
    window.location.assign('/login')
  }
}

const queryClient = new QueryClient({
  queryCache: new QueryCache({ onError: handleAuthFailure }),
  mutationCache: new MutationCache({ onError: handleAuthFailure }),
  defaultOptions: {
    queries: {
      // Retrying a 4xx three times turns one rejected request into four
      // identical console errors and tells us nothing new -- the answer to
      // "your token is invalid" does not change on the second ask.
      retry: (failureCount, error) => {
        if (isAuthError(error)) return false
        return failureCount < 3
      },
    },
  },
})

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </StrictMode>,
)
