"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Send, Search, FileText } from "lucide-react";
import { api } from "@/lib/api";
import type { SearchResponse, RAGResponse } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { toast } from "sonner";

export default function SearchPage() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResponse | null>(null);
  const [ragResult, setRagResult] = useState<RAGResponse | null>(null);
  const [tab, setTab] = useState("search");

  const searchMutation = useMutation({
    mutationFn: (q: string) => api.search(q),
    onSuccess: (data) => {
      setResults(data);
      setRagResult(null);
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const askMutation = useMutation({
    mutationFn: (q: string) => api.ask(q),
    onSuccess: (data) => {
      setRagResult(data);
      setResults(null);
      setTab("rag");
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const isPending = searchMutation.isPending || askMutation.isPending;

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!query.trim()) return;

    if (tab === "search") {
      searchMutation.mutate(query);
    } else {
      askMutation.mutate(query);
    }
  }

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold">Search & Ask</h1>

      <Tabs value={tab} onValueChange={setTab}>
        <TabsList>
          <TabsTrigger value="search">Search</TabsTrigger>
          <TabsTrigger value="rag">Ask (RAG)</TabsTrigger>
        </TabsList>
      </Tabs>

      <form onSubmit={handleSubmit} className="flex gap-2">
        <Input
          placeholder={
            tab === "search"
              ? "Search your documents..."
              : "Ask a question about your documents..."
          }
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="flex-1"
        />
        <Button type="submit" disabled={isPending || !query.trim()}>
          {isPending
            ? "Searching..."
            : tab === "search"
              ? <><Search className="mr-2 h-4 w-4" /> Search</>
              : <><Send className="mr-2 h-4 w-4" /> Ask</>}
        </Button>
      </form>

      {isPending && (
        <div className="space-y-3">
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-24 w-full" />
        </div>
      )}

      {results && !isPending && (
        <SearchResults results={results} onAskAgain={() => {
          setQuery(results.query);
          setTab("rag");
          askMutation.mutate(results.query);
        }} />
      )}

      {ragResult && !isPending && (
        <RAGAnswer answer={ragResult} onSearchAgain={() => {
          setQuery(ragResult.query);
          setTab("search");
          searchMutation.mutate(ragResult.query);
        }} />
      )}
    </div>
  );
}

function SearchResults({
  results,
  onAskAgain,
}: {
  results: SearchResponse;
  onAskAgain: () => void;
}) {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">
          Found {results.total} result{results.total !== 1 ? "s" : ""} for
          &ldquo;{results.query}&rdquo;
        </p>
        <Button variant="outline" size="sm" onClick={onAskAgain}>
          <Send className="mr-2 h-4 w-4" />
          Ask RAG
        </Button>
      </div>
      {results.results.map((r, i) => (
        <ResultCard key={r.id} result={r} rank={i + 1} />
      ))}
    </div>
  );
}

function ResultCard({
  result,
  rank,
}: {
  result: { id: string; score: number; text: string; document_filename: string };
  rank: number;
}) {
  return (
    <Card>
      <CardContent className="pt-4">
        <div className="flex items-start gap-3">
          <Badge variant="outline" className="mt-0.5 shrink-0">
            #{rank}
          </Badge>
          <div className="min-w-0 flex-1 space-y-1">
            <p className="text-sm font-medium truncate">
              {result.document_filename}
            </p>
            <p className="text-sm text-muted-foreground line-clamp-3">
              {result.text}
            </p>
            <p className="text-xs text-muted-foreground">
              Score: {result.score.toFixed(4)}
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function RAGAnswer({
  answer,
  onSearchAgain,
}: {
  answer: RAGResponse;
  onSearchAgain: () => void;
}) {
  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Answer</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm leading-relaxed whitespace-pre-wrap">
            {answer.answer}
          </p>
        </CardContent>
      </Card>

      {answer.citations.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">
              Citations ({answer.citations.length})
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <ScrollArea className="max-h-64">
              {answer.citations.map((c) => (
                <div
                  key={c.id}
                  className="rounded border p-3 text-sm mb-2"
                >
                  <div className="flex items-center gap-2 mb-1">
                    <FileText className="h-3 w-3 text-muted-foreground" />
                    <span className="font-medium">{c.document_filename}</span>
                    <Badge variant="outline" className="ml-auto">
                      Score: {c.score.toFixed(3)}
                    </Badge>
                  </div>
                  <p className="text-muted-foreground text-xs">{c.text}</p>
                </div>
              ))}
            </ScrollArea>
          </CardContent>
        </Card>
      )}

      <Button variant="outline" onClick={onSearchAgain}>
        <Search className="mr-2 h-4 w-4" />
        Search instead
      </Button>
    </div>
  );
}
