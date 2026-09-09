import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Send, Bot, User } from 'lucide-react';

interface ChatMessage {
  role: 'user' | 'agent';
  text: string;
}

interface AgentChatModalProps {
  open: boolean;
  agenteNome: string;
  onClose: () => void;
}

const API_BASE = import.meta.env.VITE_API_URL || '/api';

export function AgentChatModal({ open, agenteNome, onClose }: AgentChatModalProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);

  const handleSend = async () => {
    if (!input.trim() || sending) return;
    const text = input.trim();
    setInput('');
    setMessages(prev => [...prev, { role: 'user', text }]);
    setSending(true);
    try {
      const res = await fetch(`${API_BASE}/cda/chat/${encodeURIComponent(agenteNome)}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mensagem: text }),
      });
      const data = await res.json();
      if (data.status === 'ok') {
        setMessages(prev => [...prev, { role: 'agent', text: data.resposta }]);
      }
    } catch {
      setMessages(prev => [...prev, { role: 'agent', text: '[Erro de comunicação com o agente]' }]);
    } finally {
      setSending(false);
    }
  };

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm"
          onClick={onClose}
        >
          <motion.div
            initial={{ scale: 0.95, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0.95, opacity: 0 }}
            className="w-full max-w-lg mx-4 rounded-xl bg-[var(--color-card)] border border-[var(--color-border)] shadow-2xl overflow-hidden"
            onClick={e => e.stopPropagation()}
          >
            <div className="flex items-center justify-between px-4 py-3 border-b border-[var(--color-border)]">
              <div className="flex items-center gap-2">
                <Bot className="w-5 h-5 text-[var(--color-primary)]" />
                <span className="font-semibold text-sm">{agenteNome}</span>
              </div>
              <button onClick={onClose} className="p-1 rounded-lg hover:bg-[var(--color-bg)] transition-colors">
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="h-80 overflow-y-auto p-4 space-y-3">
              {messages.length === 0 && (
                <p className="text-sm text-[var(--color-muted)] text-center pt-8">
                  Inicie uma conversa com {agenteNome}.
                </p>
              )}
              {messages.map((m, i) => (
                <div key={i} className={`flex gap-2 ${m.role === 'user' ? 'justify-end' : ''}`}>
                  {m.role === 'agent' && <Bot className="w-5 h-5 mt-1 text-[var(--color-primary)] shrink-0" />}
                  <div className={`max-w-[80%] p-3 rounded-xl text-sm ${
                    m.role === 'user'
                      ? 'bg-[var(--color-primary)] text-white rounded-br-sm'
                      : 'bg-[var(--color-bg)] rounded-bl-sm'
                  }`}>{m.text}</div>
                  {m.role === 'user' && <User className="w-5 h-5 mt-1 text-[var(--color-text)] shrink-0" />}
                </div>
              ))}
              {sending && (
                <div className="flex gap-2">
                  <Bot className="w-5 h-5 mt-1 text-[var(--color-primary)] shrink-0" />
                  <div className="p-3 rounded-xl bg-[var(--color-bg)] text-sm text-[var(--color-muted)] animate-pulse">pensando...</div>
                </div>
              )}
            </div>

            <div className="flex items-center gap-2 p-3 border-t border-[var(--color-border)]">
              <input
                value={input} onChange={e => setInput(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && handleSend()}
                placeholder={`Pergunte algo a ${agenteNome}...`}
                className="flex-1 px-3 py-2 rounded-lg bg-[var(--color-bg)] border border-[var(--color-border)] text-sm outline-none focus:border-[var(--color-primary)] transition-colors"
              />
              <button onClick={handleSend} disabled={sending || !input.trim()}
                className="p-2 rounded-lg bg-[var(--color-primary)] text-white disabled:opacity-50 transition-opacity">
                <Send className="w-4 h-4" />
              </button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
