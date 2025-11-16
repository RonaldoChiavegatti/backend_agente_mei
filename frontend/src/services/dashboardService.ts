import apiClient from './apiClient';
import { DashboardSummary } from '../types';

export const fetchDashboardSummary = async () => {
  const { data } = await apiClient.get<DashboardSummary>('/dashboard/mei');
  return data;
};
