"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Shield, ShieldOff, Trash2 } from "lucide-react";
import { api } from "@/lib/api";
import type { Member } from "@/lib/types";
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
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { toast } from "sonner";

const roleBadge = (role: string) => {
  const variants: Record<string, "default" | "secondary" | "outline" | "destructive"> = {
    owner: "default",
    admin: "secondary",
  };
  return <Badge variant={variants[role] ?? "outline"}>{role}</Badge>;
};

export default function AdminMembersPage() {
  const queryClient = useQueryClient();
  const [editMember, setEditMember] = useState<Member | null>(null);
  const [newRole, setNewRole] = useState("");

  const { data: members, isLoading: membersLoading } = useQuery({
    queryKey: ["members"],
    queryFn: () => api.listMembers(),
  });

  const { data: roles } = useQuery({
    queryKey: ["org-roles"],
    queryFn: () => api.listOrgRoles(),
  });

  const updateMutation = useMutation({
    mutationFn: ({ userId, role }: { userId: string; role: string }) =>
      api.updateMember(userId, { role }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["members"] });
      toast.success("Member role updated");
      setEditMember(null);
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const removeMutation = useMutation({
    mutationFn: (userId: string) => api.removeMember(userId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["members"] });
      toast.success("Member removed");
    },
    onError: (err: Error) => toast.error(err.message),
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold">Organization Members</h1>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Members</CardTitle>
        </CardHeader>
        <CardContent>
          {membersLoading ? (
            <div className="space-y-2">
              {Array.from({ length: 3 }).map((_, i) => (
                <Skeleton key={i} className="h-12 w-full" />
              ))}
            </div>
          ) : !members?.length ? (
            <p className="text-muted-foreground py-8 text-center">No members found.</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>User</TableHead>
                  <TableHead>Email</TableHead>
                  <TableHead>Role</TableHead>
                  <TableHead className="w-24" />
                </TableRow>
              </TableHeader>
              <TableBody>
                {members.map((m) => (
                  <TableRow key={m.id}>
                    <TableCell className="font-medium">{m.username}</TableCell>
                    <TableCell className="text-muted-foreground">{m.email}</TableCell>
                    <TableCell>{roleBadge(m.role)}</TableCell>
                    <TableCell>
                      <div className="flex gap-1">
                        <Dialog
                          open={editMember?.id === m.id}
                          onOpenChange={(open) => {
                            if (!open) { setEditMember(null); setNewRole(""); }
                          }}
                        >
                          <DialogTrigger
                            render={
                              <Button
                                variant="ghost"
                                size="icon"
                                onClick={() => { setEditMember(m); setNewRole(m.role); }}
                                disabled={m.role === "owner"}
                              >
                                {m.role === "owner" ? <ShieldOff className="h-4 w-4" /> : <Shield className="h-4 w-4" />}
                              </Button>
                            }
                          />
                          <DialogContent>
                            <DialogHeader>
                              <DialogTitle>Change Role — {m.username}</DialogTitle>
                            </DialogHeader>
                            <div className="space-y-4">
                              <div className="space-y-2">
                                <Label htmlFor="role">Role</Label>
                                <Select value={newRole} onValueChange={(v) => v && setNewRole(v)}>
                                  <SelectTrigger>
                                    <SelectValue />
                                  </SelectTrigger>
                                  <SelectContent>
                                    {roles?.map((r) => (
                                      <SelectItem key={r.id} value={r.name}>
                                        {r.name}
                                      </SelectItem>
                                    ))}
                                  </SelectContent>
                                </Select>
                              </div>
                              <Button
                                onClick={() =>
                                  updateMutation.mutate({ userId: m.user_id, role: newRole })
                                }
                                disabled={newRole === m.role || updateMutation.isPending}
                                className="w-full"
                              >
                                Save
                              </Button>
                            </div>
                          </DialogContent>
                        </Dialog>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => {
                            if (confirm(`Remove ${m.username} from organization?`)) {
                              removeMutation.mutate(m.user_id);
                            }
                          }}
                          disabled={m.role === "owner"}
                        >
                          <Trash2 className="h-4 w-4 text-destructive" />
                        </Button>
                      </div>
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
