export type Permission =
  | "document:create"
  | "document:read"
  | "document:update"
  | "document:delete"
  | "search:query"
  | "users:manage"
  | "roles:manage"
  | "evaluate:run"
  | "admin:full";

export interface Role {
  id: string;
  name: string;
  description: string;
  permissions: Permission[];
  created_at: string;
  updated_at: string;
}

export interface User {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  roles: Role[];
  created_at: string;
  updated_at: string;
}

export interface Document {
  id: string;
  filename: string;
  file_type: string;
  file_size: number;
  status: "processing" | "ready" | "failed";
  owner_id: string;
  is_public: boolean;
  allowed_role_ids: string[];
  allowed_user_ids: string[];
  chunk_count: number;
  created_at: string;
  updated_at: string;
}

export interface DocumentAccessUpdate {
  is_public?: boolean;
  allowed_role_ids?: string[];
  allowed_user_ids?: string[];
}

export interface SearchResult {
  id: string;
  score: number;
  text: string;
  metadata: Record<string, unknown>;
  document_id: string;
  document_filename: string;
}

export interface SearchResponse {
  query: string;
  results: SearchResult[];
  total: number;
}

export interface RAGResponse {
  query: string;
  answer: string;
  citations: SearchResult[];
  trace_id: string;
}

export interface SearchHistoryItem {
  id: string;
  query: string;
  type: "search" | "ask";
  created_at: string;
}

export interface FeedbackBody {
  trace_id: string;
  score: "thumbs_up" | "thumbs_down";
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface RegisterBody {
  email: string;
  password: string;
  full_name: string;
}

export interface LoginBody {
  email: string;
  password: string;
}

export interface EvaluationResult {
  metric: string;
  score: number;
  threshold: number;
  passed: boolean;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  per_page: number;
}

export interface ApiError {
  detail: string;
}
