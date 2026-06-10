"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Upload, Trash2, FileText } from "lucide-react";
import { api } from "@/lib/api";
import type { Document } from "@/lib/types";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";
import { toast } from "sonner";
import { formatDistanceToNow } from "@/lib/format";
import { useRouter } from "next/navigation";

function statusBadge(status: Document["status"]) {
  const variants: Record<string, "default" | "secondary" | "destructive"> = {
    ready: "default",
    processing: "secondary",
    failed: "destructive",
  };
  return <Badge variant={variants[status] ?? "secondary"}>{status}</Badge>;
}

export default function DocumentsPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [uploadOpen, setUploadOpen] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [isPublic, setIsPublic] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ["documents"],
    queryFn: () => api.listDocuments(1, 100),
  });

  const uploadMutation = useMutation({
    mutationFn: () => {
      if (!file) throw new Error("No file selected");
      return api.uploadDocument(file, isPublic);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documents"] });
      toast.success("Document uploaded");
      setUploadOpen(false);
      setFile(null);
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.deleteDocument(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documents"] });
      toast.success("Document deleted");
    },
    onError: (err: Error) => toast.error(err.message),
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold">Documents</h1>
        <Dialog open={uploadOpen} onOpenChange={setUploadOpen}>
          <DialogTrigger
            render={
              <Button>
                <Upload className="mr-2 h-4 w-4" />
                Upload
              </Button>
            }
          />
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Upload Document</DialogTitle>
            </DialogHeader>
            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="file">File</Label>
                <Input
                  id="file"
                  type="file"
                  onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                  accept=".pdf,.docx,.txt,.md,.html"
                />
              </div>
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="isPublic"
                  checked={isPublic}
                  onChange={(e) => setIsPublic(e.target.checked)}
                  className="h-4 w-4 rounded border-gray-300"
                />
                <Label htmlFor="isPublic">Make public (all users can access)</Label>
              </div>
              <Button
                onClick={() => uploadMutation.mutate()}
                disabled={!file || uploadMutation.isPending}
                className="w-full"
              >
                {uploadMutation.isPending ? "Uploading..." : "Upload"}
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>All Documents</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-2">
              {Array.from({ length: 5 }).map((_, i) => (
                <Skeleton key={i} className="h-12 w-full" />
              ))}
            </div>
          ) : data?.items?.length === 0 ? (
            <div className="flex flex-col items-center gap-2 py-12 text-muted-foreground">
              <FileText className="h-12 w-12" />
              <p>No documents yet. Upload your first document.</p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Access</TableHead>
                  <TableHead>Uploaded</TableHead>
                  <TableHead className="w-16" />
                </TableRow>
              </TableHeader>
              <TableBody>
                {data?.items?.map((doc) => (
                  <TableRow
                    key={doc.id}
                    className="cursor-pointer"
                    onClick={() => router.push(`/dashboard/documents/${doc.id}`)}
                  >
                    <TableCell className="font-medium">{doc.filename}</TableCell>
                    <TableCell>{doc.file_type}</TableCell>
                    <TableCell>{statusBadge(doc.status)}</TableCell>
                    <TableCell>
                      {doc.is_public ? (
                        <Badge variant="secondary">Public</Badge>
                      ) : (
                        <Badge variant="outline">Restricted</Badge>
                      )}
                    </TableCell>
                    <TableCell className="text-muted-foreground text-sm">
                      {formatDistanceToNow(doc.created_at)}
                    </TableCell>
                    <TableCell>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={(e) => {
                          e.stopPropagation();
                          deleteMutation.mutate(doc.id);
                        }}
                      >
                        <Trash2 className="h-4 w-4 text-destructive" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
