import { TierConfig, UserTier } from '../types/api';

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
export const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws/dashboard';
export const API_PREFIX = '/v1';

export const TIER_CONFIGS: Record<UserTier, TierConfig> = {
  free: {
    name: 'Free',
    apiKey: 'free_test_key',
    rateLimit: 10,
    dailyQuota: 100,
    color: 'gray',
    canGenerate: false,
    canBatchGenerate: false,
  },
  developer: {
    name: 'Developer',
    apiKey: 'dev_test_key',
    rateLimit: 30,
    dailyQuota: 500,
    color: 'blue',
    canGenerate: true,
    canBatchGenerate: false,
  },
  pro: {
    name: 'Pro',
    apiKey: 'pro_test_key',
    rateLimit: 100,
    dailyQuota: 5000,
    color: 'purple',
    canGenerate: true,
    canBatchGenerate: true,
  },
  enterprise: {
    name: 'Enterprise',
    apiKey: 'enterprise_test_key',
    rateLimit: 1000,
    dailyQuota: -1, // unlimited
    color: 'amber',
    canGenerate: true,
    canBatchGenerate: true,
  },
};

export const STATUS_COLORS: Record<number, string> = {
  200: 'green',
  201: 'green',
  202: 'green',
  204: 'green',
  400: 'orange',
  401: 'orange',
  403: 'red',
  404: 'orange',
  429: 'yellow',
  500: 'red',
  502: 'red',
  503: 'red',
};

export const ENDPOINTS = [
  {
    category: 'Generation',
    endpoints: [
      { method: 'POST' as const, path: '/generate', name: 'Generate Video', tierRequired: 'developer' as UserTier, hasBody: true },
      { method: 'POST' as const, path: '/generate/batch', name: 'Batch Generate', tierRequired: 'pro' as UserTier, hasBody: true },
      { method: 'GET' as const, path: '/generate/models', name: 'List Models', tierRequired: 'free' as UserTier, hasBody: false },
    ],
  },
  {
    category: 'Jobs',
    endpoints: [
      { method: 'GET' as const, path: '/jobs', name: 'List Jobs', tierRequired: 'free' as UserTier, hasBody: false },
      { method: 'GET' as const, path: '/jobs/{id}', name: 'Get Job', tierRequired: 'free' as UserTier, hasBody: false, hasParam: true },
      { method: 'DELETE' as const, path: '/jobs/{id}', name: 'Cancel Job', tierRequired: 'free' as UserTier, hasBody: false, hasParam: true },
    ],
  },
  {
    category: 'Account',
    endpoints: [
      { method: 'GET' as const, path: '/account', name: 'Get Account', tierRequired: 'free' as UserTier, hasBody: false },
      { method: 'GET' as const, path: '/account/quota', name: 'Get Quota', tierRequired: 'free' as UserTier, hasBody: false },
      { method: 'GET' as const, path: '/account/usage', name: 'Get Usage', tierRequired: 'free' as UserTier, hasBody: false },
    ],
  },
  {
    category: 'Videos',
    endpoints: [
      { method: 'GET' as const, path: '/videos', name: 'List Videos', tierRequired: 'free' as UserTier, hasBody: false },
      { method: 'GET' as const, path: '/videos/{id}', name: 'Get Video', tierRequired: 'free' as UserTier, hasBody: false, hasParam: true },
      { method: 'DELETE' as const, path: '/videos/{id}', name: 'Delete Video', tierRequired: 'free' as UserTier, hasBody: false, hasParam: true },
    ],
  },
];

export const PRIORITY_COLORS: Record<string, string> = {
  critical: 'amber',
  high: 'purple',
  normal: 'blue',
};
