import { Link, useNavigate } from 'react-router-dom';
import { Shuffle, Expand } from 'lucide-react';
import { useState } from 'react';
import { imageUrl } from '../lib/api';
import { cn } from '../lib/utils';
import { ImagePreviewModal } from './ImagePreviewModal';

export function ImageCard({
  path, className, score, distance, rank, matched, muted, onSelect, extra,
}: {
  path: string; className?: string; score?: number; distance?: number;
  rank?: number; matched?: boolean; muted?: string; extra?: React.ReactNode;
  onSelect?: (path: string) => void;
}) {
  const nav = useNavigate();
  const [preview, setPreview] = useState(false);
  return (
    <>
      <div className="card card-hover overflow-hidden group">
        <div className="relative aspect-[4/3] bg-ink-100 dark:bg-ink-900 overflow-hidden">
          <img
            src={imageUrl(path)} alt={path} loading="lazy"
            className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-[1.02]"
            onClick={() => setPreview(true)}
          />
          {rank !== undefined && (
            <div className="absolute top-2 left-2 h-7 min-w-[1.75rem] px-2 rounded-md
                            bg-white/90 dark:bg-ink-900/80 backdrop-blur-sm
                            border border-ink-200/80 dark:border-ink-700
                            flex items-center justify-center text-xs font-mono font-medium
                            text-ink-700 dark:text-ink-200">
              #{rank}
            </div>
          )}
          <button
            className="absolute top-2 right-2 h-7 w-7 rounded-md
                       bg-white/90 dark:bg-ink-900/80 backdrop-blur-sm
                       border border-ink-200/80 dark:border-ink-700
                       opacity-0 group-hover:opacity-100 transition-opacity
                       flex items-center justify-center text-ink-700 dark:text-ink-200"
            onClick={() => setPreview(true)} aria-label="Preview">
            <Expand size={13} />
          </button>
          {className && (
            <div className="absolute bottom-2 left-2">
              <span className={cn(
                'chip',
                matched === true ? 'bg-emerald-500/90 text-white' :
                matched === false ? 'bg-red-500/90 text-white' :
                'bg-white/90 dark:bg-ink-900/80 text-ink-800 dark:text-ink-100'
              )}>
                {className}
              </span>
            </div>
          )}
        </div>
        <div className="p-3 space-y-1.5">
          <div className="font-mono text-[11px] text-ink-500 dark:text-ink-400 truncate" title={path}>
            {path}
          </div>
          {(score !== undefined || distance !== undefined) && (
            <div className="flex items-center justify-between text-xs">
              {distance !== undefined && (
                <span className="text-ink-500 dark:text-ink-400">
                  distance <span className="font-mono text-ink-800 dark:text-ink-100 tabular-nums">
                    {distance.toFixed(3)}
                  </span>
                </span>
              )}
              {score !== undefined && (
                <span className="text-ink-500 dark:text-ink-400">
                  score <span className="font-mono text-ink-800 dark:text-ink-100 tabular-nums">
                    {score.toFixed(3)}
                  </span>
                </span>
              )}
            </div>
          )}
          {muted && <div className="text-[11px] text-ink-500 dark:text-ink-400">{muted}</div>}
          {extra}
          <div className="pt-2 flex gap-2">
            <button
              className="btn-secondary flex-1 text-xs !py-1.5"
              onClick={() => onSelect ? onSelect(path) :
                             nav(`/similar?path=${encodeURIComponent(path)}`)}>
              <Shuffle size={12}/> Find similar
            </button>
          </div>
        </div>
      </div>
      {preview && <ImagePreviewModal path={path} onClose={() => setPreview(false)} />}
    </>
  );
}
