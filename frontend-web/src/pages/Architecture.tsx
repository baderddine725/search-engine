import { PageHeader } from '../components/PageHeader';

export default function Architecture() {
  return (
    <div className="space-y-8">
      <PageHeader eyebrow="System" title="Architecture"
                  subtitle="How a request flows through the search engine, and what powers each stage."/>

      <div className="card p-6 overflow-x-auto">
        <svg viewBox="0 0 1000 580" className="w-full h-auto min-w-[760px]">
          <defs>
            <marker id="arr" viewBox="0 0 10 10" refX="9" refY="5"
                    markerWidth="7" markerHeight="7" orient="auto-start-reverse">
              <path d="M 0 0 L 10 5 L 0 10 z" fill="#4f46e5"/>
            </marker>
            <linearGradient id="brand" x1="0" x2="1">
              <stop offset="0%" stopColor="#4f46e5"/>
              <stop offset="100%" stopColor="#06b6d4"/>
            </linearGradient>
          </defs>

          {/* Client */}
          <Node x={420} y={20} w={160} h={54} fill="url(#brand)" label="Browser · User"
                sub="React + Tailwind UI"/>

          {/* Frontend */}
          <Node x={200} y={110} w={200} h={54} fill="#111827" label="VisionSearch AI"
                sub="React / Vite · this app"/>
          <Node x={600} y={110} w={200} h={54} fill="#4b5563" label="Streamlit UI"
                sub="original interface (still live)"/>

          <Arrow x1={500} y1={74}  x2={300} y2={110}/>
          <Arrow x1={500} y1={74}  x2={700} y2={110}/>

          {/* Flask API */}
          <Node x={370} y={210} w={260} h={66} fill="#1b2238"
                label="Flask REST API"
                sub="CORS · JSON · /health /search /compare /benchmark …"/>

          <Arrow x1={300} y1={164} x2={450} y2={210}/>
          <Arrow x1={700} y1={164} x2={550} y2={210}/>

          {/* Services */}
          <Node x={60}  y={330} w={200} h={56} fill="#4f46e5" label="Text Retrieval"
                sub="BM25 — Elasticsearch index"/>
          <Node x={290} y={330} w={200} h={56} fill="#4f46e5" label="Feature extraction"
                sub="InceptionV3 + LBP · VGG16"/>
          <Node x={520} y={330} w={200} h={56} fill="#4f46e5" label="Vector retrieval"
                sub="Elastiknn LSH · VP-Tree L1"/>
          <Node x={750} y={330} w={200} h={56} fill="#4f46e5" label="Benchmark engine"
                sub="precision@k · mAP · P@1"/>

          <Arrow x1={430} y1={276} x2={160} y2={330}/>
          <Arrow x1={470} y1={276} x2={390} y2={330}/>
          <Arrow x1={520} y1={276} x2={620} y2={330}/>
          <Arrow x1={560} y1={276} x2={850} y2={330}/>

          {/* Data layer */}
          <Node x={60}  y={450} w={260} h={58} fill="#0f172a"
                label="Elasticsearch 7.17.9"
                sub="flickrphotos · mirflickr · images_*"/>
          <Node x={360} y={450} w={260} h={58} fill="#0f172a"
                label="Image files + CSV features"
                sub="data/bdimage · features.csv"/>
          <Node x={660} y={450} w={290} h={58} fill="#0f172a"
                label="MIRFLICKR-1M + MPEG-7 memmaps"
                sub="edge.npy · homo.npy · *_vptree.npz"/>

          <Arrow x1={160} y1={386} x2={160} y2={450}/>
          <Arrow x1={390} y1={386} x2={420} y2={450}/>
          <Arrow x1={620} y1={386} x2={600} y2={450}/>
          <Arrow x1={850} y1={386} x2={800} y2={450}/>

          {/* Legend */}
          <g transform="translate(40,550)">
            <rect width="12" height="12" fill="#4f46e5" rx="2"/>
            <text x="20" y="10" fontSize="11" fill="#64748b">Service</text>
            <rect x="90"  width="12" height="12" fill="#0f172a" rx="2"/>
            <text x="110" y="10" fontSize="11" fill="#64748b">Data store</text>
            <rect x="190" width="12" height="12" fill="#111827" rx="2"/>
            <text x="210" y="10" fontSize="11" fill="#64748b">Frontend</text>
          </g>
        </svg>
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        <Pipeline title="Text pipeline"
                  steps={[
                    'Query hits /search/text',
                    'Elasticsearch BM25 over title ×3, tags ×2, description',
                    'Fuzzy tolerance = AUTO · highlighted snippets',
                    'JSON returned to the client in milliseconds',
                  ]}/>
        <Pipeline title="Visual pipeline"
                  steps={[
                    'Image uploaded, pulled from URL, or picked from the dataset',
                    'InceptionV3 + LBP (2058 dims) or VGG16 (512 dims) extracts features',
                    'Elastiknn L2 LSH approximate search over the vector index',
                    'Top-k returned with distances; same request can be sent to both models for comparison',
                  ]}/>
        <Pipeline title="Benchmark pipeline"
                  steps={[
                    'Each indexed image is used as its own query (minus itself)',
                    'Precision@k, mAP, P@1 computed over all queries',
                    'Measured in both exact and LSH modes for fairness',
                    'Report saved to data/benchmark.json and served by /benchmark',
                  ]}/>
      </div>
    </div>
  );
}

function Node(p: { x: number; y: number; w: number; h: number;
                   fill: string; label: string; sub?: string }) {
  return (
    <g>
      <rect x={p.x} y={p.y} width={p.w} height={p.h} rx={10} fill={p.fill}
            stroke="rgba(255,255,255,.08)"/>
      <text x={p.x + p.w / 2} y={p.y + p.h / 2 - 4} textAnchor="middle"
            fontSize="13" fontWeight="600" fill="white">{p.label}</text>
      {p.sub && (
        <text x={p.x + p.w / 2} y={p.y + p.h / 2 + 12} textAnchor="middle"
              fontSize="10" fill="rgba(255,255,255,.75)">{p.sub}</text>
      )}
    </g>
  );
}
function Arrow({ x1, y1, x2, y2 }: { x1: number; y1: number; x2: number; y2: number }) {
  return <path d={`M ${x1} ${y1} L ${x2} ${y2}`}
               stroke="#94a3b8" strokeWidth={1.4} fill="none"
               markerEnd="url(#arr)"/>;
}
function Pipeline({ title, steps }: { title: string; steps: string[] }) {
  return (
    <div className="card p-5">
      <div className="font-display text-lg font-semibold">{title}</div>
      <ol className="mt-3 space-y-2.5">
        {steps.map((s, i) => (
          <li key={i} className="flex gap-3 text-sm">
            <span className="h-5 w-5 shrink-0 rounded-full bg-brand-50 dark:bg-brand-500/10
                             text-brand-700 dark:text-brand-300 text-[11px] font-mono
                             flex items-center justify-center">{i + 1}</span>
            <span className="text-ink-700 dark:text-ink-200">{s}</span>
          </li>
        ))}
      </ol>
    </div>
  );
}
