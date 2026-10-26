import { useEffect, useMemo, useState } from 'react';
import { Database, Shuffle } from 'lucide-react';
import { Dataset, Stats, type DatasetImage, type StatsResponse } from '../lib/api';
import { PageHeader } from '../components/PageHeader';
import { ImageCard } from '../components/ImageCard';
import { LoadingGrid } from '../components/LoadingGrid';

export default function DatasetExplorer() {
  const [all, setAll] = useState<DatasetImage[]>([]);
  const [stats, setStats] = useState<StatsResponse | null>(null);
  const [cls, setCls] = useState<string>('');
  const [query, setQuery] = useState('');
  const [page, setPage] = useState(0);
  const [loading, setLoading] = useState(true);
  const perPage = 24;

  useEffect(() => {
    setLoading(true);
    Promise.all([Dataset.images({ size: 500 }), Stats.get().catch(() => null)])
      .then(([d, s]) => { setAll(d.images); setStats(s); })
      .finally(() => setLoading(false));
  }, []);

  const filtered = useMemo(() => {
    let x = all;
    if (cls) x = x.filter(i => i.class_name === cls);
    if (query.trim())
      x = x.filter(i => i.image_path.toLowerCase().includes(query.toLowerCase()));
    return x;
  }, [all, cls, query]);

  const pageData = filtered.slice(page * perPage, (page + 1) * perPage);
  const totalPages = Math.max(1, Math.ceil(filtered.length / perPage));
  const classes = Object.keys(stats?.classes ?? {});

  return (
    <div className="space-y-8">
      <PageHeader eyebrow="Dataset" title="Dataset explorer"
                  subtitle="Browse the indexed collection, filter by category, and pivot to visual search."/>

      <div className="card p-4 flex flex-col sm:flex-row gap-3">
        <input value={query} onChange={e => { setQuery(e.target.value); setPage(0); }}
               placeholder="Filter paths…" className="input flex-1"/>
        <select value={cls} onChange={e => { setCls(e.target.value); setPage(0); }} className="input sm:w-56">
          <option value="">All classes ({classes.length})</option>
          {classes.map(c => <option key={c} value={c}>{c} · {stats?.classes[c]}</option>)}
        </select>
        <button className="btn-secondary" onClick={() => setPage(Math.floor(Math.random() * totalPages))}>
          <Shuffle size={14}/> Random
        </button>
      </div>

      <div className="text-xs font-mono text-ink-500 flex justify-between">
        <span>{filtered.length} of {all.length} images</span>
        <span>page {page + 1} / {totalPages}</span>
      </div>

      {loading ? <LoadingGrid n={perPage}/> : (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6 gap-4">
          {pageData.map(d =>
            <ImageCard key={d.image_path} path={d.image_path} className={d.class_name}/>)}
        </div>
      )}

      <div className="flex justify-center gap-2">
        <button className="btn-secondary" disabled={page === 0} onClick={() => setPage(p => p - 1)}>
          ← Prev
        </button>
        <button className="btn-secondary" disabled={page >= totalPages - 1} onClick={() => setPage(p => p + 1)}>
          Next →
        </button>
      </div>
    </div>
  );
}
