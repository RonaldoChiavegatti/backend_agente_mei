import axios from 'axios';

export const BASE_API_URL =
  import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8080/api';

const apiClient = axios.create({
  baseURL: BASE_API_URL
});

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('agente-mei.token');
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export default apiClient;
