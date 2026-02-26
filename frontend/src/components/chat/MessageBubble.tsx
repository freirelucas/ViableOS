import { Bot, User, FileText, Paperclip } from 'lucide-react';
import Markdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import type { ChatMessage } from '../../types';

interface Props {
  message: ChatMessage;
  isStreaming?: boolean;
}

export function MessageBubble({ message, isStreaming }: Props) {
  const isUser = message.role === 'user';

  return (
    <div className={`flex gap-3 ${isUser ? 'flex-row-reverse' : ''}`}>
      <div
        className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${
          isUser
            ? 'bg-[var(--color-primary)]'
            : 'bg-[var(--color-secondary)]'
        }`}
      >
        {isUser ? <User className="w-4 h-4 text-white" /> : <Bot className="w-4 h-4 text-white" />}
      </div>
      <div
        className={`max-w-[80%] rounded-xl px-4 py-3 text-sm leading-relaxed ${
          isUser
            ? 'bg-[var(--color-primary)] text-white'
            : 'bg-[var(--color-card)] text-[var(--color-text)] border border-[var(--color-border)]'
        }`}
      >
        {/* Attachment thumbnails */}
        {message.attachments && message.attachments.length > 0 && (
          <div className="flex gap-2 flex-wrap mb-2">
            {message.attachments.map((att) => (
              <div key={att.id}>
                {att.thumbnail_url ? (
                  <div className="w-20 h-20 rounded-lg overflow-hidden border border-white/20">
                    <img src={att.thumbnail_url} alt={att.filename} className="w-full h-full object-cover" />
                  </div>
                ) : att.type === 'application/pdf' ? (
                  <div className={`flex items-center gap-1.5 px-2 py-1 rounded-lg text-xs ${
                    isUser ? 'bg-white/15' : 'bg-[var(--color-bg)] border border-[var(--color-border)]'
                  }`}>
                    <FileText className="w-3 h-3" />
                    <span className="max-w-[100px] truncate">{att.filename}</span>
                  </div>
                ) : (
                  <div className={`flex items-center gap-1.5 px-2 py-1 rounded-lg text-xs ${
                    isUser ? 'bg-white/15' : 'bg-[var(--color-bg)] border border-[var(--color-border)]'
                  }`}>
                    <Paperclip className="w-3 h-3" />
                    <span className="max-w-[100px] truncate">{att.filename}</span>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Message content */}
        {isUser ? (
          <div className="whitespace-pre-wrap">{message.content}</div>
        ) : (
          <div className="prose prose-sm dark:prose-invert max-w-none [&>*:first-child]:mt-0 [&>*:last-child]:mb-0">
            <Markdown
              remarkPlugins={[remarkGfm]}
              components={{
                code({ className, children, ...props }) {
                  const match = /language-(\w+)/.exec(className || '');
                  const code = String(children).replace(/\n$/, '');
                  if (match) {
                    return (
                      <SyntaxHighlighter
                        style={oneDark}
                        language={match[1]}
                        PreTag="div"
                        customStyle={{ margin: '0.5em 0', borderRadius: '0.5rem', fontSize: '12px' }}
                      >
                        {code}
                      </SyntaxHighlighter>
                    );
                  }
                  return (
                    <code className="bg-[var(--color-border)]/50 px-1 py-0.5 rounded text-xs" {...props}>
                      {children}
                    </code>
                  );
                },
                table({ children }) {
                  return (
                    <div className="overflow-x-auto my-2">
                      <table className="text-xs border-collapse w-full [&_th]:border [&_th]:border-[var(--color-border)] [&_th]:px-2 [&_th]:py-1 [&_th]:bg-[var(--color-bg)] [&_td]:border [&_td]:border-[var(--color-border)] [&_td]:px-2 [&_td]:py-1">
                        {children}
                      </table>
                    </div>
                  );
                },
                a({ href, children }) {
                  return (
                    <a href={href} target="_blank" rel="noopener noreferrer" className="text-[var(--color-primary)] underline">
                      {children}
                    </a>
                  );
                },
              }}
            >
              {message.content}
            </Markdown>
          </div>
        )}

        {/* Streaming cursor */}
        {isStreaming && !isUser && (
          <span className="inline-block w-2 h-4 ml-1 bg-[var(--color-primary)] animate-pulse rounded-sm" />
        )}
      </div>
    </div>
  );
}
