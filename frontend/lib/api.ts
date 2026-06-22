"use client";

import type {
  AuthTokens,
  Collection,
  ConversationDetail,
  ConversationThread,
  Document,
  DocumentAccessUpdate,
  EvaluationResult,
  FeedbackBody,
  Invitation,
  InviteRequest,
  InviteVerifyResponse,
  LoginBody,
  Member,
  MemberUpdate,
  OrgRole,
  PaginatedResponse,
  RAGResponse,
  RegisterBody,
  RegisterResponse,
  SearchHistoryItem,
  SearchResponse,
  User,
} from "./types";

const BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

class ApiClient {
  private accessToken: string | null = null;
  private refreshToken: string | null = null;
  private refreshPromise: Promise<void> | null = null;
  private _orgId: string | null = null;

  constructor() {
    if (typeof window !== "undefined") {
      this.accessToken = localStorage.getItem("access_token");
      this.refreshToken = localStorage.getItem("refresh_token");
      this._orgId = localStorage.getItem("active_org_id");
    }
  }

  get orgId(): string | null {
    return this._orgId;
  }

  set orgId(id: string | null) {
    this._orgId = id;
    if (typeof window !== "undefined") {
      if (id) {
        localStorage.setItem("active_org_id", id);
      } else {
        localStorage.removeItem("active_org_id");
      }
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
    this._orgId = null;
    if (typeof window !== "undefined") {
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      localStorage.removeItem("active_org_id");
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
    return this.post<RegisterResponse>("/auth/register", body);
  }

  async login(body: LoginBody) {
    const tokens = await this.post<AuthTokens>("/auth/login", body);
    this.setTokens(tokens);
    return tokens;
  }

  selectOrg(orgId: string) {
    return this.post<AuthTokens>("/auth/select-org", { org_id: orgId });
  }

  async logout() {
    this.clearTokens();
  }

  getMe() {
    return this.get<User>("/auth/me");
  }

  // Users (admin, non-org-scoped)

  listUsers() {
    return this.get<User[]>("/users");
  }

  getUser(id: string) {
    return this.get<User>(`/users/${id}`);
  }

  updateUser(
    id: string,
    data: { is_active?: boolean; is_superuser?: boolean },
  ) {
    return this.patch<{ detail: string }>(`/users/${id}`, data);
  }

  // Org-scoped helpers

  private orgPath(path: string): string {
    if (!this._orgId) throw new Error("No active organization");
    return `/orgs/${this._orgId}${path}`;
  }

  // Documents

  uploadDocument(file: File, classification?: string, collectionId?: string) {
    const fd = new FormData();
    fd.append("file", file);
    if (classification) fd.append("classification", classification);
    if (collectionId) fd.append("collection_id", collectionId);
    return this.upload<Document>(`${this.orgPath("/documents/upload")}`, fd);
  }

  listDocuments(page = 1, perPage = 20) {
    return this.get<PaginatedResponse<Document>>(
      `${this.orgPath("/documents")}?page=${page}&per_page=${perPage}`,
    );
  }

  getDocument(id: string) {
    return this.get<Document>(this.orgPath(`/documents/${id}`));
  }

  deleteDocument(id: string) {
    return this.delete<void>(this.orgPath(`/documents/${id}`));
  }

  setDocumentAccess(id: string, body: DocumentAccessUpdate) {
    return this.post<{ detail: string }>(
      this.orgPath(`/documents/${id}/access`),
      body,
    );
  }

  updateDocument(
    id: string,
    body: {
      collection_id?: string | null;
      title?: string;
      classification?: string;
    },
  ) {
    return this.patch<Document>(this.orgPath(`/documents/${id}`), body);
  }

  // Search

  search(query: string, topK = 5) {
    return this.post<SearchResponse>(this.orgPath("/search/query"), {
      query,
      top_k: topK,
    });
  }

  ask(query: string, topK = 5) {
    return this.post<RAGResponse>(this.orgPath("/search/ask"), {
      query,
      top_k: topK,
    });
  }

  getSearchHistory() {
    return this.get<SearchHistoryItem[]>(this.orgPath("/search/history"));
  }

  submitFeedback(body: FeedbackBody) {
    return this.post<void>(this.orgPath("/search/feedback"), body);
  }

  // Members

  listMembers() {
    return this.get<Member[]>(this.orgPath("/members"));
  }

  updateMember(userId: string, data: MemberUpdate) {
    return this.patch<{ detail: string }>(
      this.orgPath(`/members/${userId}`),
      data,
    );
  }

  removeMember(userId: string) {
    return this.delete<{ detail: string }>(this.orgPath(`/members/${userId}`));
  }

  // Invitations

  inviteMember(body: InviteRequest) {
    return this.post<Invitation>(this.orgPath("/invites"), body);
  }

  listInvitations() {
    return this.get<Invitation[]>(this.orgPath("/invites"));
  }

  // Audit

  getAuditLogs(page = 1, perPage = 50) {
    return this.get<unknown[]>(
      `${this.orgPath("/audit")}?page=${page}&per_page=${perPage}`,
    );
  }

  // Evaluation

  runEvaluation() {
    return this.post<EvaluationResult[]>("/evaluate/run");
  }

  getDataset() {
    return this.get<{ name: string; size: number }>("/evaluate/dataset");
  }

  // Collections

  listCollections() {
    return this.get<Collection[]>(this.orgPath("/collections"));
  }

  createCollection(data: { name: string; description?: string }) {
    return this.post<Collection>(this.orgPath("/collections"), data);
  }

  getCollection(id: string) {
    return this.get<Collection>(this.orgPath(`/collections/${id}`));
  }

  deleteCollection(id: string) {
    return this.delete<void>(this.orgPath(`/collections/${id}`));
  }

  //  Conversations

  listConversations() {
    return this.get<ConversationThread[]>(this.orgPath("/conversations"));
  }

  createConversation(data: { title?: string }) {
    return this.post<ConversationThread>(this.orgPath("/conversations"), data);
  }

  getConversation(id: string) {
    return this.get<ConversationDetail>(this.orgPath(`/conversations/${id}`));
  }

  deleteConversation(id: string) {
    return this.delete<void>(this.orgPath(`/conversations/${id}`));
  }

  askWithConversation(query: string, conversationId?: string) {
    return this.post<RAGResponse>(this.orgPath("/search/ask"), {
      query,
      top_k: 5,
      conversation_id: conversationId,
    });
  }

  // Document Download

  async downloadDocument(id: string): Promise<Blob> {
    const headers: Record<string, string> = {};
    if (this.accessToken) {
      headers["Authorization"] = `Bearer ${this.accessToken}`;
    }
    const res = await fetch(
      `${BASE_URL}${this.orgPath(`/documents/${id}/download`)}`,
      { headers },
    );
    if (!res.ok) throw new Error("Download failed");
    return res.blob();
  }

  // Health

  health() {
    return this.get<{ status: string }>("/health");
  }

  // Org Roles

  listOrgRoles() {
    return this.get<OrgRole[]>(this.orgPath("/roles"));
  }

  getOrgRole(id: string) {
    return this.get<OrgRole>(this.orgPath(`/roles/${id}`));
  }

  createOrgRole(body: {
    name: string;
    description?: string | null;
    permissions: string[];
  }) {
    return this.post<OrgRole>(this.orgPath("/roles"), body);
  }

  updateOrgRole(
    id: string,
    body: {
      name?: string;
      description?: string | null;
      permissions?: string[];
    },
  ) {
    return this.patch<OrgRole>(this.orgPath(`/roles/${id}`), body);
  }

  deleteOrgRole(id: string) {
    return this.delete<{ detail: string }>(this.orgPath(`/roles/${id}`));
  }

  // Invites

  verifyInvite(token: string) {
    return this.get<InviteVerifyResponse>(`/invites/verify/${token}`);
  }

  registerWithInvite(body: {
    invitation_token: string;
    email: string;
    username: string;
    password: string;
  }) {
    return this.post<RegisterResponse>("/auth/register-with-invite", body);
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
