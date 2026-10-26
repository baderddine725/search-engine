import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Search, Image as ImageIcon, Images, Database, Layers,
  Timer, Target, AlertTriangle, CheckCircle2, Loader2,
} from 'lucide-react';
import {
  Stats as StatsAPI, Health as HealthAPI, Models as ModelsAPI,
  Dataset as DatasetAPI, Benchmark as BenchAPI, Mirflickr,
  type StatsResponse, type ModelsResponse, type HealthResponse,
  type DatasetImage, type BenchmarkReport, type MirflickrStats,
  imageUrl,
} from '../lib/api';
import { PageHeader } from '../components/PageHeader';
import { StatCard } from '../components/StatCard';
import { fmt, fmtMs } from '../lib/utils';

export default function Overview() {
  const nav = useNavigate();
  const [query, setQuery] = useState('');
  const [stats, setStats] = useState<StatsResponse | null>(null);
  const [models, setModels] = useState<ModelsResponse | null>(null);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [mirStats, setMirStats] = useState<MirflickrStats | null>(null);
  const [bench, setBench] = useState<BenchmarkReport | null>(null);
  const [gallery, setGallery] = useState<DatasetImage[] | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const [h, m, s] = await Promise.all([
          HealthAPI.get().catch(() => null),
          ModelsAPI.list().catch(() => null),
          StatsAPI.get().catch(() => null),
        ]);
        if (!alive) return;
        setHealth(h); setModels(m); setStats(s);
        const extras = await Promise.all([
          DatasetAPI.images({ size: 12, random: true }).catch(() => null),
          BenchAPI.latest().catch(() => null),
          Mirflickr.stats().catch(() => null),
        ]);
        if (!alive) return;
        setGallery(extras[0]?.images ?? null);
        setBench(extras[1]);
        setMirStats(extras[2]);
      } finally {
        if (alive) setLoading(false);
      }
    })();
    return () => { alive = false; };
  }, []);

  const totalImages = stats
    ? Object.values(stats.models).reduce((a, b) => a + b.images, 0) /
      Math.max(Object.keys(stats.models).length, 1)
    : 0;
  const mapInception = bench?.models?.inception_lbp?.exact?.map;
  const latencyFromBench = bench?.models?.inception_lbp?.exact?.mean_query_ms
                       ?? bench?.models?.inception_lbp?.lsh?.mean_query_ms;

  return (
    <div className="space-y-10">
      <PageHeader
        eyebrow="VisionSearch AI"
        title="Intelligent Image Retrieval"
        subtitle="Combine semantic text search with deep visual similarity to discover the images you need."
      />

      {/* Hero search */}
      <section className="relative rounded-2xl overflow-hidden border border-ink-200 dark:border-ink-700
                          bg-gradient-to-br from-ink-900 via-ink-800 to-brand-900 text-white
                          p-6 sm:p-10">
        <div aria-hidden
             className="absolute inset-0 bg-grid-slate [background-size:48px_48px] opacity-[0.08]"/>
        <div aria-hidden
             className="absolute -top-24 -right-24 h-96 w-96 rounded-full
                        bg-gradient-to-br from-violet to-cyan opacity-20 blur-3xl"/>
        <div className="relative max-w-3xl">
          <div className="eyebrow !text-brand-300 mb-3">Unified search</div>
          <h2 className="font-display text-2xl sm:text-3xl font-semibold leading-tight tracking-tight">
            Search by meaning. <span className="text-brand-300">Discover</span> by vision.
          </h2>
          <p className="mt-3 text-ink-200 text-sm sm:text-base max-w-2xl">
            Type a query, upload a photo, or pick one from the dataset.
            Elasticsearch BM25 for text, Elastiknn vectors + VP-Trees for visual similarity.
          </p>

          <div className="mt-6 flex flex-col sm:flex-row gap-3">
            <div className="flex-1 flex items-center gap-2 bg-white/95 text-ink-900 rounded-xl p-2 pl-4">
              <Search size={16} className="text-ink-500"/>
              <input
                value={query} onChange={e => setQuery(e.target.value)}
                onKeyDown={e => { if (e.key === 'Enter' && query.trim())
                                     nav(`/text?q=${encodeURIComponent(query.trim())}`); }}
                placeholder="Try 'sunset over the beach' or 'red sports car'…"
                className="flex-1 bg-transparent outline-none text-sm py-2"/>
              <button className="btn-primary !py-2"
                      onClick={() => query.trim() && nav(`/text?q=${encodeURIComponent(query.trim())}`)}>
                Search by Text
              </button>
            </div>
            <button onClick={() => nav('/visual')}
                    className="inline-flex items-center justify-center gap-2 rounded-xl px-5 py-3
                               bg-white/10 border border-white/20 hover:bg-white/20 text-sm font-medium
                               backdrop-blur transition">
              <ImageIcon size={16}/> Search by Image
            </button>
          </div>

          <div className="mt-8 flex items-center gap-6 text-xs text-ink-200/80 font-mono">
            <span className="flex items-center gap-1.5">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400"/>
              BM25 · ES {health?.elasticsearch ?? '—'}
            </span>
            <span className="flex items-center gap-1.5">
              <span className="h-1.5 w-1.5 rounded-full bg-cyan"/>
              L2 LSH · Elastiknn
            </span>
            <span className="flex items-center gap-1.5">
              <span className="h-1.5 w-1.5 rounded-full bg-violet"/>
              VP-Tree L1
            </span>
          </div>
        </div>
      </section>

      {/* Statistics cards */}
      <section>
        <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-4">
          <StatCard label="Indexed images" icon={Images}
            value={loading ? '' : fmt(totalImages)} unit="objects"
            loading={loading} accent="brand"/>
          <StatCard label="Text documents" icon={Database}
            value={loading ? '' : fmt(stats?.text_documents ?? 0)} unit="BM25"
            loading={loading} accent="cyan"/>
          <StatCard label="Categories" icon={Layers}
            value={loading ? '' : Object.keys(stats?.classes ?? {}).length}
            unit="classes" loading={loading} accent="violet"/>
          <StatCard label="Feature models" icon={ImageIcon}
            value={loading ? '' : Object.keys(models?.models ?? {}).length}
            unit="available" loading={loading} accent="brand"/>
          <StatCard label="Avg query latency" icon={Timer}
            value={loading ? '' : fmtMs(latencyFromBench)}
            unit="per query" trend={bench ? 'offline benchmark' : undefined}
            loading={loading} accent="emerald"/>
          <StatCard label="Latest mAP" icon={Target}
            value={loading ? '' : mapInception !== undefined ? mapInception.toFixed(3) : '—'}
            unit="InceptionV3 + LBP"
            trend={bench?.generated_at
              ? new Date(bench.generated_at).toLocaleDateString() : 'no benchmark yet'}
            loading={loading} accent="violet"/>
        </div>
      </section>

      {/* Approach / service health side by side */}
      <section className="grid lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 card p-6">
          <div className="eyebrow mb-3">Feature extraction models</div>
          <div className="space-y-3">
            {Object.entries(models?.models ?? {}).map(([k, m]) => (
              <div key={k}
                   className="flex flex-col sm:flex-row sm:items-center gap-3 p-3 rounded-xl
                              border border-ink-200 dark:border-ink-700
                              bg-ink-50/50 dark:bg-ink-900/40">
                <div className="flex-1">
                  <div className="font-medium">{m.label}</div>
                  <div className="text-xs text-ink-500 dark:text-ink-400 mt-0.5">
                    {m.description}
                  </div>
                </div>
                <div className="flex items-center gap-4 text-xs font-mono tabular-nums">
                  <span className="text-ink-500 dark:text-ink-400">
                    dim <span className="text-ink-900 dark:text-ink-100">{m.dims}</span>
                  </span>
                  <span className="text-ink-500 dark:text-ink-400">
                    images <span className="text-ink-900 dark:text-ink-100">
                      {stats?.models[k]?.images ?? 0}
                    </span>
                  </span>
                  <span className="chip-brand">{k}</span>
                </div>
              </div>
            ))}
            {!models && !loading && (
              <div className="text-sm text-ink-500">Models endpoint unavailable.</div>
            )}
          </div>
        </div>

        <div className="card p-6">
          <div className="eyebrow mb-3">Service health</div>
          <ul className="space-y-2.5 text-sm">
            <HealthRow ok={health?.status === 'ok'} label="Flask API" sub={health?.status === 'ok' ? 'healthy' : 'unreachable'}/>
            <HealthRow ok={!!health?.elasticsearch} label="Elasticsearch" sub={health?.elasticsearch ?? '—'}/>
            <HealthRow ok={Object.values(stats?.models ?? {}).some(m => m.images > 0)}
              label="Vector search (Elastiknn)"
              sub={Object.values(stats?.models ?? {}).some(m => m.images > 0) ? 'indexed' : 'empty'}/>
            <HealthRow ok={!!stats?.models?.inception_lbp?.images}
              label="InceptionV3 + LBP"
              sub={`${stats?.models?.inception_lbp?.images ?? 0} images`}/>
            <HealthRow ok={!!stats?.models?.vgg16?.images}
              label="VGG16"
              sub={`${stats?.models?.vgg16?.images ?? 0} images`}/>
            <HealthRow ok={mirStats?.has_text}
              label="MIRFLICKR-1M"
              sub={mirStats?.has_text ? `${fmt(mirStats.indexed_documents)} docs` : 'not loaded'}/>
          </ul>
        </div>
      </section>

      {/* Dataset gallery */}
      <section>
        <div className="flex items-end justify-between mb-4">
          <div>
            <div className="eyebrow mb-1">Dataset preview</div>
            <h3 className="font-display text-xl font-semibold">A glimpse of the indexed collection</h3>
          </div>
          <button className="btn-secondary" onClick={() => nav('/dataset')}>
            Browse all →
          </button>
        </div>
        {gallery
          ? <div className="grid grid-cols-3 sm:grid-cols-4 lg:grid-cols-6 gap-3">
              {gallery.map(g => (
                <button key={g.image_path}
                        onClick={() => nav(`/similar?path=${encodeURIComponent(g.image_path)}`)}
                        className="group relative aspect-square rounded-lg overflow-hidden
                                   border border-ink-200 dark:border-ink-700 bg-ink-100 dark:bg-ink-900">
                  <img src={imageUrl(g.image_path)} loading="lazy" alt=""
                       className="h-full w-full object-cover transition-transform duration-300
                                  group-hover:scale-105"/>
                  <div className="absolute inset-x-0 bottom-0 p-1.5 text-[10px] text-white
                                  bg-gradient-to-t from-black/70 to-transparent text-left">
                    {g.class_name}
                  </div>
                </button>
              ))}
            </div>
          : <div className="grid grid-cols-6 gap-3">
              {Array.from({length:12}).map((_, i) =>
                <div key={i} className="skeleton aspect-square rounded-lg"/>
              )}
            </div>}
      </section>
    </div>
  );
}

function HealthRow({ ok, label, sub }: { ok?: boolean; label: string; sub?: string }) {
  return (
    <li className="flex items-center gap-3">
      {ok === undefined
        ? <Loader2 size={14} className="animate-spin text-ink-400"/>
        : ok ? <CheckCircle2 size={14} className="text-emerald-500"/>
             : <AlertTriangle size={14} className="text-amber-500"/>}
      <span className="flex-1">{label}</span>
      <span className="text-xs text-ink-500 dark:text-ink-400 font-mono">{sub}</span>
    </li>
  );
}
