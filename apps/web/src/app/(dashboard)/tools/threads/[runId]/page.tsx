import { notFound } from "next/navigation";
import { z } from "zod";
import { ThreadsWorkspace } from "@/features/threads/threads-workspace";

export default async function ThreadsRunPage({ params }: { params: Promise<{ runId: string }> }) {
  const { runId } = await params;
  if (!z.uuid().safeParse(runId).success) notFound();
  return <ThreadsWorkspace />;
}
