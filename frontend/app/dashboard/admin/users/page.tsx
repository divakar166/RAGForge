"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "@/lib/api";
import type { User } from "@/lib/types";
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
import { toast } from "sonner";

export default function AdminUsersPage() {
  const queryClient = useQueryClient();

  const { data: users, isLoading } = useQuery({
    queryKey: ["users"],
    queryFn: () => api.listUsers(),
  });

  const { data: roles } = useQuery({
    queryKey: ["roles"],
    queryFn: () => api.listRoles(),
  });

  const [selectedUser, setSelectedUser] = useState<User | null>(null);

  const assignMutation = useMutation({
    mutationFn: ({
      userId,
      roleIds,
    }: {
      userId: string;
      roleIds: string[];
    }) => api.assignRoles(userId, roleIds),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["users"] });
      toast.success("Roles updated");
      setSelectedUser(null);
    },
    onError: (err: Error) => toast.error(err.message),
  });

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">User Management</h1>

      <Card>
        <CardHeader>
          <CardTitle>Users</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-2">
              {Array.from({ length: 5 }).map((_, i) => (
                <Skeleton key={i} className="h-12 w-full" />
              ))}
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Email</TableHead>
                  <TableHead>Roles</TableHead>
                  <TableHead>Active</TableHead>
                  <TableHead className="w-24" />
                </TableRow>
              </TableHeader>
              <TableBody>
                {users?.map((user) => (
                  <TableRow key={user.id}>
                    <TableCell className="font-medium">
                      {user.full_name}
                    </TableCell>
                    <TableCell>{user.email}</TableCell>
                    <TableCell>
                      <div className="flex flex-wrap gap-1">
                        {user.roles.map((role) => (
                          <Badge key={role.id} variant="secondary">
                            {role.name}
                          </Badge>
                        ))}
                      </div>
                    </TableCell>
                    <TableCell>
                      {user.is_active ? (
                        <Badge variant="default">Active</Badge>
                      ) : (
                        <Badge variant="secondary">Inactive</Badge>
                      )}
                    </TableCell>
                    <TableCell>
                      <Dialog
                        open={selectedUser?.id === user.id}
                        onOpenChange={(open) => {
                          if (!open) setSelectedUser(null);
                        }}
                      >
                        <DialogTrigger
                          render={
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => setSelectedUser(user)}
                            >
                              Edit Roles
                            </Button>
                          }
                        />
                        <DialogContent>
                          <DialogHeader>
                            <DialogTitle>
                              Edit Roles — {user.full_name}
                            </DialogTitle>
                          </DialogHeader>
                          <div className="space-y-3">
                            {roles?.map((role) => {
                              const isAssigned = user.roles.some(
                                (r) => r.id === role.id,
                              );
                              return (
                                <div
                                  key={role.id}
                                  className="flex items-center gap-2"
                                >
                                  <input
                                    type="checkbox"
                                    id={`role-${role.id}`}
                                    defaultChecked={isAssigned}
                                    className="h-4 w-4"
                                  />
                                  <Label htmlFor={`role-${role.id}`}>
                                    {role.name}
                                  </Label>
                                </div>
                              );
                            })}
                            {roles?.length === 0 && (
                              <p className="text-sm text-muted-foreground">
                                No roles available
                              </p>
                            )}
                          </div>
                          <Button
                            onClick={() => {
                              const checkedRoles =
                                document.querySelectorAll<HTMLInputElement>(
                                  'input[type="checkbox"]:checked',
                                );
                              const roleIds = Array.from(checkedRoles).map(
                                (cb) => cb.id.replace("role-", ""),
                              );
                              assignMutation.mutate({
                                userId: user.id,
                                roleIds,
                              });
                            }}
                            className="w-full"
                          >
                            Save Roles
                          </Button>
                        </DialogContent>
                      </Dialog>
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
