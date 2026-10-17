import { useState } from 'react';
import { Send, Loader2, User, Bot, FileText } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { chat as chatApi } from '../services/api';
import type { ChatMessage, Source } from '../types';
import { useI18n } from '../i18n/I18nContext';

export function Chat() {
  const { t } = useI18n();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage: ChatMessage = { role: 'user', content: input };
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      const response = await chatApi(input);
      const assistantMessage: ChatMessage = {
        role: 'assistant',
        content: response.answer,
        sources: response.sources,
      };
      setMessages(prev => [...prev, assistantMessage]);
    } catch (error: any) {
      const errorMessage: ChatMessage = {
        role: 'assistant',
        content: `${t('chat.error')} ${error.response?.data?.detail || error.message}`,
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="border border-ink-700 rounded-xl bg-ink-900 p-6 flex flex-col h-[640px]">
      <p className="font-mono text-xs text-accent tracking-widest uppercase mb-2">{t('chat.eyebrow')}</p>
      <h2 className="font-display text-3xl text-white mb-6">{t('chat.title')}</h2>

      <div className="flex-1 overflow-y-auto space-y-5 mb-5 pr-2">
        {messages.length === 0 && (
          <div className="h-full flex flex-col items-center justify-center text-center gap-2">
            <Bot className="w-10 h-10 text-ink-600 mb-2" />
            <p className="text-slate-400">{t('chat.empty')}</p>
            <p className="font-mono text-xs text-slate-600">{t('chat.emptyHint')}</p>
          </div>
        )}

        {messages.map((msg, idx) => (
          <div key={idx} className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            {msg.role === 'assistant' && (
              <div className="w-8 h-8 rounded border border-ink-600 bg-ink-800 flex items-center justify-center flex-shrink-0">
                <Bot className="w-4 h-4 text-accent" />
              </div>
            )}

            <div className={`max-w-[85%] ${msg.role === 'user' ? 'order-first' : ''}`}>
              <div className={`rounded-lg px-4 py-3 border ${
                msg.role === 'user'
                  ? 'bg-accent/10 border-accent/30 text-slate-100'
                  : 'bg-ink-800 border-ink-700 text-slate-200'
              }`}>
                {msg.role === 'assistant' ? (
                  <div className="prose prose-invert prose-sm max-w-none prose-p:text-slate-200 prose-code:text-accent prose-pre:bg-ink-950 prose-pre:border prose-pre:border-ink-700">
                    <ReactMarkdown>{msg.content}</ReactMarkdown>
                  </div>
                ) : (
                  <p className="whitespace-pre-wrap text-sm">{msg.content}</p>
                )}
              </div>

              {msg.sources && msg.sources.length > 0 && (() => {
                const uniqueSources = msg.sources.filter((source, index, self) =>
                  index === self.findIndex(s => s.filename === source.filename && s.snippet === source.snippet)
                );
                return (
                  <div className="mt-3 border border-ink-700 rounded-lg bg-ink-950 p-3">
                    <p className="font-mono text-[11px] text-slate-500 mb-2 flex items-center gap-1.5">
                      <FileText className="w-3 h-3" />
                      {t('chat.sources')} ({uniqueSources.length})
                    </p>
                    <div className="space-y-2">
                      {uniqueSources.map((source: Source, i: number) => (
                        <div key={i} className="border-l-2 border-accent/50 pl-3">
                          <p className="font-mono text-xs text-accent">{source.filename}</p>
                          <p className="text-xs text-slate-500 italic line-clamp-2 mt-0.5">{source.snippet}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                );
              })()}
            </div>

            {msg.role === 'user' && (
              <div className="w-8 h-8 rounded border border-ink-600 bg-ink-800 flex items-center justify-center flex-shrink-0">
                <User className="w-4 h-4 text-slate-400" />
              </div>
            )}
          </div>
        ))}

        {isLoading && (
          <div className="flex gap-3">
            <div className="w-8 h-8 rounded border border-ink-600 bg-ink-800 flex items-center justify-center flex-shrink-0">
              <Bot className="w-4 h-4 text-accent" />
            </div>
            <div className="bg-ink-800 border border-ink-700 rounded-lg px-4 py-3 flex items-center gap-2 text-sm text-slate-400">
              <Loader2 className="w-4 h-4 animate-spin text-accent" />
              {t('chat.thinking')}
            </div>
          </div>
        )}
      </div>

      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={t('chat.placeholder')}
          disabled={isLoading}
          className="flex-1 bg-ink-950 border border-ink-600 rounded-lg px-4 py-2.5 text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:border-accent/60 disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={isLoading || !input.trim()}
          className="bg-accent text-ink-950 hover:bg-accent-dim disabled:bg-ink-700 disabled:text-slate-500 disabled:cursor-not-allowed px-4 rounded-lg transition-colors flex items-center justify-center"
        >
          <Send className="w-4 h-4" />
        </button>
      </form>
    </div>
  );
}