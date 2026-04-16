import { createContext, useContext, useState, useEffect, type ReactNode } from 'react'

export type CommodityId = 'doupo' | 'yumi' | 'caipo' | 'yufen' | 'douyou'
export interface CommodityDef { id: CommodityId; name: string; unit: string; basePrice: number; volatility: number }

export const COMMODITIES: CommodityDef[] = [
  { id: 'doupo', name: '豆粕', unit: '元/吨', basePrice: 5000, volatility: 1.0 },
  { id: 'yumi', name: '玉米', unit: '元/吨', basePrice: 2800, volatility: 0.6 },
  { id: 'caipo', name: '菜粕', unit: '元/吨', basePrice: 3200, volatility: 0.8 },
  { id: 'yufen', name: '鱼粉', unit: '元/吨', basePrice: 12500, volatility: 1.5 },
  { id: 'douyou', name: '豆油', unit: '元/吨', basePrice: 8200, volatility: 0.9 },
]

export type PageId = 'overview' | 'data' | 'model' | 'agent' | 'integration' | 'analysis'
export type PeriodId = '7d' | '30d' | '90d'
export type ThemeMode = 'dark' | 'light'

interface AppState {
  commodity: CommodityId; setCommodity: (c: CommodityId) => void
  period: PeriodId; setPeriod: (p: PeriodId) => void
  page: PageId; setPage: (p: PageId) => void
  theme: ThemeMode; toggleTheme: () => void
  getCommodityDef: () => CommodityDef
}

const AppContext = createContext<AppState | null>(null)

export function AppProvider({ children }: { children: ReactNode }) {
  const [commodity, setCommodity] = useState<CommodityId>('doupo')
  const [period, setPeriod] = useState<PeriodId>('30d')
  const [page, setPage] = useState<PageId>('overview')
  const [theme, setTheme] = useState<ThemeMode>(() => {
    const saved = localStorage.getItem('theme')
    return (saved === 'light' ? 'light' : 'dark') as ThemeMode
  })

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    localStorage.setItem('theme', theme)
  }, [theme])

  const toggleTheme = () => setTheme(t => t === 'dark' ? 'light' : 'dark')
  const getCommodityDef = () => COMMODITIES.find(c => c.id === commodity)!

  return (
    <AppContext.Provider value={{ commodity, setCommodity, period, setPeriod, page, setPage, theme, toggleTheme, getCommodityDef }}>
      {children}
    </AppContext.Provider>
  )
}

export function useApp() {
  const ctx = useContext(AppContext)
  if (!ctx) throw new Error('useApp must be inside AppProvider')
  return ctx
}
