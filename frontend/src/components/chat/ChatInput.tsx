import React, { useState, useRef } from 'react'
import { Send, Sparkles, StopCircle } from 'lucide-react'

interface ChatInputProps {
  onSendMessage: (query: string) => void
  disabled?: boolean
  isStreaming?: boolean
  onStopStreaming?: () => void
}

const SUGGESTIONS = [
  'Evaluate SOC 2 CC6.1 logical access controls against our policies.',
  'What is our retention policy for customer financial records?',
  'What are the encryption requirements for data in transit and at rest?',
  'Identify compliance gaps in our current incident response procedure.',
]

export const ChatInput: React.FC<ChatInputProps> = ({
  onSendMessage,
  disabled,
  isStreaming,
  onStopStreaming,
}) => {
  const [query, setQuery] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const handleSubmit = (e?: React.FormEvent) => {
    if (e) e.preventDefault()
    if (!query.trim() || disabled) return
    onSendMessage(query.trim())
    setQuery('')
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  return (
    <div className="space-y-2">
      {/* Quick Prompts */}
      <div className="flex items-center gap-2 overflow-x-auto pb-1 text-xs no-scrollbar">
        <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider shrink-0 flex items-center gap-1">
          <Sparkles className="h-3 w-3 text-amber-500" /> Prompts:
        </span>
        {SUGGESTIONS.map((suggestion, idx) => (
          <button
            key={idx}
            type="button"
            disabled={disabled}
            onClick={() => onSendMessage(suggestion)}
            className="shrink-0 px-2.5 py-1 rounded-full bg-slate-100 hover:bg-slate-200 text-slate-600 hover:text-slate-900 border border-slate-200 text-[11px] transition-colors disabled:opacity-50"
          >
            {suggestion}
          </button>
        ))}
      </div>

      {/* Main Input Form */}
      <form
        onSubmit={handleSubmit}
        className="relative bg-white rounded-xl border border-slate-200 shadow-sm focus-within:ring-2 focus-within:ring-blue-500/20 focus-within:border-blue-500 transition-all p-2 flex items-end gap-2"
      >
        <textarea
          ref={textareaRef}
          rows={2}
          value={query}
          disabled={disabled}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask VERITY about compliance requirements, policies, or gap remediations..."
          className="w-full text-xs text-slate-800 placeholder-slate-400 bg-transparent resize-none focus:outline-none p-1.5"
        />

        <div className="flex items-center gap-1 shrink-0 pb-1 pr-1">
          {isStreaming ? (
            <button
              type="button"
              onClick={onStopStreaming}
              className="p-2 bg-rose-50 text-rose-600 hover:bg-rose-100 rounded-lg transition-colors"
              title="Stop response generation"
            >
              <StopCircle className="h-4 w-4" />
            </button>
          ) : (
            <button
              type="submit"
              disabled={!query.trim() || disabled}
              className="p-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg shadow-sm disabled:opacity-40 transition-colors"
              title="Send prompt"
            >
              <Send className="h-4 w-4" />
            </button>
          )}
        </div>
      </form>
      <div className="flex justify-between items-center px-1">
        <span className="text-[10px] text-slate-400">
          Press <kbd className="px-1 py-0.5 rounded bg-slate-100 border border-slate-200 font-mono">Enter</kbd> to send, <kbd className="px-1 py-0.5 rounded bg-slate-100 border border-slate-200 font-mono">Shift+Enter</kbd> for newline
        </span>
        <span className="text-[10px] text-slate-400">
          Grounding engine: Local FastMCP Server + Hybrid Search
        </span>
      </div>
    </div>
  )
}
