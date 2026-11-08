import React from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AuthProvider } from './context/AuthContext'
import { ToastProvider } from './context/ToastContext'
import { AppLayout } from './components/layout/AppLayout'

// Pages
import { OverviewPage } from './pages/OverviewPage'
import { DocumentsPage } from './pages/DocumentsPage'
import { SearchPage } from './pages/SearchPage'
import { AssistantPage } from './pages/AssistantPage'
import { CompliancePage } from './pages/CompliancePage'
import { GapAnalysisPage } from './pages/GapAnalysisPage'
import { KnowledgeGraphPage } from './pages/KnowledgeGraphPage'
import { RemediationPage } from './pages/RemediationPage'
import { SettingsPage } from './pages/SettingsPage'

// Configure TanStack QueryClient with reasonable defaults
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 30, // 30 seconds
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
})

export const App: React.FC = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <ToastProvider>
          <BrowserRouter>
            <Routes>
              <Route path="/" element={<AppLayout />}>
                <Route index element={<OverviewPage />} />
                <Route path="documents" element={<DocumentsPage />} />
                <Route path="search" element={<SearchPage />} />
                <Route path="assistant" element={<AssistantPage />} />
                <Route path="compliance" element={<CompliancePage />} />
                <Route path="gaps" element={<GapAnalysisPage />} />
                <Route path="knowledge" element={<KnowledgeGraphPage />} />
                <Route path="remediation" element={<RemediationPage />} />
                <Route path="settings" element={<SettingsPage />} />
                <Route path="*" element={<Navigate to="/" replace />} />
              </Route>
            </Routes>
          </BrowserRouter>
        </ToastProvider>
      </AuthProvider>
    </QueryClientProvider>
  )
}

export default App
