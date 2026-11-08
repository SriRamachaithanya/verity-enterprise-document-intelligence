import apiClient, { API_BASE_URL } from '../api/client'
import type { ChatResponse, StreamEventPayload } from '../api/types'

export const chatService = {
  chat: async (query: string, session_id?: string): Promise<ChatResponse> => {
    const { data } = await apiClient.post<ChatResponse>('/api/v1/chat', {
      query,
      session_id,
    })
    return data
  },

  streamChat: async (
    query: string,
    session_id?: string,
    onEvent?: (event: string, data: StreamEventPayload) => void,
    signal?: AbortSignal
  ): Promise<void> => {
    const storedKey = localStorage.getItem('verity_api_key') || 'verity-admin-secret-key'
    const response = await fetch(`${API_BASE_URL}/api/v1/chat/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': storedKey,
        Accept: 'text/event-stream',
      },
      body: JSON.stringify({ query, session_id }),
      signal,
    })

    if (!response.ok) {
      let errorMsg = `Server error ${response.status}`
      try {
        const errJson = await response.json()
        if (errJson?.error?.message) {
          errorMsg = errJson.error.message
        }
      } catch {
        // use default status
      }
      throw new Error(errorMsg)
    }

    if (!response.body) {
      throw new Error('ReadableStream not supported by browser.')
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder('utf-8')
    let buffer = ''

    try {
      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const chunks = buffer.split('\n\n')
        buffer = chunks.pop() || ''

        for (const chunk of chunks) {
          if (!chunk.trim()) continue

          const lines = chunk.split('\n')
          let eventType = 'message'
          let rawData = ''

          for (const line of lines) {
            if (line.startsWith('event:')) {
              eventType = line.replace('event:', '').trim()
            } else if (line.startsWith('data:')) {
              rawData = line.replace('data:', '').trim()
            }
          }

          if (rawData && onEvent) {
            try {
              const parsed = JSON.parse(rawData) as StreamEventPayload
              onEvent(eventType, parsed)
            } catch {
              onEvent(eventType, { message: rawData })
            }
          }
        }
      }
    } finally {
      reader.releaseLock()
    }
  },
}

