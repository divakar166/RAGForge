"use client";

import { useQuery, useMutation } from "@tanstack/react-query";
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
import { Play } from "lucide-react";

export default function AdminEvaluatePage() {
  const { data: dataset, isLoading: datasetLoading } = useQuery({
    queryKey: ["dataset"],
    queryFn: () => api.getDataset(),
  });

  const evaluateMutation = useMutation({
    mutationFn: () => api.runEvaluation(),
    onSuccess: () => {
      toast.success("Evaluation complete");
    },
    onError: (err: Error) => toast.error(err.message),
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold">Evaluation</h1>
        <Button
          onClick={() => evaluateMutation.mutate()}
          disabled={evaluateMutation.isPending}
        >
          <Play className="mr-2 h-4 w-4" />
          {evaluateMutation.isPending ? "Running..." : "Run Evaluation"}
        </Button>
      </div>

      {datasetLoading ? (
        <Skeleton className="h-24 w-full" />
      ) : dataset ? (
        <Card>
          <CardHeader>
            <CardTitle>Golden Dataset</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              Name: {dataset.name} &middot; Size: {dataset.size} samples
            </p>
          </CardContent>
        </Card>
      ) : null}

      {evaluateMutation.data && (
        <Card>
          <CardHeader>
            <CardTitle>Results</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Metric</TableHead>
                  <TableHead>Score</TableHead>
                  <TableHead>Threshold</TableHead>
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {evaluateMutation.data.map((result) => (
                  <TableRow key={result.metric}>
                    <TableCell className="font-medium">
                      {result.metric}
                    </TableCell>
                    <TableCell>{result.score.toFixed(4)}</TableCell>
                    <TableCell>{result.threshold.toFixed(2)}</TableCell>
                    <TableCell>
                      {result.passed ? (
                        <Badge variant="default">Passed</Badge>
                      ) : (
                        <Badge variant="destructive">Failed</Badge>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
