import { Skeleton } from "@/components/ui/skeleton";

export default function ThreadsLoading() {
  return <div className="p-8" aria-label="Loading Threads workspace" role="status">
    <Skeleton className="mb-6 h-12 w-72" /><Skeleton className="h-96 w-full" />
  </div>;
}
