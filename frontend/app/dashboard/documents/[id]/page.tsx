"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useParams } from "next/navigation";
import { Download } from "lucide-react";
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
import { Skeleton } from "@/components/ui/skeleton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { toast } from "sonner";
import { formatDistanceToNow } from "@/lib/format";
import { ArrowLeft } from "lucide-react";
import Link from "next/link";

const statusVariant: Record<string, "default" | "secondary" | "destructive"> = {
  indexed: "default",
  uploaded: "secondary",
  processing: "secondary",
  failed: "destructive",
};

const CLASS_COLORS: Record<string, "default" | "secondary" | "outline" | "destructive"> = {
  public: "default",
  internal: "secondary",
  confidential: "destructive",
};

const CLASS_ROLE_MAP: Record<string, string[]> = {
  public: ["viewer", "member", "admin", "owner"],
  internal: ["member", "admin", "owner"],
  confidential: ["admin", "owner"],
};

function capitalize(s: string) {
  return s.charAt(0).toUpperCase() + s.slice(1);
}

export default function DocumentDetailPage() {
  const params = useParams();
  const id = params.id as string;
  const queryClient = useQueryClient();

  const { data: doc, isLoading } = useQuery({
    queryKey: ["document", id],
    queryFn: () => api.getDocument(id),
  });

  const { data: collections } = useQuery({
    queryKey: ["collections"],
    queryFn: () => api.listCollections(),
  });

  const updateMutation = useMutation({
    mutationFn: (data: { classification?: string; collection_id?: string | null }) =>
      api.updateDocument(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["document", id] });
      toast.success("Document updated");
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const currentCollection = collections?.find((c) => c.id === doc?.collection_id);

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
        <div className="flex items-center gap-2">
          <Badge variant={statusVariant[doc.status] ?? "secondary"}>
            {doc.status}
          </Badge>
          <Button
            variant="outline"
            size="sm"
            onClick={async () => {
              try {
                const blob = await api.downloadDocument(id);
                const url = URL.createObjectURL(blob);
                const a = document.createElement("a");
                a.href = url;
                a.download = doc.filename;
                a.click();
                URL.revokeObjectURL(url);
                toast.success("Download started");
              } catch {
                toast.error("Download failed");
              }
            }}
          >
            <Download className="mr-2 h-4 w-4" />
            Download
          </Button>
        </div>
      </div>

      <div className="grid gap-6 md:grid-cols-3">
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
            <CardTitle>Collection</CardTitle>
          </CardHeader>
          <CardContent>
            <Select
              value={doc.collection_id ?? "_none"}
              onValueChange={(v) => updateMutation.mutate({ collection_id: v === "_none" ? null : v })}
            >
              <SelectTrigger>
                <SelectValue placeholder="No collection" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="_none">No collection</SelectItem>
                {collections?.map((c) => (
                  <SelectItem key={c.id} value={c.id}>
                    {c.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Access Control</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-xs text-muted-foreground">
              Classification determines which roles can view this document
            </p>
            <div className="space-y-2">
              <Label>Classification</Label>
              <Select
                value={doc.classification}
                onValueChange={(v) => v && updateMutation.mutate({ classification: v })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="public">Public</SelectItem>
                  <SelectItem value="internal">Internal</SelectItem>
                  <SelectItem value="confidential">Confidential</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label className="text-muted-foreground">Roles with access</Label>
              <div className="flex flex-wrap gap-1">
                {(CLASS_ROLE_MAP[doc.classification] ?? []).map((r) => (
                  <Badge key={r} variant="secondary" className="capitalize">
                    {r}
                  </Badge>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
