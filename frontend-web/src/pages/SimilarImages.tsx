import { useEffect, useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { Shuffle, ChevronRight, ArrowLeftCircle } from 'lucide-react';
import { Search, Models, type ImageSearchResponse, type ModelsResponse,
         imageUrl } from '../lib/api';
import { PageHeader } from '../components/PageHeader';
import { ImageCard } from '../components/ImageCard';
import { LoadingGrid } from '../components/LoadingGrid';
import { EmptyState } from '../components/EmptyState';
import { classFromPath, fmtMs } from '../lib/utils';

export default function SimilarImages() {
  const [sp, setSp] = useSearchParams();
  const nav = useNavigate();
  const path = sp.get('path') ?? '';
  const [model, setModel] = useState<string>(sp.get('model') ?? 'inception_lbp');
  const [size, setSize] = useState<number>(Number(sp.get('size') ?? 12));
  const [data, setData] = useState<ImageSearchResponse | null>(null);
  const [models, setModels] = useState<ModelsResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [history, setHistory] = useState<string[]>([]);

  useEffect(() => { Models.list().then(setModels).catch(() => {}); }, []);

  useEffect(() => {
    if (!path) { setData(null); return; }
    setLoading(true); setError(null);
    Search.similar(path, model, size)
      .then(d => { setData(d); setHistory(h => h[h.length - 1] === path ? h : [...h, path]); })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, [path, model, size]);

  const open = (p: string) => setSp({ path: p, model, size: String(size) });
  const back = () => {
    const prev = history.slice(0, -1);
    const prevPath = prev[prev.length - 1];
    setHistory(prev);
    if (prevPath) setSp({ path: prevPath, model, size: String(size) });
  };

  return (
    <div className="space-y-8">
      <PageHeader eyebrow="Iterative discovery"
                  title="Similar images"
                  subtitle="Click any result to pivot the search. Your discovery path appears below."/>

      {history.length > 0 && (
        <div className="card p-3 flex items-center gap-2 flex-wrap">
          <button onClick={back} disabled={history.length < 2}
                  className="btn-ghost !py-1 !px-2 text-xs">
            <ArrowLeftCircle size={14}/> Back
          </button>
          <div className="h-5 w-px bg-ink-200 dark:bg-ink-700"/>
          {history.map((p, i) => (
            <div key={i} className="flex items-center gap-2">
              {i > 0 && <ChevronRight size={12} className="text-ink-400"/>}
              <button onClick={() => open(p)}
                      className="flex items-center gap-1.5 text-xs font-mono text-ink-600 dark:text-ink-300
                                 hover:text-brand-600">
                <img src={imageUrl(p)} className="h-6 w-6 object-cover rounded" alt=""/>
                <span className="truncate max-w-[160px]">{classFromPath(p)}</span>
              </button>
            </div>
          ))}
        </div>
      )}

      {!path
        ? <EmptyState icon={Shuffle} title="Start from any image"
                      body="Open an image from a search, the dataset, or Visual Search, then come back here."
                      action={<button onClick={() => nav('/dataset')} className="btn-primary">
                                Browse dataset →
                              </button>}/>
        : <div className="grid lg:grid-cols-[320px_1fr] gap-6">
            <aside className="space-y-5">
              <div className="card overflow-hidden">
                <img src={imageUrl(path)} alt={path}
                     className="w-full aspect-square object-cover"/>
                <div className="p-4">
                  <div className="eyebrow mb-1">Query</div>
                  <div className="font-mono text-xs truncate">{path}</div>
                  <div className="mt-2">
                    <span className="chip-brand">{classFromPath(path)}</span>
                  </div>
                </div>
              </div>

              <div className="card p-4">
                <div className="eyebrow mb-2">Model</div>
                <div className="space-y-1.5">
                  {Object.entries(models?.models ?? {}).map(([k, m]) =>
                    <button key={k} onClick={() => setModel(k)}
                            className={`w-full text-left p-2.5 rounded-lg border text-sm transition ${
                              model === k ? 'border-brand-400 bg-brand-50 dark:bg-brand-500/5'
                                          : 'border-ink-200 dark:border-ink-700 hover:border-ink-300'}`}>
                      <div className="font-medium">{m.label}</div>
                      <div className="text-xs text-ink-500 font-mono mt-0.5">{m.dims} dims</div>
                    </button>)}
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

              {data && (
                <div className="text-xs font-mono text-ink-500 flex items-center justify-between">
                  <span>{data.count} results</span>
                  <span>{fmtMs(data.search_ms)}</span>
                </div>
              )}
            </aside>

            <section>
              {loading ? <LoadingGrid n={size}/>
                : error ? <EmptyState icon={Shuffle} title="Failed" body={error}/>
                : data && (
                  <div className="grid grid-cols-2 sm:grid-cols-3 xl:grid-cols-4 gap-4">
                    {data.results.map((r, i) =>
                      <ImageCard key={r.image_path} path={r.image_path}
                                 className={r.class_name} rank={i + 1}
                                 score={r.score} distance={r.distance ?? undefined}
                                 onSelect={open}/>)}
                  </div>
                )}
            </section>
          </div>}
    </div>
  );
}
