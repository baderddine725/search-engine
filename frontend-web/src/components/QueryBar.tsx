import { Search } from 'lucide-react';
import { KeyboardEvent, useState } from 'react';

export function QueryBar({
  onSubmit, placeholder, initial, autoFocus, trailing,
}: {
  onSubmit: (q: string) => void;
  placeholder?: string; initial?: string; autoFocus?: boolean;
  trailing?: React.ReactNode;
}) {
  const [q, setQ] = useState(initial ?? '');
  const kd = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && q.trim()) onSubmit(q.trim());
  };
  return (
    <div className="card flex items-center p-1.5 pl-4 gap-2
                    focus-within:ring-2 focus-within:ring-brand-500/30 focus-within:border-brand-300">
      <Search size={16} className="text-ink-400 shrink-0"/>
      <input
        value={q} onChange={e => setQ(e.target.value)} onKeyDown={kd}
        placeholder={placeholder ?? 'Search…'}
        autoFocus={autoFocus}
        className="flex-1 bg-transparent outline-none text-sm py-2.5
                   placeholder-ink-400 text-ink-900 dark:text-ink-50"
      />
      {trailing}
      <button
        className="btn-primary !py-1.5 !px-4"
        onClick={() => q.trim() && onSubmit(q.trim())}
        disabled={!q.trim()}>
        Search
      </button>
    </div>
  );
}
