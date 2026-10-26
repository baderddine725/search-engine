import { useState } from 'react';
import { Copy, Check } from 'lucide-react';
import { PageHeader } from '../components/PageHeader';
import { API_BASE } from '../lib/api';
import { cn } from '../lib/utils';

type Endpoint = {
  method: 'GET' | 'POST';
  path: string;
  summary: string;
  params?: Array<{ name: string; type: string; where: string; note?: string }>;
  example: string;
  response?: string;
};

const endpoints: Endpoint[] = [
  { method: 'GET', path: '/health', summary: 'Service health check.',
    example: `curl ${API_BASE}/health`,
    response: `{ "status": "ok", "elasticsearch": "7.17.9" }` },
  { method: 'GET', path: '/models', summary: 'List registered CBIR models.',
    example: `curl ${API_BASE}/models`,
    response: `{ "default": "inception_lbp", "models": { ... } }` },
  { method: 'GET', path: '/stats', summary: 'Index sizes, class counts, benchmark availability.',
    example: `curl ${API_BASE}/stats` },
  { method: 'GET', path: '/search/text', summary: 'BM25 text search over Flickr metadata.',
    params: [
      { name: 'q', type: 'string', where: 'query', note: 'required' },
      { name: 'size', type: 'int', where: 'query', note: '1–100, default 10' },
    ],
    example: `curl "${API_BASE}/search/text?q=sunset+beach&size=5"` },
  { method: 'POST', path: '/search/image', summary: 'Visual search from an uploaded image.',
    params: [
      { name: 'image', type: 'file', where: 'multipart', note: 'required' },
      { name: 'model', type: 'string', where: 'multipart' },
      { name: 'size',  type: 'int', where: 'multipart' },
    ],
    example: `curl -X POST ${API_BASE}/search/image \\
  -F "image=@photo.jpg" -F "model=inception_lbp" -F "size=10"` },
  { method: 'POST', path: '/search/url', summary: 'Visual search from an image URL.',
    params: [
      { name: 'url', type: 'string', where: 'json', note: 'required' },
      { name: 'model', type: 'string', where: 'json' },
      { name: 'size', type: 'int', where: 'json' },
    ],
    example: `curl -X POST ${API_BASE}/search/url \\
  -H "Content-Type: application/json" \\
  -d '{"url":"https://example.com/p.jpg","model":"vgg16","size":10}'` },
  { method: 'GET', path: '/search/similar', summary: 'Visual search starting from an indexed image.',
    params: [
      { name: 'path', type: 'string', where: 'query', note: 'required · e.g. "roses/123.jpg"' },
      { name: 'model', type: 'string', where: 'query' },
      { name: 'size', type: 'int', where: 'query' },
    ],
    example: `curl "${API_BASE}/search/similar?path=roses/123.jpg&model=inception_lbp&size=10"` },
  { method: 'POST', path: '/compare', summary: 'Run the same query on every model.',
    params: [
      { name: 'path', type: 'string', where: 'json/form', note: 'or image/url' },
      { name: 'image', type: 'file', where: 'multipart' },
      { name: 'url', type: 'string', where: 'json' },
      { name: 'size', type: 'int', where: 'json/form' },
      { name: 'query_class', type: 'string', where: 'json/form', note: 'for metrics' },
    ],
    example: `curl -X POST ${API_BASE}/compare -d "path=roses/123.jpg" -d "size=10"` },
  { method: 'GET', path: '/benchmark', summary: 'Latest saved evaluation report.',
    example: `curl ${API_BASE}/benchmark` },
  { method: 'POST', path: '/benchmark/run', summary: 'Recompute the benchmark.',
    params: [
      { name: 'k', type: 'int', where: 'json', note: 'top-k, default 10' },
      { name: 'per_class', type: 'int', where: 'json', note: '0 = every image' },
      { name: 'candidates', type: 'int', where: 'json' },
    ],
    example: `curl -X POST ${API_BASE}/benchmark/run \\
  -H "Content-Type: application/json" -d '{"k":10,"per_class":20}'` },
  { method: 'GET', path: '/dataset/images', summary: 'Browse indexed images.',
    params: [
      { name: 'class', type: 'string', where: 'query' },
      { name: 'size',  type: 'int', where: 'query' },
      { name: 'random', type: '0|1', where: 'query' },
    ],
    example: `curl "${API_BASE}/dataset/images?size=20&random=1"` },
  { method: 'GET', path: '/images/{path}', summary: 'Serves a raw dataset image file.',
    example: `curl ${API_BASE}/images/roses/123.jpg` },
  { method: 'POST', path: '/init', summary: 'Create empty Elasticsearch indexes (first run).',
    example: `curl -X POST ${API_BASE}/init` },
];

