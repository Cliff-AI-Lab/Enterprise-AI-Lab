import { AppProvider, useApp } from '@/context/AppContext'
import Header from '@/components/layout/Header'
import Sidebar from '@/components/layout/Sidebar'
import OverviewPage from '@/components/pages/OverviewPage'
import DataManagePage from '@/components/pages/DataManagePage'
import ModelManagePage from '@/components/pages/ModelManagePage'
import AgentManagePage from '@/components/pages/AgentManagePage'
import AppIntegrationPage from '@/components/pages/AppIntegrationPage'
import AnalysisPage from '@/components/pages/AnalysisPage'

function PageRouter() {
  const { page } = useApp()
  switch (page) {
    case 'overview': return <OverviewPage />
    case 'data': return <DataManagePage />
    case 'model': return <ModelManagePage />
    case 'agent': return <AgentManagePage />
    case 'integration': return <AppIntegrationPage />
    case 'analysis': return <AnalysisPage />
  }
}

function AppLayout() {
  return (
    <div className="min-h-screen bg-bg-primary flex flex-col">
      <Header />
      <div className="flex flex-1 overflow-hidden">
        <Sidebar />
        <PageRouter />
      </div>
    </div>
  )
}

export default function App() {
  return (
    <AppProvider>
      <AppLayout />
    </AppProvider>
  )
}
