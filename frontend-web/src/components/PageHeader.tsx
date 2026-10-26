import { ReactNode } from 'react';

export function PageHeader({
  eyebrow, title, subtitle, actions,
}: {
  eyebrow?: string; title: string; subtitle?: string; actions?: ReactNode;
}) {
  return (
    <div className="pb-8 mb-8 border-b border-ink-200 dark:border-ink-700">
      <div className="flex flex-col lg:flex-row lg:items-end lg:justify-between gap-4">
        <div>
          {eyebrow && <div className="eyebrow mb-2">{eyebrow}</div>}
          <h1 className="font-display text-3xl sm:text-4xl font-semibold tracking-tight
                         text-ink-900 dark:text-white">
            {title}
          </h1>
          {subtitle && (
            <p className="mt-3 text-ink-600 dark:text-ink-300 max-w-2xl text-[0.95rem] leading-relaxed">
              {subtitle}
            </p>
          )}
        </div>
        {actions && <div className="flex items-center gap-2 shrink-0">{actions}</div>}
      </div>
    </div>
  );
}
