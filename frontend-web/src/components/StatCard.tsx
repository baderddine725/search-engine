import { LucideIcon } from 'lucide-react';
import { cn } from '../lib/utils';

export function StatCard({
  label, value, unit, trend, icon: Icon, accent = 'brand', loading,
}: {
  label: string; value: string | number; unit?: string;
  trend?: string; icon?: LucideIcon; loading?: boolean;
  accent?: 'brand' | 'violet' | 'cyan' | 'emerald';
}) {
  const accentClass = {
    brand:   'from-brand-500/15 to-brand-500/0 text-brand-600 dark:text-brand-300',
    violet:  'from-violet/15 to-violet/0 text-violet',
    cyan:    'from-cyan/15 to-cyan/0 text-cyan',
    emerald: 'from-emerald-500/15 to-emerald-500/0 text-emerald-600 dark:text-emerald-300',
  }[accent];

  return (
    <div className={cn(
      'card p-5 relative overflow-hidden group card-hover',
    )}>
      <div className={cn(
        'absolute inset-x-0 top-0 h-px bg-gradient-to-r opacity-70',
        accent === 'brand' ? 'from-transparent via-brand-500 to-transparent' :
        accent === 'violet' ? 'from-transparent via-violet to-transparent' :
        accent === 'cyan' ? 'from-transparent via-cyan to-transparent' :
        'from-transparent via-emerald-500 to-transparent'
      )}/>
      <div className="flex items-start justify-between">
        <div className="eyebrow">{label}</div>
        {Icon && (
          <div className={cn(
            'h-8 w-8 rounded-lg bg-gradient-to-br grid place-items-center',
            accentClass,
          )}>
            <Icon size={14} />
          </div>
        )}
      </div>
      <div className="mt-2 flex items-baseline gap-1.5">
        {loading
          ? <div className="skeleton h-8 w-24"/>
          : <div className="font-display text-3xl font-semibold tracking-tight tabular-nums">
              {value}
            </div>}
        {unit && <div className="text-xs text-ink-500 dark:text-ink-400">{unit}</div>}
      </div>
      {trend && (
        <div className="mt-1 text-xs text-ink-500 dark:text-ink-400 font-mono">
          {trend}
        </div>
      )}
    </div>
  );
}
