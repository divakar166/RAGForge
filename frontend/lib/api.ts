"use client";

import type {
  AuthTokens,
  Document,
  DocumentAccessUpdate,
  EvaluationResult,
  FeedbackBody,
  LoginBody,
  PaginatedResponse,
  RAGResponse,
  RegisterBody,
  Role,
  SearchHistoryItem,
  SearchResponse,
  User,
} from "./types";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

class ApiClient {
  private accessToken: string | null = null;
  private refreshToken: string | null = null;
  private refreshPromise: Promise<void> | null = null;

  constructor() {
    if (typeof window !== "undefined") {
      this.accessToken = localStorage.getItem("access_token");
      this.refreshToken = localStorage.getItem("refresh_token");
    }
  }

  setTokens(tokens: AuthTokens) {
    this.accessToken = tokens.access_token;
    this.refreshToken = tokens.refresh_token;
    if (typeof window !== "undefined") {
      localStorage.setItem("access_token", tokens.access_token);
      localStorage.setItem("refresh_token", tokens.refresh_token);
    }
  }

  clearTokens() {
    this.accessToken = null;
    this.refreshToken = null;
    if (typeof window !== "undefined") {
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
    }
  }

  getAccessToken() {
    return this.accessToken;
  }

  private async refreshAccessToken() {
    if (!this.refreshToken) throw new Error("No refresh token");

    const res = await fetch(`${BASE_URL}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: this.refreshToken }),
    });

    if (!res.ok) {
      this.clearTokens();
      throw new Error("Session expired");
    }

    const tokens: AuthTokens = await res.json();
    this.setTokens(tokens);
  }

  private async request<T>(
    path: string,
    options: RequestInit = {},
  ): Promise<T> {
    const headers: Record<string, string> = {
      ...(options.headers as Record<string, string>),
    };

    if (this.accessToken) {
      headers["Authorization"] = `Bearer ${this.accessToken}`;
    }

    if (!(options.body instanceof FormData)) {
      headers["Content-Type"] = "application/json";
    }

    let res = await fetch(`${BASE_URL}${path}`, {
      ...options,
      headers,
    });

    if (res.status === 401 && this.refreshToken) {
      if (!this.refreshPromise) {
        this.refreshPromise = this.refreshAccessToken().finally(() => {
          this.refreshPromise = null;
        });
      }
      await this.refreshPromise;

      headers["Authorization"] = `Bearer ${this.accessToken}`;
      res = await fetch(`${BASE_URL}${path}`, {
        ...options,
        headers,
      });
    }

    if (!res.ok) {
      const error = await res.json().catch(() => ({ detail: res.statusText }));
      throw new ApiRequestError(res.status, error.detail ?? "Request failed");
    }

    if (res.status === 204) return undefined as T;
    return res.json();
  }

  get<T>(path: string) {
    return this.request<T>(path, { method: "GET" });
  }

  post<T>(path: string, body?: unknown) {
    return this.request<T>(path, {
      method: "POST",
      body: body instanceof FormData ? body : JSON.stringify(body),
    });
  }

  patch<T>(path: string, body?: unknown) {
    return this.request<T>(path, {
      method: "PATCH",
      body: JSON.stringify(body),
    });
  }

  delete<T>(path: string) {
    return this.request<T>(path, { method: "DELETE" });
  }

  upload<T>(path: string, formData: FormData) {
    return this.request<T>(path, {
      method: "POST",
      body: formData,
    });
  }

  // Auth
  register(body: RegisterBody) {
    return this.post<AuthTokens>("/auth/register", body);
  }

  async login(body: LoginBody) {
    const tokens = await this.post<AuthTokens>("/auth/login", body);
    this.setTokens(tokens);
    return tokens;
  }

  async logout() {
    this.clearTokens();
  }

  getMe() {
    return this.get<User>("/auth/me");
  }

  // Users (admin)
  listUsers() {
    return this.get<User[]>("/users");
  }

  getUser(id: string) {
    return this.get<User>(`/users/${id}`);
  }

  assignRoles(userId: string, roleIds: string[]) {
    return this.post<User>(`/users/${userId}/roles`, { role_ids: roleIds });
  }

  // Roles (admin)
  listRoles() {
    return this.get<Role[]>("/roles");
  }

  createRole(body: { name: string; description: string; permission_ids: string[] }) {
    return this.post<Role>("/roles", body);
  }

  deleteRole(id: string) {
    return this.delete<void>(`/roles/${id}`);
  }

  listPermissions() {
    return this.get<{ id: string; name: string; description: string }[]>("/roles/permissions");
  }

  // Documents
  uploadDocument(file: File, isPublic = false) {
    const fd = new FormData();
    fd.append("file", file);
    fd.append("is_public", String(isPublic));
    return this.upload<Document>("/documents/upload", fd);
  }

  listDocuments(page = 1, perPage = 20) {
    return this.get<PaginatedResponse<Document>>(`/documents?page=${page}&per_page=${perPage}`);
  }

  getDocument(id: string) {
    return this.get<Document>(`/documents/${id}`);
  }

  deleteDocument(id: string) {
    return this.delete<void>(`/documents/${id}`);
  }

  setDocumentAccess(id: string, body: DocumentAccessUpdate) {
    return this.post<Document>(`/documents/${id}/access`, body);
  }

  // Search
  search(query: string, topK = 5) {
    return this.post<SearchResponse>("/search/query", { query, top_k: topK });
  }

  ask(query: string, topK = 5, stream = false) {
    return this.post<RAGResponse>("/search/ask", { query, top_k: topK, stream });
  }

  getSearchHistory() {
    return this.get<SearchHistoryItem[]>("/search/history");
  }

  submitFeedback(body: FeedbackBody) {
    return this.post<void>("/search/feedback", body);
  }

  // Evaluation
  runEvaluation() {
    return this.post<EvaluationResult[]>("/evaluate/run");
  }

  getDataset() {
    return this.get<{ name: string; size: number }>("/evaluate/dataset");
  }

  // Health
  health() {
    return this.get<{ status: string }>("/health");
  }
}

export class ApiRequestError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiRequestError";
  }
}

export const api = new ApiClient();
