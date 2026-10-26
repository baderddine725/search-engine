import { useEffect, useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { Search as SearchIcon, Zap, Filter } from 'lucide-react';
import { Search, type TextSearchResponse, imageUrl } from '../lib/api';
import { PageHeader } from '../components/PageHeader';
import { QueryBar } from '../components/QueryBar';
import { LoadingGrid } from '../components/LoadingGrid';
import { EmptyState } from '../components/EmptyState';
import { fmtMs } from '../lib/utils';

const SIZES = [10, 20, 50, 100];

function hilite(text: string, parts?: string[]) {
  if (!parts || !parts.length) return text;
  // Highlights come wrapped in **…** from the Flask backend
  return parts.map((p, i) => (
    <span key={i} dangerouslySetInnerHTML={{
      __html: p.replace(/\*\*(.+?)\*\*/g, '<mark class="bg-brand-100 text-brand-900 rounded px-0.5">$1</mark>')
    }}/>
  ));
}

export default function TextSearch() {
  const [sp, setSp] = useSearchParams();
  const nav = useNavigate();
  const q = sp.get('q') ?? '';
  const size = Number(sp.get('size') ?? 20);

  const [data, setData] = useState<TextSearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!q.trim()) { setData(null); return; }
    setLoading(true); setError(null);
    Search.text(q, size)
      .then(setData)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, [q, size]);

  const submit = (next: string) => setSp({ q: next, size: String(size) });

  return (
    <div className="space-y-8">
      <PageHeader eyebrow="Text-based retrieval"
                  title="Semantic text search"
                  subtitle="BM25 scoring over titles, tags and descriptions with fuzzy tolerance."/>

      <QueryBar initial={q} onSubmit={submit}
                placeholder="Try 'sunset over the beach' or 'red sports car'…" autoFocus
                trailing={
                  <div className="hidden sm:flex items-center gap-2 pr-2 text-xs text-ink-500">
                    <Filter size={12}/> Top {size}
                  </div>
                }/>

      <div className="flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="eyebrow">Results per page</span>
          {SIZES.map(s =>
            <button key={s}
                    onClick={() => setSp({ q, size: String(s) })}
                    className={`chip ${
                      s === size
                        ? 'bg-ink-900 text-white dark:bg-brand-500'
                        : 'bg-ink-100 text-ink-700 dark:bg-ink-800 dark:text-ink-200 hover:bg-ink-200'}`}>
              {s}
            </button>)}
        </div>
        {data && (
          <div className="flex items-center gap-4 text-xs text-ink-500 font-mono">
            <span>{data.count} returned</span>
            <span className="flex items-center gap-1"><Zap size={10}/>{fmtMs(data.search_ms)}</span>
          </div>
        )}
      </div>

      {!q.trim()
        ? <EmptyState icon={SearchIcon} title="Enter a query to begin"
                      body="BM25 ranks results by relevance across titles, tags and descriptions."/>
        : loading
          ? <LoadingGrid n={size > 12 ? 12 : size}/>
          : error
            ? <EmptyState icon={SearchIcon} title="Search failed" body={error}/>
            : !data?.count
              ? <EmptyState icon={SearchIcon} title={`No matches for "${q}"`}
                            body="Try broader terms or check spelling. BM25 forgives small typos but not missing words."/>
              : <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
                  {data.results.map((r, i) => (
                    <div key={r.photo_id + '-' + i} className="card card-hover overflow-hidden group">
                      <div className="aspect-[4/3] bg-ink-100 dark:bg-ink-900 overflow-hidden relative">
                        {(r.image_path || r.url) && (
                          <img src={r.image_path ? imageUrl(r.image_path) : r.url}
                               alt={r.title} loading="lazy"
                               className="h-full w-full object-cover group-hover:scale-[1.02] transition-transform"/>
                        )}
                        <div className="absolute top-2 left-2 chip bg-white/90 dark:bg-ink-900/80 font-mono !text-[10px]">
                          #{i + 1} · BM25 {r.score.toFixed(2)}
                        </div>
                      </div>
                      <div className="p-3 space-y-1.5">
                        <div className="font-medium text-sm leading-tight line-clamp-2">
                          {r.highlight?.title ? hilite('', r.highlight.title) : r.title || 'Untitled'}
                        </div>
                        {(r.highlight?.description?.[0] || r.highlight?.tags?.[0] || r.description) && (
                          <div className="text-xs text-ink-500 dark:text-ink-400 line-clamp-2">
                            {r.highlight?.description ? hilite('', r.highlight.description) :
                             r.highlight?.tags ? hilite('', r.highlight.tags) :
                             r.description}
                          </div>
                        )}
                        {r.tags && (
                          <div className="flex flex-wrap gap-1 pt-1">
                            {r.tags.split(/\s+/).slice(0, 4).map(t =>
                              <span key={t} className="chip-neutral !text-[10px]">{t}</span>)}
                          </div>
                        )}
                        {r.image_path && (
                          <button onClick={() => nav(`/similar?path=${encodeURIComponent(r.image_path!)}`)}
                                  className="btn-secondary !py-1.5 !px-3 !text-xs w-full mt-2">
                            Find visually similar →
                          </button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>}
    </div>
  );
}
