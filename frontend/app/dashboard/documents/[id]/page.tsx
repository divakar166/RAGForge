"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useParams } from "next/navigation";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Skeleton } from "@/components/ui/skeleton";
import { toast } from "sonner";
import { formatDistanceToNow } from "@/lib/format";
import { ArrowLeft } from "lucide-react";
import Link from "next/link";

export default function DocumentDetailPage() {
  const params = useParams();
  const id = params.id as string;
  const queryClient = useQueryClient();

  const { data: doc, isLoading } = useQuery({
    queryKey: ["document", id],
    queryFn: () => api.getDocument(id),
  });

  const accessMutation = useMutation({
    mutationFn: (data: { is_public?: boolean }) =>
      api.setDocumentAccess(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["document", id] });
      toast.success("Access settings updated");
    },
    onError: (err: Error) => toast.error(err.message),
  });

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-48 w-full" />
      </div>
    );
  }

  if (!doc) {
    return <div>Document not found</div>;
  }

  return (
    <div className="space-y-6">
      <Link
        href="/dashboard/documents"
        className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to documents
      </Link>

      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold">{doc.filename}</h1>
          <p className="text-muted-foreground">
            {doc.file_type} &middot; {(doc.file_size / 1024).toFixed(1)} KB
          </p>
        </div>
        <Badge
          variant={doc.status === "ready" ? "default" : "secondary"}
        >
          {doc.status}
        </Badge>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Details</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Chunks</span>
              <span>{doc.chunk_count}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Uploaded</span>
              <span>{formatDistanceToNow(doc.created_at)}</span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Access Control</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <Label htmlFor="isPublic">Public document</Label>
              <Switch
                id="isPublic"
                checked={doc.is_public}
                onCheckedChange={(checked) =>
                  accessMutation.mutate({ is_public: checked })
                }
              />
            </div>
            {doc.is_public && (
              <p className="text-xs text-muted-foreground">
                Anyone with access can view this document
              </p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
