// User tier types
export type UserTier = 'free' | 'developer' | 'pro' | 'enterprise';

export interface TierConfig {
  name: string;
  apiKey: string;
  rateLimit: number;
  dailyQuota: number;
  color: string;
  canGenerate: boolean;
  canBatchGenerate: boolean;
}

// Rate limit types
export interface RateLimitHeaders {
  limit: number;
  remaining: number;
  reset: number;
  window: number;
}

// API Response wrapper
export interface ApiResponse<T> {
  data: T;
  status: number;
  statusText: string;
  headers: Record<string, string>;
  rateLimitHeaders: RateLimitHeaders | null;
  requestId: string | null;
  duration: number;
}

// Job types
export type JobStatus = 'pending' | 'queued' | 'processing' | 'completed' | 'failed' | 'cancelled' | 'expired';

export interface Job {
  job_id: string;
  status: JobStatus;
  queue_position: number | null;
  estimated_wait: string | null;
  progress: number | null;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  video_id: string | null;
  error: string | null;
}

// Generation request
export interface GenerationRequest {
  prompt: string;
  duration?: number;
  resolution?: string;
  style?: string;
  aspect_ratio?: string;
}

// Account types
export interface Account {
  user_id: string;
  email: string;
  tier: string;
  created_at: string;
  is_active: boolean;
}

export interface Usage {
  user_id: string;
  tier: string;
  period: string;
  requests_made: number;
  videos_generated: number;
  total_duration_seconds: number;
  period_start: string;
  period_end: string;
}

export interface Quota {
  user_id: string;
  tier: string;
  rate_limit: {
    limit: number;
    remaining: number;
    reset: number;
    window_seconds: number;
  };
  daily_quota: {
    limit: number | string;
    used: number;
    remaining: number | string;
  };
  concurrent_jobs: {
    limit: number;
    active: number;
    available: number;
  };
  max_video_duration: number;
  can_generate: boolean;
  can_batch_generate: boolean;
}

// Video types
export interface Video {
  id: string;
  title: string;
  description: string;
  duration: number;
  resolution: string;
  status: string;
  url: string | null;
  thumbnail_url: string | null;
  created_at: string;
}

// Error response
export interface ApiError {
  error: {
    code: string;
    message: string;
    details?: Record<string, unknown>;
    request_id?: string;
  };
}

// Request log entry
export interface RequestLogEntry {
  id: string;
  timestamp: Date;
  method: 'GET' | 'POST' | 'DELETE';
  endpoint: string;
  status: number;
  duration: number;
  tier: UserTier;
  rateLimitRemaining: number | null;
  error?: string;
}

// Dashboard types (from WebSocket)
export interface QueueJob {
  job_id: string;
  enqueued_at: number;
  user_id?: string;
  prompt?: string;
  priority?: string;
}

export interface QueueInfo {
  length: number;
  weight: number;
  jobs: QueueJob[];
}

export interface UserRateLimit {
  user_id: string;
  tier: string;
  limit: number;
  remaining: number;
  reset_at: number;
  is_rate_limited: boolean;
}

export interface ActiveJob {
  job_id: string;
  user_id: string;
  status: string;
  priority: string;
  created_at: string | null;
  started_at: string | null;
  progress: number | null;
  prompt: string;
}

export interface DashboardData {
  queues: {
    critical: QueueInfo;
    high: QueueInfo;
    normal: QueueInfo;
  };
  total_queued: number;
  rate_limits: Record<string, UserRateLimit>;
  active_jobs: ActiveJob[];
  recent_requests: RequestLogEntry[];
}

// WebSocket message types
export type WebSocketMessageType = 'connected' | 'update' | 'error';

export interface WebSocketMessage {
  type: WebSocketMessageType;
  data?: DashboardData;
  timestamp: string;
  error?: string;
}
