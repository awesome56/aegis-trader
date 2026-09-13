export interface NavItem {
  label: string
  to: string
  icon: string
  description?: string
}

/** Primary sidebar navigation. */
export const primaryNav: NavItem[] = [
  { label: 'Dashboard', to: '/dashboard', icon: 'i-lucide-layout-dashboard' },
  { label: 'Portfolio', to: '/portfolio', icon: 'i-lucide-pie-chart' },
  { label: 'Markets', to: '/markets', icon: 'i-lucide-line-chart' },
  { label: 'Positions', to: '/positions', icon: 'i-lucide-briefcase' },
  { label: 'Trades', to: '/trades', icon: 'i-lucide-arrow-left-right' },
  { label: 'Orders', to: '/orders', icon: 'i-lucide-clipboard-list' },
  { label: 'Proposals', to: '/agent/proposals', icon: 'i-lucide-file-text' },
  { label: 'Agent', to: '/agent', icon: 'i-lucide-bot' },
  { label: 'Strategies', to: '/strategies', icon: 'i-lucide-workflow' },
  { label: 'Risk', to: '/risk', icon: 'i-lucide-shield-alert' },
  { label: 'Backtests', to: '/backtests', icon: 'i-lucide-flask-conical' },
  { label: 'Activity', to: '/activity', icon: 'i-lucide-activity' },
  { label: 'Settings', to: '/settings', icon: 'i-lucide-settings' },
]

export function isActiveRoute(currentPath: string, target: string): boolean {
  return currentPath === target || currentPath.startsWith(`${target}/`)
}
