"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, Pencil, Trash2, ShieldCheck } from "lucide-react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { toast } from "sonner";
import type { OrgRole } from "@/lib/types";
import { PERMISSION_OPTIONS } from "@/lib/types";

const PERMISSION_LABELS: Record<string, string> = {
  "documents:create": "Create Documents",
  "documents:read": "Read Documents",
  "documents:update": "Update Documents",
  "documents:delete": "Delete Documents",
  "documents:download": "Download Documents",
  "search:query": "Search & Ask",
  "collections:manage": "Manage Collections",
  "members:manage": "Manage Members",
  "invites:manage": "Manage Invitations",
  "audit:view": "View Audit Log",
  "evaluate:run": "Run Evaluations",
  "roles:manage": "Manage Roles",
  "settings:manage": "Manage Settings",
};

function RoleForm({
  role,
  onSave,
  onCancel,
  saving,
}: {
  role?: OrgRole;
  onSave: (data: { name: string; description: string; permissions: string[] }) => void;
  onCancel: () => void;
  saving: boolean;
}) {
  const [name, setName] = useState(role?.name ?? "");
  const [description, setDescription] = useState(role?.description ?? "");
  const [permissions, setPermissions] = useState<string[]>(role?.permissions ?? ["documents:read", "search:query"]);

  const togglePermission = (perm: string) => {
    setPermissions((p) =>
      p.includes(perm) ? p.filter((x) => x !== perm) : [...p, perm],
    );
  };

  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <Label>Role Name</Label>
        <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. compliance-officer" disabled={role?.is_system} />
      </div>
      <div className="space-y-2">
        <Label>Description</Label>
        <Textarea value={description} onChange={(e) => setDescription(e.target.value)} placeholder="What this role can do" disabled={role?.is_system} />
      </div>
      <div className="space-y-2">
        <Label className="text-base font-medium">Permissions</Label>
        <p className="text-xs text-muted-foreground">Choose what members with this role can do</p>
        <div className="grid gap-2 sm:grid-cols-2">
          {PERMISSION_OPTIONS.map((perm) => (
            <div key={perm} className="flex items-center gap-2">
              <Checkbox
                id={`perm-${perm}`}
                checked={permissions.includes(perm)}
                onCheckedChange={() => togglePermission(perm)}
              />
              <Label htmlFor={`perm-${perm}`} className="text-sm cursor-pointer">
                {PERMISSION_LABELS[perm] ?? perm}
              </Label>
            </div>
          ))}
        </div>
      </div>
      <div className="flex gap-2">
        <Button onClick={() => onSave({ name, description, permissions })} disabled={!name || saving}>
          {saving ? "Saving..." : role ? "Update Role" : "Create Role"}
        </Button>
        <Button variant="outline" onClick={onCancel}>Cancel</Button>
      </div>
    </div>
  );
}

export default function AdminRolesPage() {
  const queryClient = useQueryClient();
  const [editingRole, setEditingRole] = useState<OrgRole | null>(null);
  const [creating, setCreating] = useState(false);

  const { data: roles, isLoading } = useQuery({
    queryKey: ["org-roles"],
    queryFn: () => api.listOrgRoles(),
  });

  const createMutation = useMutation({
    mutationFn: (data: { name: string; description: string; permissions: string[] }) => api.createOrgRole(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["org-roles"] });
      toast.success("Role created");
      setCreating(false);
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: { name?: string; description?: string; permissions?: string[] } }) =>
      api.updateOrgRole(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["org-roles"] });
      toast.success("Role updated");
      setEditingRole(null);
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.deleteOrgRole(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["org-roles"] });
      toast.success("Role deleted");
    },
    onError: (err: Error) => toast.error(err.message),
  });

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-32 w-full" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold">Roles</h1>
        <Button onClick={() => setCreating(true)} disabled={creating}>
          <Plus className="mr-2 h-4 w-4" />
          New Role
        </Button>
      </div>

      {creating && (
        <Card>
          <CardHeader>
            <CardTitle>Create Role</CardTitle>
          </CardHeader>
          <CardContent>
            <RoleForm
              onSave={(data) => createMutation.mutate(data)}
              onCancel={() => setCreating(false)}
              saving={createMutation.isPending}
            />
          </CardContent>
        </Card>
      )}

      {editingRole && (
        <Card>
          <CardHeader>
            <CardTitle>Edit Role: {editingRole.name}</CardTitle>
          </CardHeader>
          <CardContent>
            <RoleForm
              role={editingRole}
              onSave={(data) => updateMutation.mutate({ id: editingRole.id, data })}
              onCancel={() => setEditingRole(null)}
              saving={updateMutation.isPending}
            />
          </CardContent>
        </Card>
      )}

      <div className="space-y-3">
        {roles?.map((role) => (
          <Card key={role.id}>
            <CardContent className="pt-6">
              <div className="flex items-start justify-between">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <ShieldCheck className="h-4 w-4 text-primary" />
                    <span className="font-semibold">{role.name}</span>
                    {role.is_system && (
                      <Badge variant="secondary" className="text-xs">System</Badge>
                    )}
                    <Badge variant="outline" className="text-xs">
                      {role.member_count} member{role.member_count !== 1 ? "s" : ""}
                    </Badge>
                  </div>
                  {role.description && (
                    <p className="text-sm text-muted-foreground">{role.description}</p>
                  )}
                  <div className="flex flex-wrap gap-1 pt-1">
                    {role.permissions.map((perm) => (
                      <Badge key={perm} variant="outline" className="text-xs">
                        {PERMISSION_LABELS[perm] ?? perm}
                      </Badge>
                    ))}
                  </div>
                </div>
                <div className="flex gap-1">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setEditingRole(role)}
                  >
                    <Pencil className="h-4 w-4" />
                  </Button>
                  {!role.is_system && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => {
                        if (confirm(`Delete role "${role.name}"?`)) {
                          deleteMutation.mutate(role.id);
                        }
                      }}
                    >
                      <Trash2 className="h-4 w-4 text-destructive" />
                    </Button>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
        {roles?.length === 0 && (
          <p className="text-center text-muted-foreground py-8">No roles defined.</p>
        )}
      </div>
    </div>
  );
}
