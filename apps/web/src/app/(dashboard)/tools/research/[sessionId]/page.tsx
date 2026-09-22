import { ResearchWorkspace } from "@/features/research/research-workspace";

export default async function ResearchSessionPage({
  params,
}: {
  params: Promise<{ sessionId: string }>;
}) {
  const { sessionId } = await params;
  return <ResearchWorkspace initialSessionId={sessionId} />;
}
