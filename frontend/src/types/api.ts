// DocuMind AI — Frontend Type Definitions
// Maps exactly to our FastAPI Pydantic schemas.

export interface BoundingBox {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
}

export interface DocumentMetadata {
  title?: string;
  author?: string;
  subject?: string;
  keywords?: string;
  creator?: string;
  producer?: string;
  creation_date?: string;
  page_count: number;
  is_scanned: boolean;
}

export interface DocumentResponse {
  id: string;
  filename: string;
  status: string;
  upload_time: string;
  metadata?: DocumentMetadata;
}

export interface Citation {
  document_id: string;
  chunk_id: string;
  text_snippet: string;
  heading: string;
  page_number?: number;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  citations?: Citation[];
  trace?: any;
}

export interface ChatResponse {
  answer: string;
  citations: Citation[];
  trace?: any;
}

export interface ApiResponse<T> {
  success: boolean;
  message: string;
  data: T;
  error?: string;
}
