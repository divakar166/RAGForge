"use client";

import { useState } from "react";
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
import { Checkbox } from "@/components/ui/checkbox";
import { Skeleton } from "@/components/ui/skeleton";
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

const AVAILABLE_ROLES = ["admin", "editor", "member"];

export default function DocumentDetailPage() {
  const params = useParams();
  const id = params.id as string;
  const queryClient = useQueryClient();

  const { data: doc, isLoading } = useQuery({
    queryKey: ["document", id],
    queryFn: () => api.getDocument(id),
  });

  const accessMutation = useMutation({
    mutationFn: (data: { allowed_roles?: string[] }) =>
      api.setDocumentAccess(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["document", id] });
      toast.success("Access settings updated");
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const [pendingRoles, setPendingRoles] = useState<string[] | null>(null);
  const currentRoles = pendingRoles ?? doc?.allowed_roles ?? [];

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

  const toggleRole = (role: string) => {
    const roles = pendingRoles ?? [...doc.allowed_roles];
    const idx = roles.indexOf(role);
    if (idx >= 0) {
      roles.splice(idx, 1);
    } else {
      roles.push(role);
    }
    setPendingRoles(roles);
  };

  const saveAccess = () => {
    if (pendingRoles) {
      accessMutation.mutate({ allowed_roles: pendingRoles });
      setPendingRoles(null);
    }
  };

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
            <p className="text-xs text-muted-foreground">
              Choose which roles can view this document
            </p>
            {AVAILABLE_ROLES.map((role) => (
              <div key={role} className="flex items-center gap-2">
                <Checkbox
                  id={`role-${role}`}
                  checked={currentRoles.includes(role)}
                  onCheckedChange={() => toggleRole(role)}
                />
                <Label htmlFor={`role-${role}`} className="capitalize">
                  {role}
                </Label>
              </div>
            ))}
            {pendingRoles && (
              <Button onClick={saveAccess} size="sm" className="mt-2">
                Save
              </Button>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
