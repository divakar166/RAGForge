export interface OrgInfo {
  id: string;
  name: string;
  slug: string;
  role: "owner" | "admin" | "member";
}

export interface User {
  id: string;
  email: string;
  username: string;
  is_active: boolean;
  is_superuser: boolean;
  organizations: OrgInfo[];
  created_at: string;
  updated_at: string;
}

export interface Document {
  id: string;
  title: string;
  filename: string;
  file_type: string;
  file_size: number;
  status: string;
  allowed_roles: string[];
  uploaded_by_id: string;
  organization_id: string;
  collection_id: string | null;
  chunk_count: number;
  created_at: string;
  updated_at: string;
}

export interface DocumentAccessUpdate {
  allowed_roles?: string[];
}

export interface Collection {
  id: string;
  organization_id: string;
  name: string;
  description: string;
  is_public: boolean;
  document_count: number;
  created_at: string;
  updated_at: string;
}

export interface ConversationThread {
  id: string;
  title: string;
  message_count: number;
  created_at: string;
}

export interface ConversationMessage {
  id: string;
  query: string;
  answer: string;
  citations: Record<string, unknown>[] | null;
  feedback_score: number | null;
  created_at: string;
}

export interface ConversationDetail {
  id: string;
  title: string;
  messages: ConversationMessage[];
}

export interface SearchResult {
  score: number;
  text: string;
  content: string;
  document_id: string;
  document_filename: string;
  doc_title: string;
  chunk_index: number;
  section_path: string | null;
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
  answer: string;
  feedback_score: number | null;
  created_at: string;
}

export interface FeedbackBody {
  trace_id: string;
  score: "thumbs_up" | "thumbs_down" | number;
  comment?: string;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface RegisterResponse {
  id: string;
  email: string;
  username: string;
  org_id: string;
  org_name: string;
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface RegisterBody {
  email: string;
  password: string;
  username: string;
  org_name: string;
  org_slug: string;
}

export interface LoginBody {
  username?: string;
  email?: string;
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

export interface InviteVerifyResponse {
  valid: boolean;
  email: string;
  role: string;
  org_name: string;
}

export interface ApiError {
  detail: string;
}

// --- Org-scoped member/invite types ---

export interface Member {
  id: string;
  user_id: string;
  email: string;
  username: string;
  role: string;
  is_active: boolean;
  created_at: string;
}

export interface MemberUpdate {
  role?: string;
  is_active?: boolean;
}

export interface InviteRequest {
  email: string;
  role: string;
}

export interface Invitation {
  id: string;
  organization_id: string;
  email: string;
  role: string;
  token: string;
  expires_at: string;
  accepted_at: string | null;
}
