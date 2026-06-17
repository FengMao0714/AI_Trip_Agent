import Link from "next/link";
import { ArrowLeft } from "lucide-react";

import { ItineraryView } from "@/components/itinerary/ItineraryView";
import { Button } from "@/components/ui/button";
import { fetchSession } from "@/lib/api";
import { parseItinerary } from "@/lib/parseItinerary";

interface ItineraryPageProps {
  params: Promise<{
    id: string;
  }>;
}

export const dynamic = "force-dynamic";

async function loadSessionItinerary(sessionId: string) {
  try {
    const session = await fetchSession(sessionId);
    return parseItinerary(session.itinerary);
  } catch {
    return null;
  }
}

export default async function ItineraryPage({ params }: ItineraryPageProps) {
  const { id } = await params;
  const itinerary = await loadSessionItinerary(id);

  return (
    <main className="min-h-screen bg-zinc-50 text-zinc-950">
      <div className="mx-auto flex w-full max-w-6xl flex-col gap-5 px-4 py-5 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between gap-3">
          <Button asChild type="button" variant="outline" className="rounded-lg">
            <Link href="/chat">
              <ArrowLeft className="h-4 w-4" aria-hidden="true" />
              返回对话
            </Link>
          </Button>
        </div>

        {itinerary ? (
          <ItineraryView itinerary={itinerary} showDetailLink={false} />
        ) : (
          <section className="flex min-h-[50vh] flex-col items-center justify-center gap-3 rounded-lg border border-zinc-200 bg-white px-6 py-12 text-center">
            <h1 className="text-xl font-semibold text-zinc-950">
              未找到可展示的行程
            </h1>
            <p className="max-w-md text-sm leading-6 text-zinc-600">
              当前会话可能已过期，或后端会话服务暂时不可用。
            </p>
            <Button asChild type="button" className="rounded-lg bg-teal-700 hover:bg-teal-800">
              <Link href="/chat">重新规划</Link>
            </Button>
          </section>
        )}
      </div>
    </main>
  );
}
