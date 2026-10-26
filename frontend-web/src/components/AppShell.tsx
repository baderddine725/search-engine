import { ReactNode, useEffect, useState } from 'react';
import { NavLink, Link } from 'react-router-dom';
import {
  LayoutGrid, Search, Image as ImageIcon, Shuffle, GitCompare, Database,
  BarChart3, Network, Code2, Settings as SettingsIcon, Moon, Sun, Menu, X,
  Zap,
} from 'lucide-react';
import { Health } from '../lib/api';
import { cn } from '../lib/utils';

const nav = [
  { to: '/',             label: 'Overview',        icon: LayoutGrid },
  { to: '/text',         label: 'Text Search',     icon: Search },
  { to: '/visual',       label: 'Visual Search',   icon: ImageIcon },
  { to: '/similar',      label: 'Similar Images',  icon: Shuffle },
  { to: '/compare',      label: 'Model Comparison',icon: GitCompare },
  { to: '/dataset',      label: 'Dataset Explorer',icon: Database },
  { to: '/evaluation',   label: 'Evaluation',      icon: BarChart3 },
  { to: '/architecture', label: 'Architecture',    icon: Network },
  { to: '/api',          label: 'API Docs',        icon: Code2 },
  { to: '/settings',     label: 'Settings',        icon: SettingsIcon },
];

function Brand({ compact = false }: { compact?: boolean }) {
  return (
    <Link to="/" className="flex items-center gap-2.5 py-2 px-1 group">
      <div className="relative h-9 w-9 rounded-xl bg-gradient-to-br from-brand-500 via-brand-600 to-cyan
                      shadow-lg shadow-brand-500/30 flex items-center justify-center">
        <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="white" strokeWidth="2.3"
             strokeLinecap="round" strokeLinejoin="round">
          <circle cx="10" cy="10" r="6"/>
          <line x1="14.5" y1="14.5" x2="20" y2="20"/>
        </svg>
      </div>
      {!compact && (
        <div className="leading-tight">
          <div className="font-semibold text-ink-900 dark:text-white tracking-tight">
            VisionSearch <span className="text-brand-600 dark:text-brand-400">AI</span>
          </div>
          <div className="text-[10px] text-ink-500 dark:text-ink-400 uppercase tracking-widest">
            Visual Discovery
          </div>
        </div>
      )}
    </Link>
  );
}

function HealthDot() {
  const [state, setState] = useState<'ok' | 'bad' | 'loading'>('loading');
  const [ver, setVer] = useState<string | undefined>();
  useEffect(() => {
    const tick = () =>
      Health.get()
        .then(h => { setState(h.status === 'ok' ? 'ok' : 'bad'); setVer(h.elasticsearch); })
        .catch(() => setState('bad'));
    tick();
    const i = setInterval(tick, 15_000);
    return () => clearInterval(i);
  }, []);
  const colour = state === 'ok' ? 'text-emerald-500'
                : state === 'bad' ? 'text-red-500' : 'text-amber-500';
  const label = state === 'ok' ? `Online · ES ${ver}`
              : state === 'bad' ? 'Backend unreachable' : 'Checking…';
  return (
    <div className="flex items-center gap-2 text-xs">
      <span className={cn('glow-dot', colour)} />
      <span className="text-ink-600 dark:text-ink-300">{label}</span>
    </div>
  );
}

function ThemeToggle() {
  const [dark, setDark] = useState(() =>
    document.documentElement.classList.contains('dark'));
  const toggle = () => {
    const next = !dark;
    setDark(next);
    document.documentElement.classList.toggle('dark', next);
    localStorage.setItem('theme', next ? 'dark' : 'light');
  };
  return (
    <button onClick={toggle}
            className="btn-ghost h-9 w-9 p-0 rounded-lg"
            aria-label="Toggle theme">
      {dark ? <Sun size={16} /> : <Moon size={16} />}
    </button>
  );
}

function SidebarContent({ onNav }: { onNav?: () => void }) {
  return (
    <div className="flex flex-col h-full">
      <div className="px-4 pt-5 pb-4">
        <Brand />
      </div>
      <nav className="flex-1 px-3 overflow-y-auto scrollbar-slim">
        <div className="eyebrow px-3 pt-2 pb-2">Workspace</div>
        <ul className="space-y-0.5">
          {nav.map(({ to, label, icon: Icon }) => (
            <li key={to}>
              <NavLink
                to={to}
                end={to === '/'}
                onClick={onNav}
                className={({ isActive }) =>
                  cn(
                    'group flex items-center gap-3 rounded-lg px-3 py-2 text-sm',
                    'transition-colors',
                    isActive
                      ? 'bg-brand-50 text-brand-700 font-medium dark:bg-brand-500/10 dark:text-brand-300'
                      : 'text-ink-600 hover:bg-ink-100 hover:text-ink-900 dark:text-ink-300 dark:hover:bg-ink-800 dark:hover:text-white',
                  )
                }
              >
                <Icon size={16} className="shrink-0" />
                <span className="truncate">{label}</span>
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>
      <div className="px-5 pb-5 pt-4 border-t border-ink-200 dark:border-ink-700">
        <div className="flex items-center gap-2 text-xs text-ink-500 dark:text-ink-400 font-mono">
          <Zap size={12} className="text-brand-500"/>
          <span>v0.1 · demo build</span>
        </div>
      </div>
    </div>
  );
}

export function AppShell({ children }: { children: ReactNode }) {
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <div className="min-h-screen bg-ink-50 dark:bg-ink-900 text-ink-900 dark:text-ink-50">
      {/* Mobile top bar */}
      <header className="lg:hidden sticky top-0 z-30 h-14 border-b border-ink-200 dark:border-ink-700
                         bg-white/80 dark:bg-ink-800/80 backdrop-blur px-4 flex items-center justify-between">
        <button onClick={() => setMobileOpen(true)} className="btn-ghost h-9 w-9 p-0" aria-label="Open menu">
          <Menu size={18} />
        </button>
        <Brand />
        <ThemeToggle />
      </header>

      {/* Desktop sidebar */}
      <aside className="hidden lg:flex fixed inset-y-0 left-0 w-64 border-r border-ink-200
                        bg-white dark:bg-ink-800 dark:border-ink-700 z-20">
        <SidebarContent />
      </aside>

      {/* Mobile drawer */}
      {mobileOpen && (
        <div className="lg:hidden fixed inset-0 z-40 flex">
          <div className="absolute inset-0 bg-ink-900/40 backdrop-blur-sm"
               onClick={() => setMobileOpen(false)} />
          <div className="relative w-72 bg-white dark:bg-ink-800 border-r border-ink-200 dark:border-ink-700
                          shadow-2xl">
            <button onClick={() => setMobileOpen(false)}
                    className="absolute right-3 top-3 btn-ghost h-8 w-8 p-0" aria-label="Close">
              <X size={16}/>
            </button>
            <SidebarContent onNav={() => setMobileOpen(false)} />
          </div>
        </div>
      )}

      {/* Main content area */}
      <div className="lg:pl-64">
        <div className="hidden lg:flex sticky top-0 z-10 h-16 items-center justify-end gap-3
                        px-8 border-b border-ink-200 dark:border-ink-700
                        bg-ink-50/80 dark:bg-ink-900/80 backdrop-blur">
          <HealthDot />
          <div className="h-5 w-px bg-ink-200 dark:bg-ink-700 mx-1" />
          <ThemeToggle />
        </div>
        <main className="px-4 sm:px-6 lg:px-10 py-8 max-w-[1500px] mx-auto">
          {children}
        </main>
      </div>
    </div>
  );
}