export default function ApiDocs() {
  const [active, setActive] = useState(0);
  return (
    <div className="space-y-6">
      <PageHeader eyebrow="Developer" title="API reference"
                  subtitle={`Base URL: ${API_BASE}. All endpoints return JSON unless otherwise noted;
                             CORS is enabled for cross-origin calls from this app.`}/>
      <div className="grid lg:grid-cols-[260px_1fr] gap-6">
        <nav className="card p-2 lg:sticky lg:top-20 h-fit">
          <ul className="space-y-0.5">
            {endpoints.map((e, i) =>
              <li key={e.method + e.path}>
                <button onClick={() => setActive(i)}
                        className={cn(
                          'w-full text-left px-3 py-2 rounded-lg text-sm flex items-center gap-2 transition',
                          i === active ? 'bg-brand-50 dark:bg-brand-500/10 text-brand-700 dark:text-brand-300'
                                       : 'hover:bg-ink-100 dark:hover:bg-ink-800')}>
                  <MethodChip m={e.method}/>
                  <span className="font-mono text-xs truncate">{e.path}</span>
                </button>
              </li>)}
          </ul>
        </nav>
        <article className="space-y-5">
          <EndpointDetail endpoint={endpoints[active]}/>
        </article>
      </div>
    </div>
  );
}

function MethodChip({ m }: { m: 'GET' | 'POST' }) {
  return (
    <span className={cn('text-[10px] font-mono font-semibold px-1.5 py-0.5 rounded',
      m === 'GET' ? 'bg-emerald-100 text-emerald-700' : 'bg-blue-100 text-blue-700')}>
      {m}
    </span>
  );
}

function EndpointDetail({ endpoint: e }: { endpoint: Endpoint }) {
  return (
    <>
      <div className="card p-5">
        <div className="flex items-center gap-3 mb-3">
          <MethodChip m={e.method}/>
          <code className="font-mono text-lg">{e.path}</code>
        </div>
        <p className="text-ink-600 dark:text-ink-300 text-sm">{e.summary}</p>
      </div>
      {e.params && (
        <div className="card p-5">
          <div className="eyebrow mb-3">Parameters</div>
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-ink-500">
                <th className="py-1.5 pr-3">Name</th>
                <th className="py-1.5 pr-3">Type</th>
                <th className="py-1.5 pr-3">In</th>
                <th className="py-1.5">Notes</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-ink-100 dark:divide-ink-700">
              {e.params.map(p => (
                <tr key={p.name}>
                  <td className="py-2 font-mono text-sm">{p.name}</td>
                  <td className="py-2 font-mono text-xs text-ink-500">{p.type}</td>
                  <td className="py-2 font-mono text-xs text-ink-500">{p.where}</td>
                  <td className="py-2 text-xs text-ink-600 dark:text-ink-300">{p.note}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <CodeBlock title="Example request" body={e.example}/>
      {e.response && <CodeBlock title="Example response" body={e.response}/>}
    </>
  );
}

function CodeBlock({ title, body }: { title: string; body: string }) {
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    await navigator.clipboard.writeText(body); setCopied(true);
    setTimeout(() => setCopied(false), 1800);
  };
  return (
    <div className="card overflow-hidden">
      <div className="flex items-center justify-between px-4 py-2 border-b border-ink-200 dark:border-ink-700">
        <div className="eyebrow">{title}</div>
        <button onClick={copy} className="btn-ghost !py-1 text-xs">
          {copied ? <><Check size={12}/> Copied</> : <><Copy size={12}/> Copy</>}
        </button>
      </div>
      <pre className="p-4 font-mono text-xs overflow-x-auto bg-ink-900 text-ink-100">
        <code>{body}</code>
      </pre>
    </div>
  );
}
