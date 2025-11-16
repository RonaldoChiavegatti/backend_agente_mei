import apiClient from './apiClient';
import { DocumentDetails, DocumentItem } from '../types';

export const fetchDocuments = async () => {
  const { data } = await apiClient.get<DocumentItem[]>('/documents');
  return data;
};

export const uploadDocument = async (file: File) => {
  const formData = new FormData();
  formData.append('file', file);
  const { data } = await apiClient.post('/documents/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  });
  return data;
};

export const fetchDocumentDetails = async (id: string) => {
  const { data } = await apiClient.get<DocumentDetails>(`/documents/${id}`);
  return data;
};

export const updateDocument = async (id: string, payload: Partial<DocumentDetails>) => {
  const { data } = await apiClient.put<DocumentDetails>(`/documents/${id}`, payload);
  return data;
};
