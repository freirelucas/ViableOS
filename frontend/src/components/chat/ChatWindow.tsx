import { useEffect, useRef, useState } from 'react';
import { Send, Paperclip, X } from 'lucide-react';
import { useChatStore } from '../../store/useChatStore';
import { api } from '../../api/client';
import { MessageBubble } from './MessageBubble';
import type { ChatMessage, ChatAttachment } from '../../types';

const API_BASE = import.meta.env.VITE_API_URL || '/api';
const MAX_FILES = 5;

export function ChatWindow() {
  const [input, setInput] = useState('');
  const [dragOver, setDragOver] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const {
    sessionId, provider, model, apiKey, messages, isStreaming, error,
    pendingFiles, addPendingFile, removePendingFile, clearPendingFiles,
    setSessionId, setIsStreaming, setError, addMessage, appendToLastMessage,
  } = useChatStore();

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const startSession = async () => {
    const res = await fetch(`${API_BASE}/chat/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ provider, model, api_key: apiKey }),
    });
    if (!res.ok) throw new Error(`Failed to start session: ${res.status}`);
    const data = await res.json();
    setSessionId(data.session_id);
    return data.session_id;
  };

  const addFiles = (files: File[]) => {
    const remaining = MAX_FILES - pendingFiles.length;
    if (remaining <= 0) return;
    for (const file of files.slice(0, remaining)) {
      addPendingFile(file);
    }
  };

  const handlePaste = (e: React.ClipboardEvent) => {
    const items = e.clipboardData?.items;
    if (!items) return;
    for (const item of items) {
      if (item.type.startsWith('image/')) {
        e.preventDefault();
        const file = item.getAsFile();
        if (file) addFiles([file]);
      }
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const files = Array.from(e.dataTransfer.files);
    if (files.length > 0) addFiles(files);
  };

  const handleSend = async () => {
    const text = input.trim();
    if ((!text && pendingFiles.length === 0) || isStreaming) return;
    if (!apiKey && provider !== 'ollama') {
      setError('Please enter your API key first.');
      return;
    }

    setInput('');
    setError(null);
    setIsStreaming(true);

    try {
      let sid = sessionId;
      if (!sid) {
        sid = await startSession();
      }

      // Upload pending files
      const uploadedAttachments: ChatAttachment[] = [];
      const attachmentIds: string[] = [];
      for (const file of pendingFiles) {
        try {
          const result = await api.chatUploadFile(sid, file);
          attachmentIds.push(result.id);
          uploadedAttachments.push({
            id: result.id,
            filename: result.filename,
            type: result.type,
            thumbnail_url: file.type.startsWith('image/')
              ? URL.createObjectURL(file)
              : undefined,
          });
        } catch {
          // Skip failed uploads
        }
      }
      clearPendingFiles();

      const userMsg: ChatMessage = {
        role: 'user',
        content: text || (uploadedAttachments.length > 0 ? `[${uploadedAttachments.map(a => a.filename).join(', ')}]` : ''),
        timestamp: Date.now() / 1000,
        attachments: uploadedAttachments.length > 0 ? uploadedAttachments : undefined,
      };
      addMessage(userMsg);

      // Add empty assistant message for streaming
      const assistantMsg: ChatMessage = {
        role: 'assistant',
        content: '',
        timestamp: Date.now() / 1000,
      };
      addMessage(assistantMsg);

      // SSE streaming via fetch + ReadableStream
      const res = await fetch(`${API_BASE}/chat/message`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sid,
          message: text,
          attachment_ids: attachmentIds,
        }),
      });

      if (!res.ok) {
        throw new Error(`Chat request failed: ${res.status}`);
      }

      const reader = res.body?.getReader();
      if (!reader) throw new Error('No response body');

      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const raw = line.slice(6);
            if (raw === '[DONE]') continue;
            // Chunks are JSON-encoded to safely transport newlines
            try {
              const text = JSON.parse(raw);
              if (typeof text === 'string' && text.startsWith('[ERROR]')) {
                setError(text);
                continue;
              }
              appendToLastMessage(text);
            } catch {
              // Fallback for non-JSON data
              if (raw.startsWith('[ERROR]')) {
                setError(raw);
              } else {
                appendToLastMessage(raw);
              }
            }
          }
        }
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Unknown error');
    } finally {
      setIsStreaming(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div
      className="flex flex-col flex-1 min-h-0 relative"
      onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
      onDragLeave={() => setDragOver(false)}
      onDrop={handleDrop}
    >
      {/* Drag overlay */}
      {dragOver && (
        <div className="absolute inset-0 z-50 bg-[var(--color-primary)]/10 border-2 border-dashed border-[var(--color-primary)] rounded-xl flex items-center justify-center pointer-events-none">
          <div className="text-[var(--color-primary)] font-medium text-sm">Drop files here</div>
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center gap-3">
            <div className="text-4xl">🧠</div>
            <h2 className="text-lg font-semibold text-[var(--color-text)]">VSM Expert Chat</h2>
            <p className="text-sm text-[var(--color-muted)] max-w-md">
              I'll interview you about your business and create a structured assessment
              that maps your operations onto the Viable System Model. Start by telling me
              about your organization.
            </p>
            <p className="text-xs text-[var(--color-muted)] max-w-sm">
              You can drag & drop files, paste screenshots, or click the paperclip to attach PDFs, images, and documents.
            </p>
          </div>
        )}
        {messages.map((msg, i) => (
          <MessageBubble
            key={i}
            message={msg}
            isStreaming={isStreaming && i === messages.length - 1 && msg.role === 'assistant'}
          />
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Error */}
      {error && (
        <div className="mx-4 mb-2 px-3 py-2 text-xs text-[var(--color-danger)] bg-[var(--color-danger)]/10 rounded-lg border border-[var(--color-danger)]/20">
          {error}
        </div>
      )}

      {/* Pending files preview */}
      {pendingFiles.length > 0 && (
        <div className="px-4 py-2 border-t border-[var(--color-border)] flex gap-2 flex-wrap">
          {pendingFiles.map((file, i) => (
            <div key={i} className="relative group">
              {file.type.startsWith('image/') ? (
                <div className="relative w-16 h-16 rounded-lg overflow-hidden border border-[var(--color-border)]">
                  <img src={URL.createObjectURL(file)} alt={file.name} className="w-full h-full object-cover" />
                  <button
                    onClick={() => removePendingFile(i)}
                    className="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-[var(--color-danger)] text-white flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
                  >
                    <X className="w-2.5 h-2.5" />
                  </button>
                </div>
              ) : (
                <div className="flex items-center gap-1.5 px-2 py-1 rounded-lg bg-[var(--color-bg)] border border-[var(--color-border)] text-xs">
                  <Paperclip className="w-3 h-3" />
                  <span className="max-w-[120px] truncate">{file.name}</span>
                  <button onClick={() => removePendingFile(i)} className="text-[var(--color-muted)] hover:text-[var(--color-danger)]">
                    <X className="w-3 h-3" />
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Input */}
      <div className="p-4 border-t border-[var(--color-border)]">
        <div className="flex items-end gap-2">
          <button
            onClick={() => fileInputRef.current?.click()}
            className="shrink-0 w-10 h-10 rounded-xl border border-[var(--color-border)] flex items-center justify-center text-[var(--color-muted)] hover:border-[var(--color-primary)] hover:text-[var(--color-primary)] transition-all"
            title="Attach files"
          >
            <Paperclip className="w-4 h-4" />
          </button>
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept="image/*,.pdf,.txt,.md,.csv"
            className="hidden"
            onChange={(e) => {
              const files = Array.from(e.target.files || []);
              if (files.length > 0) addFiles(files);
              e.target.value = '';
            }}
          />
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            onPaste={handlePaste}
            placeholder="Describe your business or organization..."
            rows={1}
            className="flex-1 bg-[var(--color-card)] text-[var(--color-text)] text-sm rounded-xl px-4 py-3 border border-[var(--color-border)] outline-none focus:border-[var(--color-primary)] placeholder:text-[var(--color-muted)] resize-none"
            style={{ minHeight: '44px', maxHeight: '120px' }}
            onInput={(e) => {
              const target = e.target as HTMLTextAreaElement;
              target.style.height = '44px';
              target.style.height = `${Math.min(target.scrollHeight, 120)}px`;
            }}
          />
          <button
            onClick={handleSend}
            disabled={isStreaming || (!input.trim() && pendingFiles.length === 0)}
            className="shrink-0 w-10 h-10 rounded-xl bg-[var(--color-primary)] text-white flex items-center justify-center hover:opacity-90 transition-opacity disabled:opacity-40"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
