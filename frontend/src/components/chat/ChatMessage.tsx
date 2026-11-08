import React from 'react'
import { Bot, User, Sparkles } from 'lucide-react'
import { CitationCard } from './CitationCard'
import type { Citation } from '../../api/types'

export interface ChatMessageData {
  id: string
  role: 'user' | 'assistant'
  content: string
  intent?: string
  citations?: Citation[]
  statusMessage?: string
  isStreaming?: boolean
  timestamp: string
}

interface ChatMessageProps {
  message: ChatMessageData
}

export const ChatMessage: React.FC<ChatMessageProps> = ({ message }) => {
  const isUser = message.role === 'user'

  return (
    <div className={`flex gap-3 py-4 ${isUser ? 'justify-end' : 'justify-start'}`}>
      {!isUser && (
        <div className="h-8 w-8 rounded-lg bg-blue-600 text-white flex items-center justify-center shrink-0 shadow-xs">
          <Bot className="h-4 w-4" />
        </div>
      )}

      <div
        className={`max-w-2xl space-y-3 rounded-2xl px-4 py-3 text-sm ${
          isUser
            ? 'bg-blue-600 text-white rounded-tr-none'
            : 'bg-white border border-slate-200 text-slate-800 rounded-tl-none shadow-xs'
        }`}
      >
        {/* Header / Intent Badge for Assistant */}
        {!isUser && (
          <div className="flex items-center justify-between text-xs pb-1 border-b border-slate-100">
            <div className="flex items-center gap-2">
              <span className="font-semibold text-slate-900">VERITY Agent</span>
              {message.intent && (
                <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full bg-slate-100 text-slate-600">
                  {message.intent.replace(/_/g, ' ')}
                </span>
              )}
            </div>
            <span className="text-[10px] text-slate-400">{message.timestamp}</span>
          </div>
        )}

        {/* Live SSE Workflow Stage Indicator */}
        {message.statusMessage && (
          <div className="flex items-center gap-2 text-xs text-blue-700 bg-blue-50/80 px-2.5 py-1.5 rounded-md border border-blue-100 animate-pulse">
            <Sparkles className="h-3.5 w-3.5 text-blue-500 animate-spin" />
            <span className="font-medium">{message.statusMessage}</span>
          </div>
        )}

        {/* Message Content */}
        <div className={`leading-relaxed whitespace-pre-wrap break-words ${isUser ? 'text-white' : 'text-slate-800'}`}>
          {message.content}
          {message.isStreaming && (
            <span className="inline-block w-1.5 h-4 ml-1 bg-blue-500 animate-pulse align-middle" />
          )}
        </div>

        {/* Verified Citations Carousel / Grid */}
        {!isUser && message.citations && message.citations.length > 0 && (
          <div className="pt-2 border-t border-slate-100 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
                Ground Truth Citations ({message.citations.length})
              </span>
              <span className="text-[10px] text-slate-400">
                Verified against repository chunks
              </span>
            </div>
            <div className="space-y-2">
              {message.citations.map((cite, index) => (
                <CitationCard key={cite.chunk_id || index} citation={cite} index={index} />
              ))}
            </div>
          </div>
        )}
      </div>

      {isUser && (
        <div className="h-8 w-8 rounded-lg bg-slate-800 text-white flex items-center justify-center shrink-0 shadow-xs">
          <User className="h-4 w-4" />
        </div>
      )}
    </div>
  )
}
