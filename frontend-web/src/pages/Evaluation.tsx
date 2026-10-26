import { useEffect, useState } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  LineChart, Line, CartesianGrid, Legend,
} from 'recharts';
import { Play, Download, BarChart3 } from 'lucide-react';
import { Benchmark, type BenchmarkReport } from '../lib/api';
import { PageHeader } from '../components/PageHeader';
import { EmptyState } from '../components/EmptyState';
import { fmtMs } from '../lib/utils';

export default function Evaluation() {
  const [data, setData] = useState<BenchmarkReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [k, setK] = useState(10);
  const [perClass, setPerClass] = useState(20);
  const [err, setErr] = useState<string | null>(null);

  const load = () => Benchmark.latest().then(setData).catch(() => setData(null));

  useEffect(() => { setLoading(true); load().finally(() => setLoading(false)); }, []);

  const run = async () => {
    if (!confirm(`Run the benchmark with k=${k}, per_class=${perClass}? ` +
                 'This can take several minutes and will replace the saved report.')) return;
    setRunning(true); setErr(null);
    try {
      const r = await Benchmark.run({ k, per_class: perClass });
      setData(r);
    } catch (e: any) { setErr(e.message); } finally { setRunning(false); }
  };

  const download = () => {
    if (!data) return;
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = `benchmark-${data.generated_at.slice(0, 10)}.json`;
    a.click(); URL.revokeObjectURL(url);
  };

  const models = Object.keys(data?.models ?? {});
  const curveLen = Math.max(0, ...models.flatMap(m =>
    [data?.models[m].exact?.curve?.length ?? 0, data?.models[m].lsh?.curve?.length ?? 0]));
  const curve = Array.from({ length: curveLen }, (_, i) => ({
    rank: i + 1,
    ...Object.fromEntries(models.flatMap(m => [
      [`${m}_exact`, data?.models[m].exact?.curve?.[i] ?? null],
      [`${m}_lsh`, (data?.models[m].lsh ?? data?.models[m].approx)?.curve?.[i] ?? null],
    ])),
  }));

  const metricBars = models.map(m => ({
    model: m,
    'mAP exact':  data?.models[m].exact?.map ?? null,
    'P@1 exact':  data?.models[m].exact?.p_at_1 ?? null,
    'mAP LSH':   (data?.models[m].lsh ?? data?.models[m].approx)?.map ?? null,
    'P@1 LSH':   (data?.models[m].lsh ?? data?.models[m].approx)?.p_at_1 ?? null,
  }));

  const perClassBars = (() => {
    if (!models.length) return [];
    const classes = Object.keys(data?.classes ?? {});
    return classes.map(c => ({
      class: c,
      ...Object.fromEntries(models.map(m => [
        m, data?.models[m].exact?.per_class?.[c]?.ap ?? null,
      ])),
    }));
  })();

  return (
    <div className="space-y-8">
      <PageHeader eyebrow="Analytics" title="Evaluation & benchmarks"
                  subtitle="Quantitative evaluation of each model: precision@k, mAP, P@1,
                            per-class AP and latency. Results come straight from the backend
                            benchmark job — no synthetic numbers."
                  actions={
                    <>
                      <button className="btn-secondary" onClick={download} disabled={!data}>
                        <Download size={14}/> JSON
                      </button>
                      <button className="btn-primary" onClick={run} disabled={running}>
                        <Play size={14}/>{running ? 'Running…' : 'Run benchmark'}
                      </button>
                    </>
                  }/>

      <div className="card p-5 flex flex-wrap items-end gap-4">
        <div>
          <div className="eyebrow mb-1.5">Top-k</div>
          <input type="number" min={1} max={50} value={k} onChange={e => setK(Number(e.target.value))}
                 className="input !w-24"/>
        </div>
        <div>
          <div className="eyebrow mb-1.5">Queries per class</div>
          <input type="number" min={0} max={500} value={perClass}
                 onChange={e => setPerClass(Number(e.target.value))}
                 className="input !w-28"/>
          <div className="text-[10px] text-ink-500 mt-1 font-mono">0 = every image</div>
        </div>
        <div className="flex-1"/>
        {data?.generated_at && (
          <div className="text-xs font-mono text-ink-500">
            report generated {new Date(data.generated_at).toLocaleString()}
          </div>
        )}
      </div>

      {loading
        ? <div className="skeleton h-80 rounded-xl"/>
        : err ? <EmptyState icon={BarChart3} title="Benchmark failed" body={err}/>
        : !data
          ? <EmptyState icon={BarChart3} title="No benchmark yet"
                        body="Press Run benchmark to generate one. It can take several minutes
                              depending on dataset size."/>
          : (
          <>
            <div className="grid lg:grid-cols-2 gap-6">
              {models.map(m => {
                const ex = data.models[m].exact;
                const lsh = data.models[m].lsh ?? data.models[m].approx;
                return (
                  <div key={m} className="card p-5">
                    <div className="flex items-center justify-between mb-4">
                      <div>
                        <div className="eyebrow mb-1">Model</div>
                        <div className="font-display text-lg font-semibold">{m}</div>
                        <div className="text-xs font-mono text-ink-500">
                          {data.models[m].dims} dims
                        </div>
                      </div>
                      {data.models[m].extraction && (
                        <div className="text-xs font-mono text-ink-500 text-right">
                          <div>{fmtMs(data.models[m].extraction!.per_image_ms)} / image extract</div>
                          <div>{data.models[m].extraction!.images} images</div>
                        </div>
                      )}
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                      <Group label="Exact search" ev={ex} k={data.k}/>
                      <Group label="LSH approx."  ev={lsh} k={data.k}/>
                    </div>
                  </div>
                );
              })}
            </div>

            <div className="card p-5">
              <div className="eyebrow mb-2">Precision at rank</div>
              <div className="h-72">
                <ResponsiveContainer>
                  <LineChart data={curve}>
                    <CartesianGrid stroke="#e5e7eb" strokeDasharray="3 3"/>
                    <XAxis dataKey="rank" tick={{ fontSize: 11 }}/>
                    <YAxis domain={[0, 1]} tick={{ fontSize: 11 }}/>
                    <Tooltip/>
                    <Legend/>
                    {models.flatMap((m, i) => [
                      <Line key={m + 'ex'} dataKey={`${m}_exact`}
                            stroke={i === 0 ? '#4f46e5' : '#06b6d4'} strokeWidth={2}
                            dot={false} name={`${m} · exact`}/>,
                      <Line key={m + 'lsh'} dataKey={`${m}_lsh`}
                            stroke={i === 0 ? '#8b5cf6' : '#10b981'} strokeDasharray="4 3"
                            strokeWidth={2} dot={false} name={`${m} · LSH`}/>,
                    ])}
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="grid lg:grid-cols-2 gap-6">
              <div className="card p-5">
                <div className="eyebrow mb-2">Headline metrics</div>
                <div className="h-72">
                  <ResponsiveContainer>
                    <BarChart data={metricBars}>
                      <CartesianGrid stroke="#e5e7eb" strokeDasharray="3 3"/>
                      <XAxis dataKey="model" tick={{ fontSize: 11 }}/>
                      <YAxis tick={{ fontSize: 11 }}/>
                      <Tooltip/>
                      <Legend/>
                      <Bar dataKey="mAP exact" fill="#4f46e5"/>
                      <Bar dataKey="P@1 exact" fill="#06b6d4"/>
                      <Bar dataKey="mAP LSH" fill="#8b5cf6"/>
                      <Bar dataKey="P@1 LSH" fill="#10b981"/>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
              <div className="card p-5">
                <div className="eyebrow mb-2">Per-class AP (exact)</div>
                <div className="h-72">
                  <ResponsiveContainer>
                    <BarChart data={perClassBars}>
                      <CartesianGrid stroke="#e5e7eb" strokeDasharray="3 3"/>
                      <XAxis dataKey="class" tick={{ fontSize: 11 }}/>
                      <YAxis domain={[0, 1]} tick={{ fontSize: 11 }}/>
                      <Tooltip/>
                      <Legend/>
                      {models.map((m, i) =>
                        <Bar key={m} dataKey={m} fill={i === 0 ? '#4f46e5' : '#06b6d4'} name={m}/>
                      )}
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>
          </>
        )}
    </div>
  );
}

function Group({ label, ev, k }: { label: string; ev?: any; k: number }) {
  if (!ev) return (
    <div className="rounded-lg border border-dashed border-ink-200 dark:border-ink-700 p-4 text-center
                    text-xs text-ink-500">{label} unavailable</div>
  );
  return (
    <div className="rounded-lg border border-ink-200 dark:border-ink-700 p-3 space-y-1.5">
      <div className="eyebrow">{label}</div>
      <Row k="mAP"      v={ev.map?.toFixed(3)}/>
      <Row k="P@1"      v={ev.p_at_1?.toFixed(3)}/>
      <Row k={`P@${k}`} v={ev.precision?.toFixed(3)}/>
      <Row k="latency"  v={fmtMs(ev.mean_query_ms)}/>
    </div>
  );
}
function Row({ k, v }: { k: string; v?: any }) {
  return (
    <div className="flex items-center justify-between text-xs">
      <span className="text-ink-500 dark:text-ink-400">{k}</span>
      <span className="font-mono tabular-nums font-medium">{v ?? '—'}</span>
    </div>
  );
}
