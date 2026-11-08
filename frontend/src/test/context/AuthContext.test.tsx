import { render, screen, act } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { AuthProvider, useAuth } from '../../context/AuthContext'

const TestComponent = () => {
  const { currentRole, setRole, hasRole } = useAuth()
  return (
    <div>
      <span data-testid="role">{currentRole}</span>
      <span data-testid="is-admin">{hasRole(['admin']) ? 'YES' : 'NO'}</span>
      <button onClick={() => setRole('auditor')}>Switch to Auditor</button>
      <button onClick={() => setRole('user')}>Switch to User</button>
    </div>
  )
}

describe('AuthContext', () => {
  it('defaults to admin and allows role switching', () => {
    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    )

    expect(screen.getByTestId('role')).toHaveTextContent('admin')
    expect(screen.getByTestId('is-admin')).toHaveTextContent('YES')

    act(() => {
      screen.getByText('Switch to Auditor').click()
    })

    expect(screen.getByTestId('role')).toHaveTextContent('auditor')
    expect(screen.getByTestId('is-admin')).toHaveTextContent('NO')
  })
})

