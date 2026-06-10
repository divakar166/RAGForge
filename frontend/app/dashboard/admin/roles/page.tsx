"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
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
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Trash2, Plus } from "lucide-react";
import { toast } from "sonner";

export default function AdminRolesPage() {
  const queryClient = useQueryClient();
  const [createOpen, setCreateOpen] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");

  const { data: roles, isLoading } = useQuery({
    queryKey: ["roles"],
    queryFn: () => api.listRoles(),
  });

  const { data: permissions } = useQuery({
    queryKey: ["permissions"],
    queryFn: () => api.listPermissions(),
  });

  const [selectedPerms, setSelectedPerms] = useState<string[]>([]);

  const createMutation = useMutation({
    mutationFn: () =>
      api.createRole({
        name,
        description,
        permission_ids: selectedPerms,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["roles"] });
      toast.success("Role created");
      setCreateOpen(false);
      setName("");
      setDescription("");
      setSelectedPerms([]);
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.deleteRole(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["roles"] });
      toast.success("Role deleted");
    },
    onError: (err: Error) => toast.error(err.message),
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold">Role Management</h1>
        <Dialog open={createOpen} onOpenChange={setCreateOpen}>
          <DialogTrigger
            render={
              <Button>
                <Plus className="mr-2 h-4 w-4" />
                New Role
              </Button>
            }
          />
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Create Role</DialogTitle>
            </DialogHeader>
            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="roleName">Name</Label>
                <Input
                  id="roleName"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g., editor"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="roleDesc">Description</Label>
                <Input
                  id="roleDesc"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Can edit documents"
                />
              </div>
              <div className="space-y-2">
                <Label>Permissions</Label>
                <div className="space-y-2 max-h-48 overflow-y-auto">
                  {permissions?.map((perm) => (
                    <div key={perm.id} className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        id={`perm-${perm.id}`}
                        checked={selectedPerms.includes(perm.id)}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setSelectedPerms([...selectedPerms, perm.id]);
                          } else {
                            setSelectedPerms(
                              selectedPerms.filter((p) => p !== perm.id),
                            );
                          }
                        }}
                        className="h-4 w-4"
                      />
                      <Label htmlFor={`perm-${perm.id}`}>
                        {perm.name}
                      </Label>
                    </div>
                  ))}
                </div>
              </div>
              <Button
                onClick={() => createMutation.mutate()}
                disabled={!name || createMutation.isPending}
                className="w-full"
              >
                {createMutation.isPending ? "Creating..." : "Create Role"}
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Roles</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-2">
              {Array.from({ length: 3 }).map((_, i) => (
                <Skeleton key={i} className="h-12 w-full" />
              ))}
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Description</TableHead>
                  <TableHead>Permissions</TableHead>
                  <TableHead className="w-16" />
                </TableRow>
              </TableHeader>
              <TableBody>
                {roles?.map((role) => (
                  <TableRow key={role.id}>
                    <TableCell className="font-medium">{role.name}</TableCell>
                    <TableCell className="text-muted-foreground">
                      {role.description}
                    </TableCell>
                    <TableCell>
                      <div className="flex flex-wrap gap-1">
                        {role.permissions.slice(0, 4).map((p) => (
                          <Badge key={p} variant="outline">
                            {p}
                          </Badge>
                        ))}
                        {role.permissions.length > 4 && (
                          <Badge variant="outline">
                            +{role.permissions.length - 4}
                          </Badge>
                        )}
                      </div>
                    </TableCell>
                    <TableCell>
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => deleteMutation.mutate(role.id)}
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
