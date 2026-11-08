import React, { createContext, useContext, useState, useEffect } from 'react'
import type { AuthenticatedUser, UserRole } from '../api/types'

interface AuthContextType {
  user: AuthenticatedUser
  currentRole: UserRole
  setRole: (role: UserRole) => void
  switchRole: (role: UserRole) => void
  setCustomApiKey: (key: string, role?: UserRole) => void
  hasRole: (roles: UserRole[]) => boolean
  isAdmin: boolean
  isAuditor: boolean
  canUpload: boolean
  canDelete: boolean
  canAudit: boolean
}

const DEFAULT_KEYS: Record<UserRole, string> = {
  admin: 'verity-admin-secret-key',
  auditor: 'verity-auditor-secret-key',
  user: 'verity-user-secret-key',
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [role, setRoleState] = useState<UserRole>(() => {
    return (localStorage.getItem('verity_role') as UserRole) || 'admin'
  })
  const [apiKey, setApiKey] = useState<string>(() => {
    return localStorage.getItem('verity_api_key') || DEFAULT_KEYS.admin
  })

  useEffect(() => {
    localStorage.setItem('verity_role', role)
    localStorage.setItem('verity_api_key', apiKey)
  }, [role, apiKey])

  const switchRole = (newRole: UserRole) => {
    setRoleState(newRole)
    const newKey = DEFAULT_KEYS[newRole]
    setApiKey(newKey)
  }

  const setCustomApiKey = (key: string, customRole: UserRole = 'admin') => {
    setApiKey(key)
    setRoleState(customRole)
  }

  const hasRole = (roles: UserRole[]): boolean => {
    return roles.includes(role)
  }

  const user: AuthenticatedUser = {
    userId: `${role}-user`,
    role,
    apiKey,
  }

  const isAdmin = role === 'admin'
  const isAuditor = role === 'admin' || role === 'auditor'
  const canUpload = isAdmin
  const canDelete = isAdmin
  const canAudit = isAuditor

  return (
    <AuthContext.Provider
      value={{
        user,
        currentRole: role,
        setRole: switchRole,
        switchRole,
        setCustomApiKey,
        hasRole,
        isAdmin,
        isAuditor,
        canUpload,
        canDelete,
        canAudit,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
