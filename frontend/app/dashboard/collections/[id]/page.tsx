"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, Trash2 } from "lucide-react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { toast } from "sonner";
import Link from "next/link";
import { formatDistanceToNow } from "@/lib/format";

export default function CollectionDetailPage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id as string;
  const queryClient = useQueryClient();

  const { data: collection, isLoading } = useQuery({
    queryKey: ["collection", id],
    queryFn: () => api.getCollection(id),
  });

  const { data: docs } = useQuery({
    queryKey: ["documents"],
    queryFn: () => api.listDocuments(1, 100),
  });

  const deleteMutation = useMutation({
    mutationFn: () => api.deleteCollection(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["collections"] });
      toast.success("Collection deleted");
      router.push("/dashboard/collections");
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const collectionDocs = docs?.items?.filter((d) => d.collection_id === id) ?? [];

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-48 w-full" />
      </div>
    );
  }

  if (!collection) {
    return <div>Collection not found</div>;
  }

  return (
    <div className="space-y-6">
      <Link
        href="/dashboard/collections"
        className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to collections
      </Link>

      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold">{collection.name}</h1>
          {collection.description && (
            <p className="text-muted-foreground mt-1">{collection.description}</p>
          )}
        </div>
        <div className="flex gap-2">
          <Button variant="destructive" size="sm" onClick={() => deleteMutation.mutate()}>
            <Trash2 className="mr-2 h-4 w-4" />
            Delete
          </Button>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Documents ({collectionDocs.length})</CardTitle>
        </CardHeader>
        <CardContent>
          {!collectionDocs.length ? (
            <p className="text-muted-foreground py-8 text-center">
              No documents in this collection.
            </p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Uploaded</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {collectionDocs.map((doc) => (
                  <TableRow
                    key={doc.id}
                    className="cursor-pointer"
                    onClick={() => router.push(`/dashboard/documents/${doc.id}`)}
                  >
                    <TableCell className="font-medium">{doc.filename}</TableCell>
                    <TableCell>{doc.file_type}</TableCell>
                    <TableCell>
                      <Badge variant={doc.status === "indexed" ? "default" : "secondary"}>
                        {doc.status}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {formatDistanceToNow(doc.created_at)}
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
