import { useEffect, useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { isAxiosError } from 'axios'
import toast from 'react-hot-toast'
import { useAuth } from '../context/AuthContext'
import type { AuthError } from '../types/auth'

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

export default function LoginPage() {
  const { login, user, isLoading: authLoading } = useAuth()
  const navigate = useNavigate()

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [abacError, setAbacError] = useState<string | null>(null)
  const [fieldErrors, setFieldErrors] = useState<{ email?: string; password?: string }>({})

  useEffect(() => {
    if (!authLoading && user) {
      navigate('/welcome', { replace: true })
    }
  }, [authLoading, user, navigate])

  const validate = (): boolean => {
    const errors: { email?: string; password?: string } = {}
    if (!email.trim()) {
      errors.email = 'Введите email'
    } else if (!EMAIL_RE.test(email)) {
      errors.email = 'Некорректный формат email'
    }
    if (!password) {
      errors.password = 'Введите пароль'
    }
    setFieldErrors(errors)
    return Object.keys(errors).length === 0
  }

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setAbacError(null)
    if (!validate()) return

    setIsSubmitting(true)
    try {
      await login(email.trim(), password)
      toast.success('Вход выполнен успешно')
      navigate('/welcome')
    } catch (err) {
      if (isAxiosError<AuthError>(err)) {
        if (err.response?.status === 403) {
          const reason =
            err.response.data?.reason ||
            err.response.data?.detail ||
            'Доступ запрещён политикой безопасности'
          setAbacError(reason)
          toast.error(`Вход запрещён: ${reason}`)
        } else if (err.response?.status === 401) {
          toast.error('Неверный email или пароль')
        } else {
          toast.error('Ошибка сервера. Попробуйте позже.')
        }
      } else {
        toast.error('Не удалось выполнить вход')
      }
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-blue-50 px-4 py-8">
      <div className="w-full max-w-md">
        <div className="bg-white border border-blue-200 rounded-lg p-8 shadow-sm">
          <div className="mb-8">
            <h1 className="text-2xl font-semibold text-blue-900">Вход в систему</h1>
            <p className="text-blue-600 mt-1 text-sm">ABAC-авторизация</p>
          </div>

          {abacError && (
            <div className="mb-6 p-4 rounded-md bg-red-50 border border-red-200">
              <p className="text-red-800 font-medium text-sm">Вход запрещён</p>
              <p className="text-red-700 text-sm mt-1">{abacError}</p>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4" noValidate>
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-blue-900 mb-1">
                Email
              </label>
              <input
                id="email"
                type="email"
                autoComplete="email"
                value={email}
                onChange={(e) => {
                  setEmail(e.target.value)
                  setFieldErrors((prev) => ({ ...prev, email: undefined }))
                  setAbacError(null)
                }}
                className={`w-full px-3 py-2 rounded-md border bg-white text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 ${
                  fieldErrors.email ? 'border-red-400' : 'border-blue-200'
                }`}
                placeholder="user@company.com"
              />
              {fieldErrors.email && <p className="mt-1 text-sm text-red-600">{fieldErrors.email}</p>}
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-medium text-blue-900 mb-1">
                Пароль
              </label>
              <div className="relative">
                <input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  autoComplete="current-password"
                  value={password}
                  onChange={(e) => {
                    setPassword(e.target.value)
                    setFieldErrors((prev) => ({ ...prev, password: undefined }))
                    setAbacError(null)
                  }}
                  className={`w-full px-3 py-2 pr-20 rounded-md border bg-white text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 ${
                    fieldErrors.password ? 'border-red-400' : 'border-blue-200'
                  }`}
                  placeholder="••••••••"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((v) => !v)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-blue-600 hover:text-blue-800 text-sm"
                  aria-label={showPassword ? 'Скрыть пароль' : 'Показать пароль'}
                >
                  {showPassword ? 'Скрыть' : 'Показать'}
                </button>
              </div>
              {fieldErrors.password && <p className="mt-1 text-sm text-red-600">{fieldErrors.password}</p>}
            </div>

            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full py-2.5 px-4 rounded-md bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 disabled:cursor-not-allowed text-white font-medium transition"
            >
              {isSubmitting ? 'Вход...' : 'Войти'}
            </button>
          </form>

          <div className="mt-6 pt-6 border-t border-blue-100">
            <p className="text-blue-600 text-xs text-center">Тестовые аккаунты — пароль: Test123!</p>
            <div className="mt-2 flex flex-wrap gap-2 justify-center">
              {['admin@test.com', 'hr@test.com', 'guest@test.com'].map((acc) => (
                <button
                  key={acc}
                  type="button"
                  onClick={() => {
                    setEmail(acc)
                    setPassword('Test123!')
                    setAbacError(null)
                  }}
                  className="text-xs text-blue-700 hover:text-blue-900 bg-blue-50 hover:bg-blue-100 border border-blue-200 px-2 py-1 rounded transition"
                >
                  {acc}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
