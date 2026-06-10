"use client";

import { useQuery } from "@tanstack/react-query";
import { Search, MessageSquare, Clock } from "lucide-react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { formatDistanceToNow } from "@/lib/format";
import { useRouter } from "next/navigation";

export default function HistoryPage() {
  const router = useRouter();
  const { data: history, isLoading } = useQuery({
    queryKey: ["search-history"],
    queryFn: () => api.getSearchHistory(),
  });

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">Search History</h1>

      <Card>
        <CardHeader>
          <CardTitle>Recent Queries</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-2">
              {Array.from({ length: 5 }).map((_, i) => (
                <Skeleton key={i} className="h-14 w-full" />
              ))}
            </div>
          ) : history?.length === 0 ? (
            <div className="flex flex-col items-center gap-2 py-12 text-muted-foreground">
              <Clock className="h-12 w-12" />
              <p>No search history yet.</p>
            </div>
          ) : (
            <div className="space-y-2">
              {history?.map((item) => (
                <div
                  key={item.id}
                  className="flex items-center justify-between rounded border p-3"
                >
                  <div className="flex items-center gap-3 min-w-0 flex-1">
                    {item.type === "search" ? (
                      <Search className="h-4 w-4 shrink-0 text-muted-foreground" />
                    ) : (
                      <MessageSquare className="h-4 w-4 shrink-0 text-muted-foreground" />
                    )}
                    <div className="min-w-0">
                      <p className="text-sm font-medium truncate">
                        {item.query}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {item.type === "search" ? "Search" : "Ask RAG"} &middot;{" "}
                        {formatDistanceToNow(item.created_at)}
                      </p>
                    </div>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() =>
                      router.push(
                        `/dashboard/search?q=${encodeURIComponent(item.query)}`,
                      )
                    }
                  >
                    Re-run
                  </Button>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
