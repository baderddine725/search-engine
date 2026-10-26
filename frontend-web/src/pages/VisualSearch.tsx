import { useEffect, useState } from 'react';
import { Upload, Link2, Image as ImageIcon, Database, Zap, X } from 'lucide-react';
import {
  Search, Models, Dataset, type ModelsResponse, type ImageSearchResponse,
  type DatasetImage, imageUrl,
} from '../lib/api';
import { PageHeader } from '../components/PageHeader';
import { ImageCard } from '../components/ImageCard';
import { EmptyState } from '../components/EmptyState';
import { LoadingGrid } from '../components/LoadingGrid';
import { cn, fmtMs } from '../lib/utils';

type Mode = 'upload' | 'url' | 'dataset';

export default function VisualSearch() {
  const [mode, setMode] = useState<Mode>('dataset');
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [url, setUrl] = useState('');
  const [path, setPath] = useState<string>('');
  const [classes, setClasses] = useState<string[]>([]);
  const [classFilter, setClassFilter] = useState<string>('');
  const [library, setLibrary] = useState<DatasetImage[]>([]);
  const [models, setModels] = useState<ModelsResponse | null>(null);
  const [model, setModel] = useState<string>('inception_lbp');
  const [size, setSize] = useState(10);
  const [result, setResult] = useState<ImageSearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Models.list().then(r => { setModels(r); setModel(r.default); }).catch(() => {});
    Dataset.images({ size: 500 }).then(r => {
      setLibrary(r.images);
      const uniq = Array.from(new Set(r.images.map(i => i.class_name))).sort();
      setClasses(uniq);
      if (uniq.length) setClassFilter(uniq[0]);
    }).catch(() => {});
  }, []);

  const pick = (f: File) => {
    setFile(f);
    const r = new FileReader();
    r.onload = () => setPreview(r.result as string);
    r.readAsDataURL(f);
  };

  const run = async () => {
    try {
      setLoading(true); setError(null); setResult(null);
      if (mode === 'upload' && file) setResult(await Search.image(file, model, size));
      else if (mode === 'url' && url.trim()) setResult(await Search.url(url.trim(), model, size));
      else if (mode === 'dataset' && path) setResult(await Search.similar(path, model, size));
      else throw new Error('Provide a query image first.');
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const queryPreview = mode === 'upload' ? preview
                     : mode === 'url' ? (url.trim() || null)
                     : path ? imageUrl(path) : null;

  const filtered = classFilter
    ? library.filter(l => l.class_name === classFilter)
    : library;

  return (
    <div className="space-y-8">
      <PageHeader eyebrow="Content-based retrieval"
                  title="Visual search workspace"
                  subtitle="Provide a query image — upload, URL, or dataset pick — and retrieve
                            the visually closest images using deep features."/>

      <div className="grid lg:grid-cols-[380px_1fr] gap-6">
        {/* Query controls */}
        <aside className="space-y-5">
          <div className="card p-4">
            <div className="eyebrow mb-3">Query source</div>
            <div className="grid grid-cols-3 gap-1.5 p-1 bg-ink-100 dark:bg-ink-900 rounded-lg">
              {([
                { k: 'dataset', l: 'Dataset', I: Database },
                { k: 'upload',  l: 'Upload',  I: Upload   },
                { k: 'url',     l: 'URL',     I: Link2    },
              ] as const).map(m =>
                <button key={m.k}
                        onClick={() => setMode(m.k)}
                        className={cn(
                          'flex items-center justify-center gap-1.5 py-2 text-xs font-medium rounded-md transition',
                          mode === m.k
                            ? 'bg-white dark:bg-ink-700 text-ink-900 dark:text-white shadow-sm'
                            : 'text-ink-500 dark:text-ink-400 hover:text-ink-800'
                        )}>
                  <m.I size={12}/>{m.l}
                </button>)}
            </div>

            {mode === 'upload' && (
              <div className="mt-4">
                <label className="block border-2 border-dashed border-ink-300 dark:border-ink-600
                                  rounded-xl p-6 text-center hover:border-brand-400
                                  transition cursor-pointer">
                  <input type="file" className="hidden" accept="image/*"
                         onChange={e => e.target.files?.[0] && pick(e.target.files[0])}/>
                  <Upload className="mx-auto mb-2 text-ink-400" size={22}/>
                  <div className="text-sm font-medium">Drop or click to upload</div>
                  <div className="text-xs text-ink-500 mt-1">PNG, JPG up to 16 MB</div>
                </label>
                {file && (
                  <div className="mt-2 flex items-center justify-between text-xs text-ink-600 dark:text-ink-300">
                    <span className="font-mono truncate">{file.name}</span>
                    <button onClick={() => { setFile(null); setPreview(null); }}
                            className="btn-ghost !p-1"><X size={12}/></button>
                  </div>
                )}
              </div>
            )}

            {mode === 'url' && (
              <input value={url} onChange={e => setUrl(e.target.value)}
                     placeholder="https://example.com/photo.jpg"
                     className="input mt-4"/>
            )}

            {mode === 'dataset' && (
              <div className="mt-4 space-y-2">
                <select value={classFilter} onChange={e => setClassFilter(e.target.value)}
                        className="input">
                  <option value="">All classes</option>
                  {classes.map(c => <option key={c} value={c}>{c}</option>)}
                </select>
                <div className="grid grid-cols-4 gap-1.5 max-h-56 overflow-y-auto scrollbar-slim
                                p-0.5 rounded-lg">
                  {filtered.slice(0, 60).map(img =>
                    <button key={img.image_path}
                            onClick={() => setPath(img.image_path)}
                            className={cn(
                              'aspect-square rounded-md overflow-hidden border-2 transition',
                              path === img.image_path
                                ? 'border-brand-500 ring-2 ring-brand-500/30'
                                : 'border-transparent hover:border-ink-300')}>
                      <img src={imageUrl(img.image_path)} loading="lazy" alt=""
                           className="h-full w-full object-cover"/>
                    </button>)}
                </div>
              </div>
            )}
          </div>

          <div className="card p-4">
            <div className="eyebrow mb-3">Model</div>
            <div className="space-y-2">
              {Object.entries(models?.models ?? {}).map(([k, m]) => (
                <label key={k}
                       className={cn(
                         'flex items-start gap-2 p-3 rounded-lg border cursor-pointer transition',
                         model === k ? 'border-brand-400 bg-brand-50 dark:bg-brand-500/5'
                                     : 'border-ink-200 dark:border-ink-700 hover:border-ink-300')}>
                  <input type="radio" checked={model === k}
                         onChange={() => setModel(k)}
                         className="mt-1 accent-brand-500"/>
                  <div>
                    <div className="font-medium text-sm">{m.label}</div>
                    <div className="text-[11px] text-ink-500 mt-0.5">{m.description}</div>
                    <div className="text-[10px] font-mono text-ink-400 mt-0.5">
                      {m.dims} dims · index {m.index}
                    </div>
                  </div>
                </label>
              ))}
            </div>
          </div>

          <div className="card p-4">
            <div className="flex items-center justify-between">
              <div className="eyebrow">Results</div>
              <span className="font-mono text-sm">{size}</span>
            </div>
            <input type="range" min={1} max={50} value={size}
                   onChange={e => setSize(Number(e.target.value))}
                   className="w-full accent-brand-500 mt-2"/>
          </div>

          <button onClick={run} disabled={loading}
                  className="btn-primary w-full !py-3">
            {loading ? 'Searching…' : 'Run visual search →'}
          </button>
        </aside>

        {/* Query preview + results */}
        <section className="space-y-6">
          {queryPreview && (
            <div className="card p-4">
              <div className="flex items-center gap-4">
                <img src={queryPreview} alt="query"
                     className="h-24 w-24 object-cover rounded-lg border border-ink-200"/>
                <div className="flex-1 min-w-0">
                  <div className="eyebrow mb-1">Query image</div>
                  <div className="font-mono text-xs truncate">
                    {mode === 'dataset' ? path : mode === 'upload' ? file?.name : url}
                  </div>
                  {result && (
                    <div className="mt-2 flex items-center gap-4 text-xs text-ink-500 font-mono">
                      <span className="flex items-center gap-1">
                        <Zap size={10}/>{fmtMs(result.search_ms)} search
                      </span>
                      {result.extract_ms !== undefined && result.extract_ms > 0 && (
                        <span>{fmtMs(result.extract_ms)} extraction</span>
                      )}
                      <span className="chip-brand">{result.model}</span>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {error && <EmptyState icon={ImageIcon} title="Search failed" body={error}/>}
          {loading && <LoadingGrid n={size > 10 ? 10 : size}/>}
          {!loading && !error && !result &&
            <EmptyState icon={ImageIcon} title="Pick a query image"
                        body="Choose from the dataset on the left, upload a photo, or paste an image URL,
                              then run the search."/>}
          {result && !loading && (
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 2xl:grid-cols-5 gap-4">
              {result.results.map((r, i) =>
                <ImageCard key={r.image_path} path={r.image_path}
                           className={r.class_name} rank={i + 1}
                           score={r.score} distance={r.distance ?? undefined}/>
              )}
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
