export const cn = (...xs: (string | undefined | null | false)[]) =>
  xs.filter(Boolean).join(' ');

export const fmt = (n: number | undefined | null, digits = 0): string => {
  if (n === undefined || n === null || Number.isNaN(n)) return '—';
  return n.toLocaleString('en-US', {
    maximumFractionDigits: digits,
    minimumFractionDigits: digits,
  });
};

export const fmtMs = (n: number | undefined): string =>
  n === undefined ? '—' : n < 1 ? '<1 ms' : n < 1000 ? `${n.toFixed(0)} ms` : `${(n / 1000).toFixed(2)} s`;

export const classFromPath = (p: string): string =>
  (p.split('/')[0] || '').replace(/\\/g, '/');

export const useLocalStorage = <T>(key: string, initial: T) => {
  const read = (): T => {
    try {
      const v = window.localStorage.getItem(key);
      return v ? (JSON.parse(v) as T) : initial;
    } catch { return initial; }
  };
  const write = (v: T) => {
    try { window.localStorage.setItem(key, JSON.stringify(v)); } catch { /* ignore */ }
  };
  return [read, write] as const;
};
