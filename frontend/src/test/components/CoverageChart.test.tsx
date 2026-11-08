import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { CoverageChart } from '../../components/compliance/CoverageChart'

describe('CoverageChart Component', () => {
  it('calculates coverage percentage and renders legends', () => {
    render(<CoverageChart covered={8} partiallyCovered={2} missing={0} />)

    // Total = 10, covered = 8 -> 80%
    expect(screen.getByText('80%')).toBeInTheDocument()
    expect(screen.getByText('Covered')).toBeInTheDocument()
    expect(screen.getByText('Partially Covered')).toBeInTheDocument()
    expect(screen.getByText('Missing Evidence')).toBeInTheDocument()
  })
})

