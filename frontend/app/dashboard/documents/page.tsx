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
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
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

function capitalize(s: string) {
  return s.charAt(0).toUpperCase() + s.slice(1);
}

const CLASS_COLORS: Record<string, "default" | "secondary" | "outline" | "destructive"> = {
  public: "default",
  internal: "secondary",
  confidential: "destructive",
};

function statusBadge(status: string) {
  const variants: Record<string, "default" | "secondary" | "destructive"> = {
    indexed: "default",
    uploaded: "secondary",
    processing: "secondary",
    failed: "destructive",
  };
  return <Badge variant={variants[status] ?? "secondary"}>{status}</Badge>;
}

function classificationBadge(cls: string) {
  return (
    <Badge variant={CLASS_COLORS[cls] ?? "outline"}>
      {capitalize(cls)}
    </Badge>
  );
}

export default function DocumentsPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [uploadOpen, setUploadOpen] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [classification, setClassification] = useState("internal");
  const [collectionId, setCollectionId] = useState("none");

  const { data, isLoading } = useQuery({
    queryKey: ["documents"],
    queryFn: () => api.listDocuments(1, 100),
  });

  const { data: collections } = useQuery({
    queryKey: ["collections"],
    queryFn: () => api.listCollections(),
  });

  const uploadMutation = useMutation({
    mutationFn: () => {
      if (!file) throw new Error("No file selected");
      return api.uploadDocument(file, classification, collectionId === "none" ? undefined : collectionId);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documents"] });
      toast.success("Document uploaded");
      setUploadOpen(false);
      setFile(null);
      setClassification("internal");
      setCollectionId("none");
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
              <div className="space-y-2">
                <Label htmlFor="classification">Classification</Label>
                <Select value={classification} onValueChange={(v) => v && setClassification(v)}>
                  <SelectTrigger id="classification">
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
                <Label htmlFor="collection">Collection</Label>
                <Select value={collectionId} onValueChange={(v) => v && setCollectionId(v)}>
                  <SelectTrigger id="collection">
                    <SelectValue placeholder="None" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">None</SelectItem>
                    {collections?.map((c) => (
                      <SelectItem key={c.id} value={c.id}>{c.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
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
          ) : !data?.items?.length ? (
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
                    <TableHead>Classification</TableHead>
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
                    <TableCell>{classificationBadge(doc.classification)}</TableCell>
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
