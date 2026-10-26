import { useEffect } from 'react';
import { X } from 'lucide-react';
import { imageUrl } from '../lib/api';

export function ImagePreviewModal({
  path, onClose,
}: { path: string; onClose: () => void }) {
  useEffect(() => {
    const h = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('keydown', h);
    return () => window.removeEventListener('keydown', h);
  }, [onClose]);
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-ink-900/70 backdrop-blur-sm"
         onClick={onClose} role="dialog" aria-modal="true">
      <div className="relative max-w-5xl w-full" onClick={e => e.stopPropagation()}>
        <button onClick={onClose}
                className="absolute -top-2 -right-2 h-9 w-9 rounded-full bg-white text-ink-800
                           flex items-center justify-center shadow-lg hover:scale-105 transition"
                aria-label="Close">
          <X size={16}/>
        </button>
        <img src={imageUrl(path)} alt={path}
             className="rounded-xl max-h-[85vh] mx-auto shadow-2xl object-contain" />
        <div className="mt-3 font-mono text-xs text-ink-200 text-center">{path}</div>
      </div>
    </div>
  );
}
