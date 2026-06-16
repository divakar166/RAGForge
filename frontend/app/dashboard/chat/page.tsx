"use client";

import { useState, useRef, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Send, Plus, MessageSquare, Trash2, PanelLeftClose, PanelLeft } from "lucide-react";
import { api } from "@/lib/api";
import type { ConversationThread, ConversationMessage } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Textarea } from "@/components/ui/textarea";
import { Skeleton } from "@/components/ui/skeleton";
import { toast } from "sonner";
import { formatDistanceToNow } from "@/lib/format";
import { cn } from "@/lib/utils";

export default function ChatPage() {
  const queryClient = useQueryClient();
  const [activeId, setActiveId] = useState<string | null>(null);
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<ConversationMessage[]>([]);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const { data: threads, isLoading: threadsLoading } = useQuery({
    queryKey: ["conversations"],
    queryFn: () => api.listConversations(),
  });

  const { data: conversation } = useQuery({
    queryKey: ["conversation", activeId],
    queryFn: () => api.getConversation(activeId!),
    enabled: !!activeId,
  });

  useEffect(() => {
    if (conversation) {
      setMessages(conversation.messages);
    }
  }, [conversation]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const createMutation = useMutation({
    mutationFn: () => api.createConversation({}),
    onSuccess: (thread) => {
      queryClient.invalidateQueries({ queryKey: ["conversations"] });
      setActiveId(thread.id);
      setMessages([]);
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const askMutation = useMutation({
    mutationFn: (query: string) => api.askWithConversation(query, activeId ?? undefined),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ["conversations"] });
      if (activeId) {
        queryClient.invalidateQueries({ queryKey: ["conversation", activeId] });
      }
      setMessages((prev) => [
        ...prev,
        {
          id: result.trace_id || crypto.randomUUID(),
          query: result.query,
          answer: result.answer,
          citations: result.citations as unknown as Record<string, unknown>[],
          feedback_score: null,
          created_at: new Date().toISOString(),
        },
      ]);
      setInput("");
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.deleteConversation(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["conversations"] });
      if (activeId) {
        setActiveId(null);
        setMessages([]);
      }
      toast.success("Conversation deleted");
    },
    onError: (err: Error) => toast.error(err.message),
  });

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!input.trim()) return;

    if (!activeId) {
      createMutation.mutate(undefined, {
        onSuccess: (thread) => {
          setActiveId(thread.id);
          askMutation.mutate(input);
        },
      });
      return;
    }

    askMutation.mutate(input);
  }

  const isPending = askMutation.isPending || createMutation.isPending;

  return (
    <div className="flex h-[calc(100vh-8rem)] -mx-6 -mt-6">
      {/* Sidebar */}
      <div className={cn(
        "border-r bg-muted/30 flex flex-col transition-all duration-200",
        sidebarOpen ? "w-72" : "w-0 overflow-hidden",
      )}>
        <div className="flex items-center justify-between p-4 border-b">
          <h2 className="font-semibold text-sm">Chats</h2>
          <Button variant="ghost" size="icon" onClick={() => setSidebarOpen(false)}>
            <PanelLeftClose className="h-4 w-4" />
          </Button>
        </div>
        <div className="p-2">
          <Button
            variant="secondary"
            className="w-full justify-start gap-2 mb-2"
            size="sm"
            onClick={() => createMutation.mutate()}
          >
            <Plus className="h-4 w-4" />
            New Chat
          </Button>
        </div>
        <ScrollArea className="flex-1">
          {threadsLoading ? (
            <div className="space-y-2 p-2">
              {Array.from({ length: 5 }).map((_, i) => (
                <Skeleton key={i} className="h-10 w-full" />
              ))}
            </div>
          ) : (
            <div className="space-y-1 p-2">
              {threads?.map((t) => (
                <div
                  key={t.id}
                  className={cn(
                    "flex items-center gap-2 rounded-lg px-3 py-2 text-sm cursor-pointer group",
                    activeId === t.id
                      ? "bg-primary/10 text-primary"
                      : "hover:bg-muted",
                  )}
                  onClick={() => { setActiveId(t.id); setMessages([]); }}
                >
                  <MessageSquare className="h-4 w-4 shrink-0" />
                  <span className="truncate flex-1">{t.title}</span>
                  <span className="text-xs text-muted-foreground shrink-0">
                    {t.message_count}
                  </span>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-6 w-6 opacity-0 group-hover:opacity-100 shrink-0"
                    onClick={(e) => {
                      e.stopPropagation();
                      deleteMutation.mutate(t.id);
                    }}
                  >
                    <Trash2 className="h-3 w-3 text-destructive" />
                  </Button>
                </div>
              ))}
            </div>
          )}
        </ScrollArea>
      </div>

      {/* Main chat area */}
      <div className="flex-1 flex flex-col min-w-0">
        {!sidebarOpen && (
          <div className="p-2 border-b">
            <Button variant="ghost" size="icon" onClick={() => setSidebarOpen(true)}>
              <PanelLeft className="h-4 w-4" />
            </Button>
          </div>
        )}

        <ScrollArea className="flex-1 p-4">
          {!activeId && messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-muted-foreground gap-4">
              <MessageSquare className="h-16 w-16" />
              <p className="text-lg">Start a conversation</p>
              <p className="text-sm">Ask questions about your documents</p>
            </div>
          ) : messages.length === 0 && isPending ? (
            <div className="space-y-4">
              <Skeleton className="h-20 w-3/4" />
              <Skeleton className="h-32 w-full" />
            </div>
          ) : (
            <div className="space-y-6 max-w-3xl mx-auto">
              {messages.map((m) => (
                <div key={m.id} className="space-y-3">
                  {/* User query */}
                  <div className="flex justify-end">
                    <div className="bg-primary text-primary-foreground rounded-2xl rounded-br-sm px-4 py-2.5 max-w-[75%]">
                      <p className="text-sm">{m.query}</p>
                    </div>
                  </div>
                  {/* Assistant answer */}
                  <div className="flex justify-start">
                    <div className="bg-muted rounded-2xl rounded-bl-sm px-4 py-2.5 max-w-[85%]">
                      <p className="text-sm whitespace-pre-wrap">{m.answer}</p>
                      {m.citations && m.citations.length > 0 && (
                        <div className="mt-2 pt-2 border-t border-border/50">
                          <p className="text-xs text-muted-foreground mb-1">Sources:</p>
                          <div className="flex flex-wrap gap-1">
                            {m.citations.slice(0, 3).map((c, i) => (
                              <span key={i} className="text-xs bg-background rounded px-1.5 py-0.5">
                                {(c as { document_filename?: string }).document_filename || "Source"}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                      <p className="text-xs text-muted-foreground mt-1">
                        {formatDistanceToNow(m.created_at)}
                      </p>
                    </div>
                  </div>
                </div>
              ))}
              {isPending && (
                <div className="flex justify-start">
                  <div className="bg-muted rounded-2xl rounded-bl-sm px-4 py-3">
                    <div className="flex gap-1">
                      <span className="w-2 h-2 bg-foreground/30 rounded-full animate-bounce" />
                      <span className="w-2 h-2 bg-foreground/30 rounded-full animate-bounce [animation-delay:0.1s]" />
                      <span className="w-2 h-2 bg-foreground/30 rounded-full animate-bounce [animation-delay:0.2s]" />
                    </div>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          )}
        </ScrollArea>

        <div className="border-t p-4">
          <form onSubmit={handleSubmit} className="flex gap-2 max-w-3xl mx-auto">
            <Textarea
              placeholder={activeId ? "Ask a follow-up..." : "Start a new conversation..."}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              className="min-h-[2.5rem] max-h-32"
              rows={1}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleSubmit(e);
                }
              }}
            />
            <Button type="submit" disabled={isPending || !input.trim()} className="shrink-0">
              <Send className="h-4 w-4" />
            </Button>
          </form>
        </div>
      </div>
    </div>
  );
}
