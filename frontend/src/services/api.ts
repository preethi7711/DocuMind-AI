import axios from 'axios';
import type { ApiResponse, DocumentResponse, ChatMessage } from '../types/api';

const API_BASE_URL = 'http://localhost:8010/api/v1';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const documentService = {
  uploadDocument: async (file: File): Promise<ApiResponse<DocumentResponse>> => {
    const formData = new FormData();
    formData.append('file', file);
    
    // Override content-type for multipart upload
    const response = await apiClient.post<ApiResponse<DocumentResponse>>('/documents/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },
};

export const ocrService = {
  processDocument: async (documentId: string): Promise<ApiResponse<any>> => {
    const response = await apiClient.post<ApiResponse<any>>(`/ocr/process/${documentId}`);
    return response.data;
  },
};

export const chatService = {
  askQuestionStream: async (
    documentId: string, 
    messages: ChatMessage[], 
    debug: boolean,
    onChunk: (text: string) => void,
    onMetadata: (citations: any[], trace: any) => void
  ): Promise<void> => {
    const response = await fetch(`${API_BASE_URL}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        document_id: documentId,
        messages,
        stream: true,
        debug
      })
    });

    if (!response.body) throw new Error("No response body");

    const reader = response.body.getReader();
    const decoder = new TextDecoder('utf-8');
    
    let citations: any[] = [];
    let trace: any = null;

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      
      const chunk = decoder.decode(value, { stream: true });
      const lines = chunk.split('\n');
      
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const dataStr = line.replace('data: ', '').trim();
          if (!dataStr) continue;
          
          try {
            const data = JSON.parse(dataStr);
            if (data.type === 'chunk') {
              onChunk(data.content);
            } else if (data.type === 'citations') {
              citations = data.citations;
              onMetadata(citations, trace);
            } else if (data.type === 'trace') {
              trace = data.trace;
              onMetadata(citations, trace);
            }
          } catch (e) {
            console.error("SSE JSON Error", e);
          }
        }
      }
    }
  },
};
