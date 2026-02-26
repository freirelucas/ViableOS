import { create } from 'zustand';
import type { ChatMessage, AssessmentConfig } from '../types';

interface ChatStore {
  // Session state
  sessionId: string | null;
  provider: string;
  model: string;
  apiKey: string;

  // Chat state
  messages: ChatMessage[];
  isStreaming: boolean;
  error: string | null;

  // File uploads
  pendingFiles: File[];

  // Assessment
  assessmentData: AssessmentConfig | null;

  // Actions
  setProvider: (provider: string) => void;
  setModel: (model: string) => void;
  setApiKey: (apiKey: string) => void;
  setSessionId: (id: string) => void;
  setIsStreaming: (streaming: boolean) => void;
  setError: (error: string | null) => void;
  addMessage: (msg: ChatMessage) => void;
  appendToLastMessage: (chunk: string) => void;
  addPendingFile: (file: File) => void;
  removePendingFile: (index: number) => void;
  clearPendingFiles: () => void;
  setAssessmentData: (data: AssessmentConfig | null) => void;
  reset: () => void;
}

// NOT persisted — contains API key, must stay in-memory only
export const useChatStore = create<ChatStore>()((set, get) => ({
  sessionId: null,
  provider: 'anthropic',
  model: 'claude-sonnet-4-6',
  apiKey: '',

  messages: [],
  isStreaming: false,
  error: null,

  pendingFiles: [],

  assessmentData: null,

  setProvider: (provider) => set({ provider }),
  setModel: (model) => set({ model }),
  setApiKey: (apiKey) => set({ apiKey }),
  setSessionId: (sessionId) => set({ sessionId }),
  setIsStreaming: (isStreaming) => set({ isStreaming }),
  setError: (error) => set({ error }),

  addMessage: (msg) => set((s) => ({ messages: [...s.messages, msg] })),

  appendToLastMessage: (chunk) =>
    set((s) => {
      const msgs = [...s.messages];
      if (msgs.length > 0 && msgs[msgs.length - 1].role === 'assistant') {
        msgs[msgs.length - 1] = {
          ...msgs[msgs.length - 1],
          content: msgs[msgs.length - 1].content + chunk,
        };
      }
      return { messages: msgs };
    }),

  addPendingFile: (file) =>
    set((s) => ({ pendingFiles: [...s.pendingFiles, file] })),

  removePendingFile: (index) =>
    set((s) => ({ pendingFiles: s.pendingFiles.filter((_, i) => i !== index) })),

  clearPendingFiles: () => set({ pendingFiles: [] }),

  setAssessmentData: (assessmentData) => set({ assessmentData }),

  reset: () =>
    set({
      sessionId: null,
      messages: [],
      isStreaming: false,
      error: null,
      pendingFiles: [],
      assessmentData: null,
    }),
}));
