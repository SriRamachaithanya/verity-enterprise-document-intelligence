import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import {
  ComplianceBadge,
  AssuranceBadge,
  SeverityBadge,
  RoleBadge,
} from '../../components/common/Badge'

describe('Badge Components', () => {
  it('renders compliance status badges correctly', () => {
    const { rerender } = render(<ComplianceBadge status="COVERED" />)
    expect(screen.getByText('Covered')).toBeInTheDocument()

    rerender(<ComplianceBadge status="PARTIALLY_COVERED" />)
    expect(screen.getByText('Partially Covered')).toBeInTheDocument()

    rerender(<ComplianceBadge status="MISSING" />)
    expect(screen.getByText('Missing Evidence')).toBeInTheDocument()
  })

  it('renders assurance tier badges', () => {
    const { rerender } = render(<AssuranceBadge tier="high" />)
    expect(screen.getByText(/High Assurance/i)).toBeInTheDocument()

    rerender(<AssuranceBadge tier="medium" />)
    expect(screen.getByText(/Medium Assurance/i)).toBeInTheDocument()

    rerender(<AssuranceBadge tier="low" />)
    expect(screen.getByText(/Low Assurance/i)).toBeInTheDocument()
  })

  it('renders severity badges', () => {
    const { rerender } = render(<SeverityBadge severity="critical" />)
    expect(screen.getByText(/critical/i)).toBeInTheDocument()

    rerender(<SeverityBadge severity="high" />)
    expect(screen.getByText(/high/i)).toBeInTheDocument()
  })

  it('renders security role badges', () => {
    const { rerender } = render(<RoleBadge role="admin" />)
    expect(screen.getByText('Admin')).toBeInTheDocument()

    rerender(<RoleBadge role="auditor" />)
    expect(screen.getByText('Auditor')).toBeInTheDocument()
  })
})

