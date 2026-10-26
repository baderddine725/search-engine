import { useEffect, useState } from 'react';
import { GitCompare, Database, Upload } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, LineChart, Line, CartesianGrid, Legend } from 'recharts';
import {
  Compare, Dataset, type CompareResponse, type DatasetImage,
  imageUrl,
} from '../lib/api';
import { PageHeader } from '../components/PageHeader';
import { EmptyState } from '../components/EmptyState';
import { cn, fmtMs } from '../lib/utils';

export default function ModelComparison() {
  const [library, setLibrary] = useState<DatasetImage[]>([]);
  const [path, setPath] = useState<string>('');
  const [size, setSize] = useState(10);
  const [data, setData] = useState<CompareResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => { Dataset.images({ size: 60, random: true }).then(r => setLibrary(r.images)); }, []);

  const run = () => {
    if (!path) return;
    setLoading(true); setErr(null); setData(null);
    Compare.byPath(path, size).then(setData).catch(e => setErr(e.message)).finally(() => setLoading(false));
  };

  const modelKeys = Object.keys(data?.models ?? {});
  const chartData = modelKeys.map(k => {
    const m = data!.models[k];
    return {
      model: m.label || k,
      precision: m.metrics?.precision ?? null,
      ap: m.metrics?.ap ?? null,
      search_ms: m.search_ms,
    };
  });
  const curveData = Array.from({ length: size }, (_, i) => ({
    rank: i + 1,
    ...Object.fromEntries(modelKeys.map(k => [k, data?.models[k]?.metrics?.curve?.[i] ?? null])),
  }));

  return (
    <div className="space-y-8">
      <PageHeader eyebrow="Research workspace"
                  title="Model comparison"
                  subtitle="Run the same query on both feature extractors side-by-side and inspect
                            per-request precision, ranking parity, and search latency."/>

      <div className="card p-4 lg:p-5">
        <div className="flex flex-col lg:flex-row lg:items-end gap-4">
          <div className="flex-1 min-w-0">
            <div className="eyebrow mb-2">Query image (dataset)</div>
            <div className="grid grid-cols-6 sm:grid-cols-10 gap-1.5 max-h-32 overflow-y-auto scrollbar-slim">
              {library.map(img =>
                <button key={img.image_path} onClick={() => setPath(img.image_path)}
                        className={cn('aspect-square rounded border-2 overflow-hidden',
                          path === img.image_path ? 'border-brand-500' : 'border-transparent hover:border-ink-300')}>
                  <img src={imageUrl(img.image_path)} className="h-full w-full object-cover" alt=""/>
                </button>)}
            </div>
          </div>
          <div className="flex items-center gap-3">
            <label className="text-xs text-ink-500 font-mono">Top-k</label>
            <input type="number" min={1} max={50} value={size}
                   onChange={e => setSize(Number(e.target.value))}
                   className="input !w-20 !py-1.5"/>
            <button onClick={run} className="btn-primary" disabled={!path || loading}>
              {loading ? 'Running…' : 'Compare'}
            </button>
          </div>
        </div>
      </div>

      {err && <EmptyState icon={GitCompare} title="Comparison failed" body={err}/>}

      {!data && !loading && !err &&
        <EmptyState icon={GitCompare} title="Pick an image and press Compare"
                    body="Both InceptionV3 + LBP and VGG16 will run on the same query."/>}

      {data && (
        <>
          <div className="grid lg:grid-cols-2 gap-6">
            {modelKeys.map(k => {
              const m = data.models[k];
              const relevant = m.metrics?.relevant ?? 0;
              return (
                <div key={k} className="card p-5">
                  <div className="flex items-center justify-between mb-4">
                    <div>
                      <div className="eyebrow mb-1">Model</div>
                      <div className="font-display text-lg font-semibold">{m.label}</div>
                    </div>
                    <div className="text-right text-xs font-mono text-ink-500">
                      <div>{fmtMs(m.search_ms)} search</div>
                      {m.extract_ms !== undefined && m.extract_ms > 0 && <div>{fmtMs(m.extract_ms)} extraction</div>}
                    </div>
                  </div>
                  {m.metrics && (
                    <div className="grid grid-cols-3 gap-3 mb-4">
                      <Metric label="Precision" value={(m.metrics.precision * 100).toFixed(1) + '%'}/>
                      <Metric label="AP" value={m.metrics.ap.toFixed(3)}/>
                      <Metric label="Relevant" value={`${relevant}/${size}`}/>
                    </div>
                  )}
                  <div className="grid grid-cols-5 gap-2">
                    {m.results.map((r, i) => (
                      <div key={r.image_path} className="relative aspect-square rounded-md overflow-hidden
                                                        border border-ink-200 dark:border-ink-700">
                        <img src={imageUrl(r.image_path)} alt="" loading="lazy"
                             className="h-full w-full object-cover"/>
                        <div className="absolute top-1 left-1 h-5 w-5 rounded bg-white/90 text-ink-900
                                        text-[10px] font-mono grid place-items-center">
                          {i + 1}
                        </div>
                        <div className={cn(
                          'absolute inset-x-0 bottom-0 text-center text-[9px] font-mono py-0.5 text-white',
                          data.query_class && r.class_name === data.query_class ? 'bg-emerald-500/90' :
                          data.query_class ? 'bg-red-500/90' : 'bg-ink-900/80'
                        )}>
                          {r.class_name}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>

          <div className="grid lg:grid-cols-2 gap-6">
            <div className="card p-5">
              <div className="eyebrow mb-2">Precision at rank</div>
              <div className="h-64">
                <ResponsiveContainer>
                  <LineChart data={curveData}>
                    <CartesianGrid stroke="var(--grid, #e5e7eb)" strokeDasharray="3 3"/>
                    <XAxis dataKey="rank" tick={{ fontSize: 11 }}/>
                    <YAxis domain={[0, 1]} tick={{ fontSize: 11 }}/>
                    <Tooltip/>
                    <Legend/>
                    {modelKeys.map((k, i) =>
                      <Line key={k} dataKey={k} stroke={i === 0 ? '#4f46e5' : '#06b6d4'}
                            strokeWidth={2} dot={false} name={data.models[k].label}/>)}
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="card p-5">
              <div className="eyebrow mb-2">Metrics</div>
              <div className="h-64">
                <ResponsiveContainer>
                  <BarChart data={chartData}>
                    <CartesianGrid stroke="#e5e7eb" strokeDasharray="3 3"/>
                    <XAxis dataKey="model" tick={{ fontSize: 11 }}/>
                    <YAxis tick={{ fontSize: 11 }}/>
                    <Tooltip/>
                    <Legend/>
                    <Bar dataKey="precision" fill="#4f46e5" name="Precision"/>
                    <Bar dataKey="ap"        fill="#06b6d4" name="AP"/>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>

          {data.overlap.length > 0 && (
            <div className="card p-5">
              <div className="eyebrow mb-2">Overlap</div>
              <div className="text-sm text-ink-600 dark:text-ink-300">
                {data.overlap.length} result(s) appear in both rankings.
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-ink-200 dark:border-ink-700 p-3">
      <div className="eyebrow">{label}</div>
      <div className="font-display text-xl font-semibold tabular-nums mt-0.5">{value}</div>
    </div>
  );
}
