import React, { useState, useRef, useEffect } from 'react'
import { ChatMessage, type ChatMessageData } from '../components/chat/ChatMessage'
import { ChatInput } from '../components/chat/ChatInput'
import { chatService } from '../services/chatService'
import type { Citation, StreamEventPayload } from '../api/types'
import { RotateCcw } from 'lucide-react'
import { useToast } from '../context/ToastContext'

export const AssistantPage: React.FC = () => {
  const [messages, setMessages] = useState<ChatMessageData[]>([
    {
      id: 'welcome',
      role: 'assistant',
      content:
        "Hello! I am VERITY, your enterprise compliance and document intelligence agent. I evaluate control frameworks (SOC 2, ISO 27001), verify audit evidence chunks, and answer questions with exact citations.\n\nHow can I assist your compliance team today?",
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    },
  ])
  const [isStreaming, setIsStreaming] = useState(false)
  const [abortController, setAbortController] = useState<AbortController | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const { showToast } = useToast()

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleSendMessage = async (queryText: string) => {
    const userMessage: ChatMessageData = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: queryText,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    }

    const assistantMsgId = `assistant-${Date.now()}`
    const initialAssistantMsg: ChatMessageData = {
      id: assistantMsgId,
      role: 'assistant',
      content: '',
      isStreaming: true,
      statusMessage: 'Connecting to MCP Server & Routing intent...',
      citations: [],
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    }

    setMessages((prev) => [...prev, userMessage, initialAssistantMsg])
    setIsStreaming(true)

    const controller = new AbortController()
    setAbortController(controller)

    try {
      await chatService.streamChat(
        queryText,
        'verity-session-default',
        (eventType: string, data: StreamEventPayload) => {
          setMessages((prev) =>
            prev.map((msg) => {
              if (msg.id !== assistantMsgId) return msg

              if (eventType === 'status') {
                return {
                  ...msg,
                  statusMessage: data.message || msg.statusMessage,
                  intent: data.intent || msg.intent,
                }
              }

              if (eventType === 'token') {
                return {
                  ...msg,
                  content: msg.content + (data.token || ''),
                  statusMessage: undefined,
                }
              }

              if (eventType === 'citation') {
                const citation: Citation = {
                  document_id: data.chunk_id || 'doc-ref',
                  chunk_id: data.chunk_id || `chunk-${Date.now()}`,
                  document_name: data.document_name,
                  page_number: data.page_number ?? undefined,
                  section: data.section_heading,
                  locator: data.locator,
                  quote: data.exact_quote,
                  is_verified: data.verified ?? true,
                  verification_tier: 'high',
                }
                return {
                  ...msg,
                  citations: [...(msg.citations || []), citation],
                }
              }

              if (eventType === 'done') {
                return {
                  ...msg,
                  isStreaming: false,
                  statusMessage: undefined,
                  content: msg.content || data.message || 'Evaluation completed.',
                  intent: data.intent || msg.intent,
                }
              }

              if (eventType === 'error') {
                // Defensive safeguard: If response was already marked complete with an answer,
                // do not append post-completion error to the UI message.
                if (!msg.isStreaming && msg.content) {
                  return msg
                }
                return {
                  ...msg,
                  isStreaming: false,
                  statusMessage: undefined,
                  content: msg.content ? `${msg.content}\n\n[Error: ${data.message || 'Workflow failed'}]` : `[Error: ${data.message || 'Workflow failed'}]`,
                }
              }

              return msg
            })
          )
        },
        controller.signal
      )
    } catch (err: any) {
      if (err.name !== 'AbortError') {
        const errorMsg = err.message || 'Stream connection interrupted'
        showToast('error', errorMsg)
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === assistantMsgId
              ? {
                  ...msg,
                  isStreaming: false,
                  statusMessage: undefined,
                  content: msg.content || `Encountered an error: ${errorMsg}`,
                }
              : msg
          )
        )
      }
    } finally {
      setIsStreaming(false)
      setAbortController(null)
      setMessages((prev) =>
        prev.map((msg) => (msg.id === assistantMsgId ? { ...msg, isStreaming: false } : msg))
      )
    }
  }

  const handleStopStreaming = () => {
    if (abortController) {
      abortController.abort()
      setIsStreaming(false)
      setAbortController(null)
    }
  }

  const handleClearChat = () => {
    setMessages([
      {
        id: 'welcome',
        role: 'assistant',
        content:
          "Chat session cleared. You can ask compliance questions or run audit evaluations at any time.",
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      },
    ])
  }

  return (
    <div className="flex flex-col h-[calc(100vh-8.5rem)]">
      {/* Header bar */}
      <div className="flex items-center justify-between pb-4 border-b border-slate-200">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
            AI Assistant & MCP Orchestration
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Real-time streaming agent execution with citation-grounded answers.
          </p>
        </div>

        <button
          type="button"
          onClick={handleClearChat}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-slate-600 hover:text-slate-900 border border-slate-200 hover:bg-slate-100 rounded-lg transition-colors"
          title="Clear session history"
        >
          <RotateCcw className="h-3.5 w-3.5" />
          <span>Clear Chat</span>
        </button>
      </div>

      {/* Messages Scroll Area */}
      <div className="flex-1 overflow-y-auto py-4 space-y-4 pr-2">
        {messages.map((message) => (
          <ChatMessage key={message.id} message={message} />
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Form at bottom */}
      <div className="pt-3 border-t border-slate-200 bg-slate-50/50">
        <ChatInput
          onSendMessage={handleSendMessage}
          disabled={isStreaming}
          isStreaming={isStreaming}
          onStopStreaming={handleStopStreaming}
        />
      </div>
    </div>
  )
}
