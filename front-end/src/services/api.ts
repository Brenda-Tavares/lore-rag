import axios from 'axios';
import type { ChatResponse, UploadResponse } from '../types';

const api = axios.create({
  baseURL: 'http://127.0.0.1:8000/api/v1',
  timeout: 60000,
});

export const uploadDocument = async (file: File): Promise<UploadResponse> => {
  const formData = new FormData();
  formData.append('file', file);
  
  const response = await api.post<UploadResponse>('/documents/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  
  return response.data;
};

export const chat = async (query: string): Promise<ChatResponse> => {
  const response = await api.post<ChatResponse>('/ai/chat', { query });
  return response.data;
};