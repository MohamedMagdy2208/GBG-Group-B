type Props = {
  className?: string;
};

export function Skeleton({ className }: Props) {
  return <div className={`animate-pulse rounded-md bg-slate-200 ${className ?? "h-4 w-full"}`} />;
}

export function SkeletonRows({ count = 4 }: { count?: number }) {
  return (
    <div className="grid gap-2">
      {Array.from({ length: count }).map((_, idx) => (
        <Skeleton key={idx} className="h-12 w-full rounded-lg" />
      ))}
    </div>
  );
}
