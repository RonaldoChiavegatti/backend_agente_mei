import apiClient from './apiClient';
import { UserProfile } from '../types';

interface LoginResponse {
  access_token: string;
  token_type: string;
}

export const login = async (email: string, password: string) => {
  const payload = new URLSearchParams();
  payload.append('username', email);
  payload.append('password', password);
  const { data } = await apiClient.post<LoginResponse>('/auth/login', payload, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
  });
  return data;
};

export const register = async (fullName: string, email: string, password: string) => {
  const { data } = await apiClient.post('/auth/register', {
    full_name: fullName,
    email,
    password
  });
  return data;
};

export const me = async (): Promise<UserProfile> => {
  try {
    const { data } = await apiClient.get<UserProfile>('/auth/me');
    return data;
  } catch (error) {
    const { data } = await apiClient.get<UserProfile>('/auth/profile');
    return data;
  }
};
