export interface Source {
    filename: string;
    snippet: string;
  }
  
  export interface ChatResponse {
    answer: string;
    sources: Source[];
  }
  
  export interface UploadResponse {
    document_id: string;
    status: string;
  }
  
  export interface ChatMessage {
    role: 'user' | 'assistant';
    content: string;
    sources?: Source[];
  }