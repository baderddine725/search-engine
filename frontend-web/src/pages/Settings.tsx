import { useState } from 'react';
import { Moon, Sun, RefreshCw, ExternalLink } from 'lucide-react';
import { PageHeader } from '../components/PageHeader';
import { API_BASE } from '../lib/api';

export default function Settings() {
  const [dark, setDark] = useState(() => document.documentElement.classList.contains('dark'));

  const toggle = () => {
    const next = !dark;
    setDark(next);
    document.documentElement.classList.toggle('dark', next);
    localStorage.setItem('theme', next ? 'dark' : 'light');
  };

  const clearCache = () => {
    localStorage.clear();
    sessionStorage.clear();
    alert('Local cache cleared.');
  };

  return (
    <div className="space-y-6">
      <PageHeader eyebrow="Preferences" title="Settings"
                  subtitle="Local preferences for this browser only. No account required."/>
      <div className="grid md:grid-cols-2 gap-6">
        <div className="card p-5">
          <div className="eyebrow mb-2">Theme</div>
          <div className="flex items-center justify-between">
            <div>
              <div className="font-medium">{dark ? 'Dark' : 'Light'} mode</div>
              <div className="text-xs text-ink-500 mt-0.5">Persisted in local storage.</div>
            </div>
            <button onClick={toggle} className="btn-secondary">
              {dark ? <Sun size={14}/> : <Moon size={14}/>}
              {dark ? 'Switch to light' : 'Switch to dark'}
            </button>
          </div>
        </div>

        <div className="card p-5">
          <div className="eyebrow mb-2">Backend</div>
          <div className="font-mono text-sm break-all">{API_BASE}</div>
          <div className="text-xs text-ink-500 mt-2">
            Change via <code>VITE_API_BASE_URL</code> at build time.
          </div>
          <a href={`${API_BASE}/health`} target="_blank" rel="noreferrer"
             className="btn-secondary mt-4 inline-flex">
            <ExternalLink size={14}/> Open /health
          </a>
        </div>

        <div className="card p-5">
          <div className="eyebrow mb-2">Local cache</div>
          <div className="text-sm text-ink-600 dark:text-ink-300">
            Clears search history and preferences stored in this browser.
          </div>
          <button onClick={clearCache} className="btn-secondary mt-3">
            <RefreshCw size={14}/> Clear cache
          </button>
        </div>

        <div className="card p-5">
          <div className="eyebrow mb-2">Related interfaces</div>
          <ul className="space-y-2 text-sm">
            <li>
              <a className="text-brand-600 hover:underline inline-flex items-center gap-1"
                 target="_blank" rel="noreferrer" href="http://localhost:8501">
                Streamlit UI (original) <ExternalLink size={12}/>
              </a>
            </li>
            <li>
              <a className="text-brand-600 hover:underline inline-flex items-center gap-1"
                 target="_blank" rel="noreferrer" href="http://localhost:9200">
                Elasticsearch <ExternalLink size={12}/>
              </a>
            </li>
          </ul>
        </div>
      </div>
    </div>
  );
}
