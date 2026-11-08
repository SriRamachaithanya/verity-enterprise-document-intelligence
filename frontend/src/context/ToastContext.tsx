import React, { createContext, useContext, useState, useCallback } from 'react'
import { CheckCircle2, AlertCircle, Info, AlertTriangle, X } from 'lucide-react'

export type ToastType = 'success' | 'error' | 'info' | 'warning'

interface ToastItem {
  id: string
  message: string
  type: ToastType
}

interface ToastContextType {
  showToast: (arg1: string, arg2?: string) => void
  success: (message: string) => void
  error: (message: string) => void
  info: (message: string) => void
  warning: (message: string) => void
}

const ToastContext = createContext<ToastContextType | undefined>(undefined)

export const ToastProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [toasts, setToasts] = useState<ToastItem[]>([])

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id))
  }, [])

  const showToast = useCallback(
    (arg1: string, arg2?: string) => {
      let toastType: ToastType = 'info'
      let message = arg1

      const validTypes: ToastType[] = ['success', 'error', 'info', 'warning']

      if (validTypes.includes(arg1 as ToastType) && arg2) {
        toastType = arg1 as ToastType
        message = arg2
      } else if (arg2 && validTypes.includes(arg2 as ToastType)) {
        toastType = arg2 as ToastType
        message = arg1
      }

      const id = Math.random().toString(36).substring(2, 9)
      setToasts((prev) => [...prev, { id, message, type: toastType }])

      setTimeout(() => {
        removeToast(id)
      }, 5000)
    },
    [removeToast]
  )

  const success = useCallback((msg: string) => showToast('success', msg), [showToast])
  const error = useCallback((msg: string) => showToast('error', msg), [showToast])
  const info = useCallback((msg: string) => showToast('info', msg), [showToast])
  const warning = useCallback((msg: string) => showToast('warning', msg), [showToast])

  return (
    <ToastContext.Provider value={{ showToast, success, error, info, warning }}>
      {children}
      <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 max-w-md w-full pointer-events-none px-4">
        {toasts.map((toast) => {
          const isError = toast.type === 'error'
          const isSuccess = toast.type === 'success'
          const isWarning = toast.type === 'warning'

          return (
            <div
              key={toast.id}
              className={`pointer-events-auto flex items-start gap-3 p-4 rounded-xl shadow-lg border text-xs transition-all animate-in slide-in-from-bottom-2 ${
                isError
                  ? 'bg-rose-50 border-rose-200 text-rose-800'
                  : isSuccess
                  ? 'bg-emerald-50 border-emerald-200 text-emerald-800'
                  : isWarning
                  ? 'bg-amber-50 border-amber-200 text-amber-800'
                  : 'bg-white border-slate-200 text-slate-800'
              }`}
            >
              {isError && <AlertCircle className="h-4 w-4 text-rose-500 shrink-0 mt-0.5" />}
              {isSuccess && <CheckCircle2 className="h-4 w-4 text-emerald-500 shrink-0 mt-0.5" />}
              {isWarning && <AlertTriangle className="h-4 w-4 text-amber-500 shrink-0 mt-0.5" />}
              {!isError && !isSuccess && !isWarning && (
                <Info className="h-4 w-4 text-blue-500 shrink-0 mt-0.5" />
              )}

              <p className="flex-1 font-medium leading-relaxed">{toast.message}</p>

              <button
                type="button"
                onClick={() => removeToast(toast.id)}
                className="text-slate-400 hover:text-slate-600 shrink-0"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            </div>
          )
        })}
      </div>
    </ToastContext.Provider>
  )
}

export const useToast = (): ToastContextType => {
  const context = useContext(ToastContext)
  if (!context) {
    throw new Error('useToast must be used within a ToastProvider')
  }
  return context
}
