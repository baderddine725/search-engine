// Centralised API client — all backend access goes through here.
// Base URL is configurable via VITE_API_BASE_URL (set at build time) and
// falls back to http://localhost:5000 for local development.

export const API_BASE: string =
  (import.meta.env.VITE_API_BASE_URL as string | undefined) || 'http://localhost:5000';

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

async function request<T>(
  path: string,
  init: RequestInit = {},
  timeoutMs = 60_000,
): Promise<T> {
  const controller = new AbortController();
  const to = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(`${API_BASE}${path}`, { ...init, signal: controller.signal });
    const text = await res.text();
    let body: any = null;
    if (text) {
      try { body = JSON.parse(text); } catch { body = text; }
    }
    if (!res.ok) {
      const msg = (body && (body.error || body.detail)) || res.statusText || `HTTP ${res.status}`;
      throw new ApiError(msg, res.status);
    }
    return body as T;
  } catch (e) {
    if ((e as any).name === 'AbortError')
      throw new ApiError('Request timed out', 0);
    throw e;
  } finally {
    clearTimeout(to);
  }
}

const qs = (p: Record<string, any>) => {
  const sp = new URLSearchParams();
  Object.entries(p).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== '') sp.set(k, String(v));
  });
  const s = sp.toString();
  return s ? `?${s}` : '';
};

// --- Types mirror the Flask backend's actual responses --------------------

export interface HealthResponse { status: string; elasticsearch?: string; detail?: string }
export interface ModelsResponse {
  default: string;
  models: Record<string, { label: string; description: string; dims: number; index: string }>;
}
export interface StatsResponse {
  text_documents: number;
  classes: Record<string, number>;
  models: Record<string, { label: string; images: number }>;
  benchmark_available: boolean;
}
export interface ImageHit {
  image_path: string;
  class_name: string;
  score: number;
  distance?: number | null;
}
export interface ImageSearchResponse {
  model: string;
  count: number;
  results: ImageHit[];
  extract_ms?: number;
  search_ms: number;
}
export interface TextHit {
  photo_id: string;
  title: string;
  tags: string;
  description: string;
  url: string;
  image_path?: string;
  score: number;
  highlight?: Record<string, string[]>;
}
export interface TextSearchResponse {
  query: string;
  count: number;
  results: TextHit[];
  search_ms: number;
}
export interface DescriptorsResponse {
  available: string[];
  descriptors: Record<string, { label: string; description: string; dims: number }>;
  all: Record<string, { label: string; description: string; dims: number }>;
}
export interface BenchmarkReport {
  k: number;
  per_class?: number;
  candidates: number;
  generated_at: string;
  classes: Record<string, number>;
  models: Record<string, {
    dims: number;
    label?: string;
    exact?: BenchmarkEval;
    approx?: BenchmarkEval;
    lsh?: BenchmarkEval;
    extraction?: { total_seconds: number; images: number; per_image_ms: number };
  }>;
}
export interface BenchmarkEval {
  map: number;
  p_at_1: number;
  precision?: number;
  mean_query_ms: number;
  per_class: Record<string, { ap: number; precision: number; n: number }>;
  curve?: number[];
}
export interface CompareResponse {
  query_class: string | null;
  size: number;
  overlap: string[];
  models: Record<string, {
    label: string;
    results: ImageHit[];
    extract_ms?: number;
    search_ms: number;
    metrics?: { precision: number; relevant: number; ap: number; curve: number[] };
  }>;
}
export interface DatasetImage { image_path: string; class_name: string }
export interface DatasetResponse { count: number; images: DatasetImage[] }

export interface MirflickrStats {
  indexed_documents: number;
  mpeg7_descriptors: string[];
  has_text: boolean;
}
export interface MirflickrTextResponse {
  query: string;
  total: number;
  count: number;
  results: Array<{
    photo_id: number; title: string; tags: string; owner: string;
    license: string; url: string; score: number; highlight?: Record<string, string[]>;
  }>;
  search_ms: number;
}

// --- Grouped service functions --------------------------------------------

