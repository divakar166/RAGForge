"use client";

import { useQuery } from "@tanstack/react-query";
import { FileText, Search, Clock, Activity } from "lucide-react";
import { api } from "@/lib/api";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

export default function DashboardPage() {
  const { data: docs, isLoading: docsLoading } = useQuery({
    queryKey: ["documents"],
    queryFn: () => api.listDocuments(1, 100),
  });
  const { data: history, isLoading: historyLoading } = useQuery({
    queryKey: ["search-history"],
    queryFn: () => api.getSearchHistory(),
  });

  const stats = [
    {
      title: "Documents",
      value: docs?.total ?? 0,
      icon: FileText,
      loading: docsLoading,
    },
    {
      title: "Searches",
      value: history?.length ?? 0,
      icon: Search,
      loading: historyLoading,
    },
    {
      title: "Ready Documents",
      value: docs?.items?.filter((d) => d.status === "indexed").length ?? 0,
      icon: Activity,
      loading: docsLoading,
    },
    {
      title: "Processing",
      value: docs?.items?.filter((d) => d.status === "processing" || d.status === "uploaded").length ?? 0,
      icon: Clock,
      loading: docsLoading,
    },
  ];

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">Dashboard</h1>
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat) => {
          const Icon = stat.icon;
          return (
            <Card key={stat.title}>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium">
                  {stat.title}
                </CardTitle>
                <Icon className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                {stat.loading ? (
                  <Skeleton className="h-8 w-20" />
                ) : (
                  <div className="text-2xl font-bold">{stat.value}</div>
                )}
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
