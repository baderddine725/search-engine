import { useEffect, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { Shuffle, ArrowLeft, Zap } from 'lucide-react';
import { Mirflickr, mirflickrThumb } from '../lib/api';
import { PageHeader } from '../components/PageHeader';
import { LoadingGrid } from '../components/LoadingGrid';
import { EmptyState } from '../components/EmptyState';
import { cn, fmtMs } from '../lib/utils';

type Descriptor = 'edge' | 'homo';

const DESC_META: Record<Descriptor, { label: string; sub: string }> = {
  edge: { label: 'Edge Histogram',       sub: 'MPEG-7 · 150 dims · scan linéaire sur 1 M points' },
  homo: { label: 'Homogeneous Texture',  sub: 'MPEG-7 · 43 dims · VP-Tree ≈ 73 % élagage' },
};

export default function MirflickrSimilar() {
  const { photoId: raw } = useParams<{ photoId: string }>();
  const nav = useNavigate();
  const photoId = Number(raw);
  const [descriptor, setDescriptor] = useState<Descriptor>('homo');
  const [size, setSize] = useState(12);
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    if (!photoId) return;
    setLoading(true); setErr(null);
    Mirflickr.similar(photoId, descriptor, size)
      .then(setData)
      .catch(e => setErr(e.message))
      .finally(() => setLoading(false));
  }, [photoId, descriptor, size]);

  return (
    <div className="space-y-8">
      <PageHeader eyebrow="MIRFLICKR-1M · CBIR"
                  title="Similar images by MPEG-7"
                  subtitle="k-nearest neighbours over the MPEG-7 descriptors shipped with the
                            dataset. The index covers the entire 1,000,000-image collection."
                  actions={
                    <button className="btn-secondary" onClick={() => nav(-1)}>
                      <ArrowLeft size={14}/> Back
                    </button>
                  }/>

      <div className="grid lg:grid-cols-[320px_1fr] gap-6">
        {/* Query card + controls */}
        <aside className="space-y-4">
          <div className="card overflow-hidden">
            <div className="aspect-square bg-ink-100 dark:bg-ink-900 overflow-hidden">
              <img src={mirflickrThumb(photoId)} alt=""
                   onError={e => (e.currentTarget.style.display='none')}
                   className="h-full w-full object-cover"/>
            </div>
            <div className="p-4">
              <div className="eyebrow mb-1">Query image</div>
              <div className="font-mono text-xs">photo_id · {photoId}</div>
            </div>
          </div>

          <div className="card p-4">
            <div className="eyebrow mb-2">Descriptor</div>
            <div className="space-y-1.5">
              {(Object.entries(DESC_META) as [Descriptor, typeof DESC_META['edge']][]).map(([k, m]) => (
                <button key={k} onClick={() => setDescriptor(k)}
                        className={cn(
                          'w-full text-left p-3 rounded-lg border transition',
                          descriptor === k
                            ? 'border-brand-400 bg-brand-50 dark:bg-brand-500/5'
                            : 'border-ink-200 dark:border-ink-700 hover:border-ink-300')}>
                  <div className="font-medium text-sm">{m.label}</div>
                  <div className="text-[11px] text-ink-500 font-mono mt-0.5">{m.sub}</div>
                </button>
              ))}
            </div>
          </div>

          <div className="card p-4">
            <div className="flex items-center justify-between mb-2">
              <div className="eyebrow">Results</div>
              <span className="font-mono text-sm">{size}</span>
            </div>
            <input type="range" min={4} max={30} value={size}
                   onChange={e => setSize(Number(e.target.value))}
                   className="w-full accent-brand-500"/>
          </div>

          {data && !loading && (
            <div className="text-xs font-mono text-ink-500 flex justify-between">
              <span>{data.count} results</span>
              <span className="flex items-center gap-1"><Zap size={10}/>{fmtMs(data.search_ms)}</span>
            </div>
          )}
        </aside>

        {/* Results */}
        <section>
          {loading ? <LoadingGrid n={size}/>
            : err ? <EmptyState icon={Shuffle} title="Search failed" body={err}/>
            : data?.results?.length
              ? <>
                  <div className="mb-3 text-xs text-ink-500 font-mono">
                    index · <span className="text-ink-700 dark:text-ink-200">{data.index}</span>
                    {data.pruned_pct !== undefined &&
                      <> · pruned <span className="text-ink-700 dark:text-ink-200">
                           {data.pruned_pct.toFixed(1)} %</span></>}
                  </div>
                  <div className="grid grid-cols-2 sm:grid-cols-3 xl:grid-cols-4 gap-4">
                    {data.results.map((r: any, i: number) => (
                      <Link key={r.photo_id}
                            to={`/mirflickr/${r.photo_id}`}
                            className="card card-hover overflow-hidden group block">
                        <div className="aspect-[4/3] bg-ink-100 dark:bg-ink-900 overflow-hidden relative">
                          <img src={mirflickrThumb(r.photo_id)} alt=""
                               loading="lazy"
                               className="h-full w-full object-cover
                                          transition-transform group-hover:scale-[1.02]"/>
                          <div className="absolute top-2 left-2 chip bg-white/90 dark:bg-ink-900/80
                                          font-mono !text-[10px]">
                            #{i + 1} · d {r.distance.toFixed(2)}
                          </div>
                        </div>
                        <div className="p-3 space-y-1">
                          <div className="font-medium text-sm leading-tight line-clamp-2">
                            {r.title || 'Untitled'}
                          </div>
                          <div className="text-[11px] font-mono text-ink-500">
                            im{r.photo_id}
                          </div>
                          {r.tags && (
                            <div className="flex flex-wrap gap-1 pt-1">
                              {r.tags.split(/\s+/).slice(0, 3).map((t: string) =>
                                <span key={t} className="chip-neutral !text-[10px]">{t}</span>)}
                            </div>
                          )}
                        </div>
                      </Link>
                    ))}
                  </div>
                </>
              : <EmptyState icon={Shuffle} title="No neighbours returned"/>}
        </section>
      </div>
    </div>
  );
}
