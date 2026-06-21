export interface Session {
  session_id: number;
  user_id: number;
  title: string | null;
  is_active: boolean;
  archived_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface RequestCreated {
  request_id: number;
  session_id: number;
  status: string;
  created_at: string;
}

export interface RequestResult {
  code: string | null;
  error: Record<string, string> | null;
  artifact_url: string | null;
  attempts: number;
  agent_state: Record<string, unknown> | null;
}

export interface StageInfo {
  name: string | null;
  attempt: number;
  max_attempts: number;
  latest_code: string | null;
  latest_error: Record<string, string> | null;
}

export interface TimestampsInfo {
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
}

export interface RequestStatus {
  request_id: number;
  session_id: number;
  status: string;
  stage: StageInfo | null;
  prompt: string;
  timestamps: TimestampsInfo;
  result: RequestResult | null;
}

export interface SessionHistoryItem {
  request_id: number;
  prompt: string;
  status: string;
  created_at: string;
  completed_at: string | null;
}

export interface SessionHistory {
  session_id: number;
  total_count: number;
  cursor: number | null;
  next_cursor: number | null;
  items: SessionHistoryItem[];
}
