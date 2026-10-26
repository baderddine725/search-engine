export function LoadingGrid({ n = 10 }: { n?: number }) {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
      {Array.from({ length: n }).map((_, i) => (
        <div key={i} className="card overflow-hidden">
          <div className="skeleton aspect-[4/3]"/>
          <div className="p-3 space-y-2">
            <div className="skeleton h-3 w-2/3"/>
            <div className="skeleton h-3 w-1/3"/>
          </div>
        </div>
      ))}
    </div>
  );
}
