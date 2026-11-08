import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { ChatMessage, type ChatMessageData } from '../../components/chat/ChatMessage'

describe('ChatMessage Component', () => {
  it('renders user message correctly', () => {
    const msg: ChatMessageData = {
      id: '1',
      role: 'user',
      content: 'What is our SOC 2 retention policy?',
      timestamp: '10:00 AM',
    }

    render(<ChatMessage message={msg} />)
    expect(screen.getByText('What is our SOC 2 retention policy?')).toBeInTheDocument()
  })

  it('renders assistant message with citations and intent', () => {
    const msg: ChatMessageData = {
      id: '2',
      role: 'assistant',
      content: 'Access logs must be retained for at least 365 days.',
      intent: 'COMPLIANCE_EVALUATION',
      statusMessage: undefined,
      timestamp: '10:01 AM',
      citations: [
        {
          document_id: 'doc-123',
          chunk_id: 'chunk-456',
          source_filename: 'Security_Standard.pdf',
          quote: 'Logs shall be archived and immutable for 365 days.',
          is_verified: true,
          verification_tier: 'high',
        },
      ],
    }

    render(<ChatMessage message={msg} />)
    expect(screen.getByText(/Access logs must be retained/i)).toBeInTheDocument()
    expect(screen.getByText('COMPLIANCE EVALUATION')).toBeInTheDocument()
    expect(screen.getByText('Security_Standard.pdf')).toBeInTheDocument()
    expect(screen.getByText('Ground Truth')).toBeInTheDocument()
  })
})