export const Health = {
  get: () => request<HealthResponse>('/health', {}, 10_000),
};

export const Models = {
  list: () => request<ModelsResponse>('/models'),
};

export const Stats = {
  get: () => request<StatsResponse>('/stats'),
};

export const Search = {
  text: (q: string, size = 20) =>
    request<TextSearchResponse>(`/search/text${qs({ q, size })}`),

  image: (file: File, model = 'inception_lbp', size = 10) => {
    const fd = new FormData();
    fd.append('image', file);
    fd.append('model', model);
    fd.append('size', String(size));
    return request<ImageSearchResponse>('/search/image', { method: 'POST', body: fd });
  },

  url: (url: string, model = 'inception_lbp', size = 10) =>
    request<ImageSearchResponse>('/search/url', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url, model, size }),
    }),

  similar: (path: string, model = 'inception_lbp', size = 10) =>
    request<ImageSearchResponse>(`/search/similar${qs({ path, model, size })}`),
};

export const Descriptor = {
  list: () => request<DescriptorsResponse>('/descriptors'),

  search: (opts: {
    descriptors: string[]; weights?: number[];
    path?: string; image?: File; url?: string;
    size?: number; exact?: boolean;
  }) => {
    const base = {
      descriptors: opts.descriptors.join(','),
      weights: (opts.weights ?? opts.descriptors.map(() => 1)).join(','),
      size: opts.size ?? 10,
      exact: opts.exact ? '1' : '0',
    };
    if (opts.image) {
      const fd = new FormData();
      Object.entries(base).forEach(([k, v]) => fd.append(k, String(v)));
      fd.append('image', opts.image);
      return request<any>('/search/descriptor', { method: 'POST', body: fd });
    }
    const body: any = { ...base };
    if (opts.path) body.path = opts.path;
    if (opts.url) body.url = opts.url;
    return request<any>('/search/descriptor', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
  },
};

export const Combined = {
  search: (opts: {
    q?: string; path?: string; descriptors?: string[]; size?: number;
  }) =>
    request<any>('/search/combined', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        q: opts.q,
        path: opts.path,
        descriptors: opts.descriptors?.join(','),
        weights: opts.descriptors?.map(() => 1).join(','),
        size: opts.size ?? 10,
      }),
    }),
};

export const Compare = {
  byPath: (path: string, size = 10, candidates?: number) =>
    request<CompareResponse>('/compare', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path, size, candidates }),
    }),
  byImage: (file: File, size = 10) => {
    const fd = new FormData();
    fd.append('image', file);
    fd.append('size', String(size));
    return request<CompareResponse>('/compare', { method: 'POST', body: fd });
  },
};

export const Benchmark = {
  latest: () => request<BenchmarkReport>('/benchmark'),
  run: (opts: { k?: number; per_class?: number; candidates?: number } = {}) =>
    request<BenchmarkReport>('/benchmark/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(opts),
    }, 10 * 60_000),
};

export const Dataset = {
  images: (opts: { class?: string; size?: number; random?: boolean; seed?: number } = {}) =>
    request<DatasetResponse>(`/dataset/images${qs({
      class: opts.class,
      size: opts.size ?? 60,
      random: opts.random ? 1 : undefined,
      seed: opts.seed,
    })}`),
};

export const Mirflickr = {
  stats: () => request<MirflickrStats>('/mirflickr/stats'),
  text: (q: string, size = 12) =>
    request<MirflickrTextResponse>(`/mirflickr/search${qs({ q, size })}`),
  similar: (photo_id: number, descriptor: 'edge' | 'homo', size = 10) =>
    request<any>(`/mirflickr/similar${qs({ photo_id, descriptor, size })}`),
};

export const imageUrl = (path: string) => `${API_BASE}/images/${path}`;

// Thumbnail URL for a MIRFLICKR photo id — the backend serves the JPEG
// straight out of the mirflickr thumbnail zip archives.
export const mirflickrThumb = (photo_id: number) =>
  `${API_BASE}/mirflickr/thumb/${photo_id}`;
