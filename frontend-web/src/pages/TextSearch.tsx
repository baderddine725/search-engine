import { useEffect, useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { Search as SearchIcon, Zap, Filter, Database, Globe } from 'lucide-react';
import { Search, Mirflickr, Stats as StatsAPI,
         type TextSearchResponse, type MirflickrTextResponse,
         imageUrl, mirflickrThumb } from '../lib/api';
import { PageHeader } from '../components/PageHeader';
import { QueryBar } from '../components/QueryBar';
import { LoadingGrid } from '../components/LoadingGrid';
import { EmptyState } from '../components/EmptyState';
import { cn, fmtMs } from '../lib/utils';

const SIZES = [10, 20, 50, 100];
type Source = 'local' | 'mirflickr';

// Thumbnail with a serif-italic placeholder fallback for MIRFLICKR photos
// whose archive isn't present on disk yet.
function MirflickrThumbImg({ photoId, alt }: { photoId: number; alt?: string }) {
  const [failed, setFailed] = useState(false);
  if (failed) {
    return (
      <div className="h-full w-full flex items-center justify-center">
        <div className="text-center p-4">
          <div className="font-display text-2xl text-ink-400 dark:text-ink-500
                          font-serif italic">im{photoId}</div>
          <div className="text-[10px] mt-1 uppercase tracking-wider
                          text-ink-400 dark:text-ink-500 font-mono">MIRFLICKR</div>
        </div>
      </div>
    );
  }
  return (
    <img src={mirflickrThumb(photoId)} alt={alt} loading="lazy"
         onError={() => setFailed(true)}
         className="h-full w-full object-cover transition-transform group-hover:scale-[1.02]"/>
  );
}

function hilite(text: string, parts?: string[]) {
  if (!parts || !parts.length) return text;
  // Highlights come wrapped in **…** from the Flask backend
  return parts.map((p, i) => (
    <span key={i} dangerouslySetInnerHTML={{
      __html: p.replace(/\*\*(.+?)\*\*/g, '<mark class="bg-brand-100 text-brand-900 rounded px-0.5">$1</mark>')
    }}/>
  ));
}

type Result = {
  key: string; title: string; snippet?: string; tags: string;
  score: number; image?: string; subtitle?: string; onPivot?: () => void;
};

export default function TextSearch() {
  const [sp, setSp] = useSearchParams();
  const nav = useNavigate();
  const q = sp.get('q') ?? '';
  const size = Number(sp.get('size') ?? 20);
  const source = (sp.get('src') as Source) || 'mirflickr';

  const [data, setData] = useState<TextSearchResponse | MirflickrTextResponse | null>(null);
  const [total, setTotal] = useState<number>(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [counts, setCounts] = useState<{ local: number; mir: number } | null>(null);

  useEffect(() => {
    Promise.all([
      StatsAPI.get().catch(() => null),
      Mirflickr.stats().catch(() => null),
    ]).then(([s, m]) =>
      setCounts({ local: s?.text_documents ?? 0, mir: m?.indexed_documents ?? 0 })
    );
  }, []);

  useEffect(() => {
    if (!q.trim()) { setData(null); setTotal(0); return; }
    setLoading(true); setError(null);
    const call = source === 'mirflickr'
      ? Mirflickr.text(q, size)
      : Search.text(q, size);
    call.then((d: any) => { setData(d); setTotal(d.total ?? d.count ?? 0); })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, [q, size, source]);

  const submit = (next: string) =>
    setSp({ q: next, size: String(size), src: source });
  const setSource = (next: Source) =>
    setSp({ q, size: String(size), src: next });

  const results = (data?.results as any[]) ?? [];
  const empty_body = source === 'local'
    ? "The local index only covers the 400 flower photos (daisy, dandelion, roses, " +
      "sunflowers, tulips). Try terms like 'rose', 'yellow', 'spring' — or switch to " +
      "MIRFLICKR for a million real Flickr photos."
    : "Try broader terms or check spelling. BM25 forgives small typos but not missing words.";

  return (
    <div className="space-y-8">
      <PageHeader eyebrow="Text-based retrieval"
                  title="Semantic text search"
                  subtitle="BM25 scoring over titles, tags and descriptions with fuzzy tolerance."/>

      {/* Dataset selector */}
      <div className="card p-1.5 inline-flex gap-1">
        {([
          { k: 'mirflickr', label: 'MIRFLICKR-1M', icon: Globe,
            sub: counts ? `${counts.mir.toLocaleString()} Flickr photos` : '…' },
          { k: 'local',     label: 'Local images',  icon: Database,
            sub: counts ? `${counts.local.toLocaleString()} documents` : '…' },
        ] as const).map(opt => (
          <button key={opt.k} onClick={() => setSource(opt.k)}
                  className={cn(
                    'flex items-center gap-2.5 px-3.5 py-2 rounded-md text-sm font-medium transition',
                    source === opt.k
                      ? 'bg-ink-900 text-white dark:bg-brand-500'
                      : 'text-ink-600 hover:bg-ink-100 dark:text-ink-300 dark:hover:bg-ink-800'
                  )}>
            <opt.icon size={14}/>
            <span>{opt.label}</span>
            <span className="font-mono text-[10px] opacity-70">· {opt.sub}</span>
          </button>
        ))}
      </div>

      <QueryBar initial={q} onSubmit={submit}
                placeholder={source === 'mirflickr'
                  ? "Try 'tunis medina' or 'sunset beach'…"
                  : "Try 'rose', 'yellow flower', 'spring garden'…"} autoFocus
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
                    onClick={() => setSp({ q, size: String(s), src: source })}
                    className={`chip ${
                      s === size
                        ? 'bg-ink-900 text-white dark:bg-brand-500'
                        : 'bg-ink-100 text-ink-700 dark:bg-ink-800 dark:text-ink-200 hover:bg-ink-200'}`}>
              {s}
            </button>)}
        </div>
        {data && (
          <div className="flex items-center gap-4 text-xs text-ink-500 font-mono">
            {total > results.length
              ? <span><b className="text-ink-800 dark:text-ink-100">{total.toLocaleString()}</b> matches</span>
              : <span>{results.length} returned</span>}
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
            : !results.length
              ? <EmptyState icon={SearchIcon} title={`No matches for "${q}"`} body={empty_body}
                            action={source === 'local'
                              ? <button className="btn-primary" onClick={() => setSource('mirflickr')}>
                                  Search MIRFLICKR-1M instead →
                                </button>
                              : null}/>
              : <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
                  {results.map((r, i) => (
                    <div key={(r.photo_id ?? r.image_path ?? i) + '-' + i}
                         className="card card-hover overflow-hidden group">
                      <div className="aspect-[4/3] overflow-hidden relative
                                      bg-gradient-to-br from-ink-100 to-ink-200
                                      dark:from-ink-800 dark:to-ink-900">
                        {r.image_path ? (
                          <img src={imageUrl(r.image_path)} alt={r.title} loading="lazy"
                               className="h-full w-full object-cover group-hover:scale-[1.02] transition-transform"/>
                        ) : r.photo_id !== undefined ? (
                          <MirflickrThumbImg photoId={r.photo_id} alt={r.title}/>
                        ) : null}
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
                        {r.owner && (
                          <div className="text-[11px] text-ink-500 dark:text-ink-400 italic">
                            by {r.owner}
                          </div>
                        )}
                        {r.tags && (
                          <div className="flex flex-wrap gap-1 pt-1">
                            {r.tags.split(/\s+/).slice(0, 4).map((t: string) =>
                              <span key={t} className="chip-neutral !text-[10px]">{t}</span>)}
                          </div>
                        )}
                        {r.image_path ? (
                          <button onClick={() => nav(`/similar?path=${encodeURIComponent(r.image_path!)}`)}
                                  className="btn-secondary !py-1.5 !px-3 !text-xs w-full mt-2">
                            Find visually similar →
                          </button>
                        ) : r.photo_id !== undefined ? (
                          <button onClick={() => nav(`/mirflickr/${r.photo_id}`)}
                                  className="btn-secondary !py-1.5 !px-3 !text-xs w-full mt-2">
                            Find similar by MPEG-7 →
                          </button>
                        ) : null}
                      </div>
                    </div>
                  ))}
                </div>}
    </div>
  );
}
