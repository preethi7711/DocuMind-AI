import { create } from 'zustand';
import type { ChatMessage, DocumentResponse } from '../types/api';

interface UIState {
  // Document Selection State
  selectedDocumentId: string | null;
  documents: DocumentResponse[];
  
  // Chat State
  chatHistory: Record<string, ChatMessage[]>;
  isSidebarOpen: boolean;
  isDebugMode: boolean;
  activePageNumber: number | null;

  // Actions
  setSelectedDocument: (id: string | null) => void;
  setActivePageNumber: (page: number | null) => void;
  addDocument: (doc: DocumentResponse) => void;
  setDocuments: (docs: DocumentResponse[]) => void;
  addChatMessage: (docId: string, message: ChatMessage) => void;
  updateLastChatMessage: (docId: string, message: Partial<ChatMessage>) => void;
  toggleSidebar: () => void;
  toggleDebugMode: () => void;
}

export const useUIStore = create<UIState>((set) => ({
  selectedDocumentId: null,
  documents: [],
  chatHistory: {},
  isSidebarOpen: true,
  isDebugMode: false,
  activePageNumber: null,

  setSelectedDocument: (id) => set({ selectedDocumentId: id, activePageNumber: null }),
  setActivePageNumber: (page) => set({ activePageNumber: page }),
  
  addDocument: (doc) => set((state) => ({ 
    documents: [doc, ...state.documents],
    selectedDocumentId: doc.id // Auto-select newly added document
  })),
  
  setDocuments: (docs) => set({ documents: docs }),
  
  addChatMessage: (docId, message) => set((state) => {
    const history = state.chatHistory[docId] || [];
    return {
      chatHistory: {
        ...state.chatHistory,
        [docId]: [...history, message]
      }
    };
  }),

  updateLastChatMessage: (docId, partialMessage) => set((state) => {
    const history = state.chatHistory[docId] || [];
    if (history.length === 0) return state;
    
    const lastMsg = history[history.length - 1];
    const newHistory = [...history];
    newHistory[newHistory.length - 1] = { ...lastMsg, ...partialMessage };
    
    return {
      chatHistory: {
        ...state.chatHistory,
        [docId]: newHistory
      }
    };
  }),

  toggleSidebar: () => set((state) => ({ isSidebarOpen: !state.isSidebarOpen })),
  toggleDebugMode: () => set((state) => ({ isDebugMode: !state.isDebugMode })),
}));
