export type Review = {
  id: number;
  name: string;
  status: string;
  company?: string | null;
  period?: string | null;
  created_at: string;
  updated_at: string;
  uploaded_file?: { filename?: string; file_type?: string; size_bytes?: number; sha256?: string };
  datasets?: Array<{ id: number; sheet_name: string; row_count: number; column_count: number; missing_count: number; duplicate_count: number }>;
};

export type DatasetSummary = {
  review_id: number;
  tables: any[];
  summary: { table_count: number; total_rows: number; total_columns: number; total_missing_values: number; total_duplicate_rows: number };
};

export type ComparisonOptions = {
  entity_columns: Array<{ name: string; entities: string[] }>;
  metric_columns: string[];
};

const API = process.env.NEXT_PUBLIC_API_URL || (process.env.NODE_ENV === 'production' ? 'https://finora-financial-agent.onrender.com' : 'http://127.0.0.1:8000');

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API}${path}`, { ...init, cache: 'no-store' });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(body.detail || `Request failed (${res.status})`);
  return body;
}

export function apiBase() { return API; }
export const api = {
  health: () => request<any>('/health'),
  reviews: () => request<{ success: boolean; items: Review[] }>('/reviews'),
  review: (id: number) => request<{ success: boolean; review: Review }>(`/reviews/${id}`),
  dataset: (id: number) => request<{ success: boolean; dataset: DatasetSummary }>(`/reviews/${id}/dataset`),
  columns: (id: number) => request<{ success: boolean; items: any[] }>(`/reviews/${id}/columns`),
  records: (id: number, offset = 0, limit = 100) => request<{ success: boolean; total: number; items: any[] }>(`/reviews/${id}/records?offset=${offset}&limit=${limit}`),
  comparisonOptions: (id: number) => request<{ success: boolean } & ComparisonOptions>(`/reviews/${id}/comparison-options`),
  compareWithin: (id: number, entityColumn: string, metric: string, left: string, right: string) => request<{ success: boolean; comparison: any }>(`/reviews/${id}/compare?entity_column=${encodeURIComponent(entityColumn)}&metric=${encodeURIComponent(metric)}&left=${encodeURIComponent(left)}&right=${encodeURIComponent(right)}`),
  audit: (id: number) => request<{ success: boolean; audit: any }>(`/reviews/${id}/audit`),
  upload: async (file: File, company?: string, period?: string) => {
    const form = new FormData(); form.append('file', file);
    if (company) form.append('company', company);
    if (period) form.append('period', period);
    return request<any>('/reviews', { method: 'POST', body: form });
  },
  deleteReview: (id: number) => request<any>(`/reviews/${id}`, { method: 'DELETE' }),
};
