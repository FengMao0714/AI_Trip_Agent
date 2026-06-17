import { MainLayout } from "@/components/layout/MainLayout";

interface ChatPageProps {
  searchParams?: Promise<{
    q?: string;
  }>;
}

export default async function ChatPage({ searchParams }: ChatPageProps) {
  const params = await searchParams;

  return <MainLayout initialQuery={params?.q ?? ""} />;
}
