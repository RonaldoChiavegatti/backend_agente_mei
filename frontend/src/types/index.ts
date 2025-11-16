export interface UserProfile {
  id: string;
  email: string;
  full_name?: string;
  created_at?: string;
}

export interface DashboardSummary {
  full_name: string;
  annual_revenue: number;
  monthly_revenue: number;
  month_label: string;
  token_usage: number;
  documents_total: number;
}

export interface DocumentItem {
  id: string;
  file_name: string;
  uploaded_at: string;
  status: 'processing' | 'completed' | 'error';
  amount?: number;
  document_date?: string;
  document_type?: string;
}

export interface DocumentDetails extends DocumentItem {
  description?: string;
}

export interface BillingEntry {
  id: string;
  date: string;
  type: string;
  tokens: number;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  createdAt: string;
  usedDocuments?: string[];
}
