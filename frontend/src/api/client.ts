import axios, { AxiosError, AxiosResponse } from 'axios';
import { ApiResponse, RateLimitHeaders } from '../types/api';
import { API_BASE_URL, API_PREFIX } from '../utils/constants';

// Create axios instance
const apiClient = axios.create({
  baseURL: API_BASE_URL + API_PREFIX,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Extract rate limit headers from response
function extractRateLimitHeaders(headers: Record<string, string>): RateLimitHeaders | null {
  const limit = headers['x-ratelimit-limit'];
  const remaining = headers['x-ratelimit-remaining'];
  const reset = headers['x-ratelimit-reset'];
  const window = headers['x-ratelimit-window'];

  if (limit && remaining && reset) {
    return {
      limit: parseInt(limit, 10),
      remaining: parseInt(remaining, 10),
      reset: parseInt(reset, 10),
      window: window ? parseInt(window, 10) : 60,
    };
  }
  return null;
}

// Make an API request with timing and response wrapping
export async function makeRequest<T>(
  method: 'GET' | 'POST' | 'DELETE',
  endpoint: string,
  apiKey: string,
  body?: unknown
): Promise<ApiResponse<T>> {
  const startTime = performance.now();

  try {
    const response: AxiosResponse<T> = await apiClient.request({
      method,
      url: endpoint,
      data: body,
      headers: {
        'X-API-Key': apiKey,
      },
    });

    const duration = performance.now() - startTime;
    const headers = Object.fromEntries(
      Object.entries(response.headers).map(([k, v]) => [k.toLowerCase(), String(v)])
    );

    return {
      data: response.data,
      status: response.status,
      statusText: response.statusText,
      headers,
      rateLimitHeaders: extractRateLimitHeaders(headers),
      requestId: headers['x-request-id'] || null,
      duration,
    };
  } catch (error) {
    const duration = performance.now() - startTime;

    if (error instanceof AxiosError) {
      // Server responded with an error status
      if (error.response) {
        const headers = Object.fromEntries(
          Object.entries(error.response.headers).map(([k, v]) => [k.toLowerCase(), String(v)])
        );

        return {
          data: error.response.data as T,
          status: error.response.status,
          statusText: error.response.statusText,
          headers,
          rateLimitHeaders: extractRateLimitHeaders(headers),
          requestId: headers['x-request-id'] || null,
          duration,
        };
      }

      // Network error (CORS, server down, etc.)
      const errorMessage = error.code === 'ERR_NETWORK'
        ? 'Network error - is the backend running on http://localhost:8000?'
        : error.message;

      return {
        data: { error: { code: error.code || 'NETWORK_ERROR', message: errorMessage } } as T,
        status: 0,
        statusText: 'Network Error',
        headers: {},
        rateLimitHeaders: null,
        requestId: null,
        duration,
      };
    }

    // Unknown error - wrap it
    return {
      data: { error: { code: 'UNKNOWN_ERROR', message: String(error) } } as T,
      status: 0,
      statusText: 'Unknown Error',
      headers: {},
      rateLimitHeaders: null,
      requestId: null,
      duration,
    };
  }
}

// Bulk request executor
export async function makeBulkRequests<T>(
  method: 'GET' | 'POST' | 'DELETE',
  endpoint: string,
  apiKey: string,
  count: number,
  body?: unknown,
  onProgress?: (completed: number, total: number) => void
): Promise<ApiResponse<T>[]> {
  const results: ApiResponse<T>[] = [];

  // Execute all requests in parallel
  const promises = Array.from({ length: count }, async (_, index) => {
    try {
      const result = await makeRequest<T>(method, endpoint, apiKey, body);
      results[index] = result;
      onProgress?.(results.filter(Boolean).length, count);
      return result;
    } catch (error) {
      // Create error response
      const errorResponse: ApiResponse<T> = {
        data: { error: { code: 'NETWORK_ERROR', message: String(error) } } as T,
        status: 0,
        statusText: 'Network Error',
        headers: {},
        rateLimitHeaders: null,
        requestId: null,
        duration: 0,
      };
      results[index] = errorResponse;
      onProgress?.(results.filter(Boolean).length, count);
      return errorResponse;
    }
  });

  await Promise.allSettled(promises);
  return results;
}

// Scraping API functions
export interface ScrapeResponse {
  markdown: string;
  url: string | null;
  source: string;
}

export async function scrapeWithPlaywright(url: string): Promise<ScrapeResponse> {
  const response = await apiClient.post<ScrapeResponse>('/scrape/playwright', { url }, {
    timeout: 120000, // 2 minute timeout for scraping
  });
  return response.data;
}

export default apiClient;
