"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
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
import { Skeleton } from "@/components/ui/skeleton";

export default function AdminAuditPage() {
  const { data: logs, isLoading } = useQuery({
    queryKey: ["audit-logs"],
    queryFn: () => api.getAuditLogs(),
  });

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">Audit Log</h1>

      <Card>
        <CardHeader>
          <CardTitle>Activity Log</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-2">
              {Array.from({ length: 8 }).map((_, i) => (
                <Skeleton key={i} className="h-10 w-full" />
              ))}
            </div>
          ) : !logs?.length ? (
            <p className="text-muted-foreground py-8 text-center">No audit logs yet.</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Action</TableHead>
                  <TableHead>Resource</TableHead>
                  <TableHead>Resource ID</TableHead>
                  <TableHead>IP</TableHead>
                  <TableHead>Timestamp</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {(logs as Array<Record<string, unknown>>).map((log) => (
                  <TableRow key={String(log.id)}>
                    <TableCell className="font-mono text-xs">
                      {String(log.action ?? "")}
                    </TableCell>
                    <TableCell>{String(log.resource_type ?? "—")}</TableCell>
                    <TableCell className="text-xs text-muted-foreground font-mono">
                      {String(log.resource_id ?? "—").slice(0, 8)}...
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {String(log.ip_address ?? "—")}
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {log.timestamp
                        ? new Date(String(log.timestamp)).toLocaleString()
                        : "—"}
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
