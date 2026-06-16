"use client";

import { Suspense } from "react";
import { useState } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { useSearchParams, useRouter } from "next/navigation";
import { api, ApiRequestError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { toast } from "sonner";

function InviteContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const token = searchParams.get("token");

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [accepted, setAccepted] = useState(false);

  const { data: invite, isLoading, isError } = useQuery({
    queryKey: ["invite", token],
    queryFn: () => api.verifyInvite(token!),
    enabled: !!token,
  });

  const acceptMutation = useMutation({
    mutationFn: (body: { invitation_token: string; email: string; username: string; password: string }) =>
      api.registerWithInvite(body),
    onSuccess: () => {
      setAccepted(true);
      toast.success("Account created! Redirecting...");
      setTimeout(() => router.push("/dashboard"), 1500);
    },
    onError: (err: ApiRequestError) => toast.error(err.message),
  });

  if (!token) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Card className="w-full max-w-md">
          <CardContent className="py-8 text-center text-muted-foreground">
            Invalid invitation link — no token provided.
          </CardContent>
        </Card>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Card className="w-full max-w-md">
          <CardContent className="space-y-4 py-8">
            <Skeleton className="h-6 w-48" />
            <Skeleton className="h-4 w-64" />
          </CardContent>
        </Card>
      </div>
    );
  }

  if (isError || !invite?.valid) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Card className="w-full max-w-md">
          <CardContent className="py-8 text-center text-muted-foreground">
            This invitation link is invalid or has expired.
          </CardContent>
        </Card>
      </div>
    );
  }

  if (accepted) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Card className="w-full max-w-md">
          <CardContent className="py-8 text-center">
            <p className="text-lg font-medium">Account created successfully!</p>
            <p className="text-sm text-muted-foreground mt-1">Redirecting to dashboard...</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    acceptMutation.mutate({
      invitation_token: token,
      email: invite.email,
      username,
      password,
    });
  };

  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <CardTitle>Join {invite.org_name}</CardTitle>
          <p className="text-sm text-muted-foreground mt-1">
            You&apos;ve been invited as <strong>{invite.role}</strong>
          </p>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label>Email</Label>
              <Input value={invite.email} disabled />
            </div>
            <div className="space-y-2">
              <Label htmlFor="username">Username</Label>
              <Input
                id="username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="Choose a username"
                required
                minLength={3}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="At least 8 characters"
                required
                minLength={8}
              />
            </div>
            <Button
              type="submit"
              className="w-full"
              disabled={!username || !password || acceptMutation.isPending}
            >
              {acceptMutation.isPending ? "Creating account..." : "Accept Invitation"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}

export default function InvitePage() {
  return (
    <Suspense fallback={
      <div className="flex min-h-screen items-center justify-center">
        <Card className="w-full max-w-md">
          <CardContent className="space-y-4 py-8">
            <Skeleton className="h-6 w-48" />
            <Skeleton className="h-4 w-64" />
          </CardContent>
        </Card>
      </div>
    }>
      <InviteContent />
    </Suspense>
  );
}
