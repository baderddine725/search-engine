import { ReactNode } from 'react';
import { LucideIcon } from 'lucide-react';

export function EmptyState({
  icon: Icon, title, body, action,
}: { icon?: LucideIcon; title: string; body?: string; action?: ReactNode }) {
  return (
    <div className="card p-10 text-center">
      {Icon && (
        <div className="mx-auto mb-4 h-12 w-12 rounded-xl bg-ink-100 dark:bg-ink-700
                        flex items-center justify-center text-ink-500 dark:text-ink-300">
          <Icon size={22}/>
        </div>
      )}
      <h3 className="font-display font-semibold text-lg">{title}</h3>
      {body && <p className="mt-1.5 text-sm text-ink-600 dark:text-ink-300 max-w-md mx-auto">{body}</p>}
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}
