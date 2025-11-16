import apiClient from './apiClient';
import { BillingEntry } from '../types';

interface BillingSummary {
  total_tokens: number;
  month_tokens: number;
}

export const fetchBillingSummary = async () => {
  const { data } = await apiClient.get<BillingSummary>('/billing/summary');
  return data;
};

export const fetchBillingHistory = async () => {
  const { data } = await apiClient.get<BillingEntry[]>('/billing/history');
  return data;
};
