import { useEffect, useRef, useState, type CSSProperties, type FormEvent, type KeyboardEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { isAxiosError } from 'axios'
import toast from 'react-hot-toast'
import api from '../api/client'
import ConfirmDialog from '../components/ConfirmDialog'
import ResultDashboard from '../components/ResultDashboard'
import { useHorizontalResize } from '../hooks/useHorizontalResize'
import { useAuth } from '../context/AuthContext'
import { summarizeResult } from '../utils/resultDashboard'

interface ChatMessage {
  id: number
  role: 'user' | 'assistant' | 'error'
  content: string
}

interface ChatApiResponse {
  result: unknown
  tools_used: string[]
}

interface DashboardState {
  result: unknown
  toolsUsed: string[]
}

interface ExternalService {
  id: number
  name: string
  url: string
  has_token: boolean
  login: string
}

let messageId = 0

const DASHBOARD_MIN_WIDTH = 300
const DASHBOARD_MAX_WIDTH = 960
const DASHBOARD_DEFAULT_WIDTH = 440
const SERVICE_STORAGE_KEY = 'chat-moodle-service-id'

export default function ChatPage() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const [input, setInput] = useState('')
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [dashboard, setDashboard] = useState<DashboardState | null>(null)
  const [isSending, setIsSending] = useState(false)
  const [isLoggingOut, setIsLoggingOut] = useState(false)
  const [confirmLogoutOpen, setConfirmLogoutOpen] = useState(false)
  const [services, setServices] = useState<ExternalService[]>([])
  const [selectedServiceId, setSelectedServiceId] = useState(() => {
    try {
      return localStorage.getItem(SERVICE_STORAGE_KEY) || ''
    } catch {
      return ''
    }
  })
  const [loadingServices, setLoadingServices] = useState(true)
  const { containerRef, width: dashboardWidth, isResizing, startResize } = useHorizontalResize({
    defaultWidth: DASHBOARD_DEFAULT_WIDTH,
    minWidth: DASHBOARD_MIN_WIDTH,
    maxWidth: DASHBOARD_MAX_WIDTH,
    storageKey: 'chat-dashboard-width',
  })

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  useEffect(() => {
    const load = async () => {
      setLoadingServices(true)
      try {
        const { data } = await api.get<ExternalService[]>('/chat/services')
        setServices(data)
        setSelectedServiceId((prev) => {
          if (prev && data.some((item) => String(item.id) === prev)) return prev
          const first = data[0] ? String(data[0].id) : ''
          if (first) {
            try {
              localStorage.setItem(SERVICE_STORAGE_KEY, first)
            } catch {
              /* ignore */
            }
          }
          return first
        })
      } catch (err) {
        let errorText = 'Не удалось загрузить сервисы Moodle'
        if (isAxiosError(err)) {
          const detail = err.response?.data?.detail
          if (typeof detail === 'string') errorText = detail
        }
        toast.error(errorText)
        setServices([])
      } finally {
        setLoadingServices(false)
      }
    }
    void load()
  }, [])

  const handleServiceChange = (value: string) => {
    setSelectedServiceId(value)
    try {
      if (value) localStorage.setItem(SERVICE_STORAGE_KEY, value)
      else localStorage.removeItem(SERVICE_STORAGE_KEY)
    } catch {
      /* ignore */
    }
  }

  const handleLogout = async () => {
    setConfirmLogoutOpen(false)
    setIsLoggingOut(true)
    try {
      await logout()
      toast.success('Вы вышли из системы')
      navigate('/login')
    } catch {
      toast.error('Ошибка при выходе')
    } finally {
      setIsLoggingOut(false)
    }
  }

  const sendMessage = async (e?: FormEvent) => {
    e?.preventDefault()
    const text = input.trim()
    if (!text || isSending) return

    if (!selectedServiceId) {
      toast.error('Выберите сервис Moodle в шапке')
      return
    }

    setInput('')
    setDashboard(null)
    setMessages((prev) => [...prev, { id: ++messageId, role: 'user', content: text }])
    setIsSending(true)

    try {
      const { data } = await api.post<ChatApiResponse>('/chat', {
        message: text,
        service_id: Number(selectedServiceId),
      })
      setDashboard({ result: data.result, toolsUsed: data.tools_used })
      setMessages((prev) => [
        ...prev,
        {
          id: ++messageId,
          role: 'assistant',
          content: summarizeResult(data.result),
        },
      ])
    } catch (err) {
      let errorText = 'Не удалось выполнить запрос'
      if (isAxiosError(err)) {
        const detail = err.response?.data?.detail
        errorText = typeof detail === 'string' ? detail : errorText
      }
      setDashboard(null)
      setMessages((prev) => [...prev, { id: ++messageId, role: 'error', content: errorText }])
      toast.error(errorText)
    } finally {
      setIsSending(false)
    }
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  if (!user) return null

  return (
    <div className="h-screen bg-blue-50 flex flex-col overflow-hidden">
      <header className="shrink-0 bg-white border-b border-blue-200 px-4 py-3 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-lg font-semibold text-blue-900">Чат</h1>
          <p className="text-sm text-blue-600">{user.name} · {user.email}</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <label className="flex items-center gap-2 text-sm text-blue-800">
            <span className="font-medium whitespace-nowrap">Moodle</span>
            <select
              value={selectedServiceId}
              onChange={(e) => handleServiceChange(e.target.value)}
              disabled={loadingServices || isSending}
              className="min-w-[12rem] max-w-[18rem] px-3 py-2 rounded-md border border-blue-200 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
            >
              <option value="">
                {loadingServices
                  ? 'Загрузка...'
                  : services.length === 0
                    ? 'Нет сервисов'
                    : 'Выберите сервис'}
              </option>
              {services.map((svc) => (
                <option key={svc.id} value={svc.id}>
                  {svc.name} — {svc.url}
                </option>
              ))}
            </select>
          </label>
          {(user.role === 'ADMIN' || user.role === 'MANAGER') && (
            <button
              onClick={() => navigate('/manager')}
              className="px-4 py-2 rounded-md border border-blue-300 bg-white hover:bg-blue-50 text-blue-700 text-sm font-medium"
            >
              Менеджер
            </button>
          )}
          <button
            onClick={() => setConfirmLogoutOpen(true)}
            disabled={isLoggingOut}
            className="px-4 py-2 rounded-md border border-blue-300 bg-white hover:bg-blue-50 text-blue-700 text-sm font-medium disabled:opacity-50"
          >
            {isLoggingOut ? 'Выход...' : 'Выйти'}
          </button>
        </div>
      </header>

      <div
        ref={containerRef}
        className={`flex-1 min-h-0 flex flex-col lg:flex-row ${isResizing ? 'select-none' : ''}`}
        style={{ '--dashboard-width': `${dashboardWidth}px` } as CSSProperties}
      >
        <section className="flex-1 min-w-0 flex flex-col border-b lg:border-b-0">
          <main className="flex-1 overflow-y-auto px-4 py-6">
            <div className="max-w-3xl mx-auto space-y-4">
              {messages.length === 0 && (
                <div className="bg-white border border-blue-200 rounded-lg p-6 text-center text-blue-600 text-sm">
                  {services.length === 0 && !loadingServices
                    ? 'Сначала добавьте сервис Moodle на странице менеджера'
                    : 'Начните диалог — результат появится в таблице справа'}
                </div>
              )}

              {messages.map((msg) => (
                <div
                  key={msg.id}
                  className={`rounded-lg p-4 border ${
                    msg.role === 'user'
                      ? 'bg-blue-600 border-blue-600 text-white ml-8'
                      : msg.role === 'error'
                        ? 'bg-red-50 border-red-200 text-red-800 mr-8'
                        : 'bg-white border-blue-200 text-blue-900 mr-8'
                  }`}
                >
                  {msg.role === 'error' && (
                    <p className="text-xs font-medium mb-2 opacity-70">Ошибка</p>
                  )}
                  <p className="whitespace-pre-wrap break-words text-sm">{msg.content}</p>
                </div>
              ))}

              {isSending && (
                <div className="bg-white border border-blue-200 rounded-lg p-4 mr-8 text-blue-600 text-sm">
                  Обработка запроса...
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          </main>

          <footer className="shrink-0 bg-white border-t border-blue-200 px-4 py-4">
            <form onSubmit={sendMessage} className="max-w-3xl mx-auto flex gap-3">
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder={
                  selectedServiceId
                    ? 'Введите сообщение...'
                    : 'Сначала выберите сервис Moodle в шапке'
                }
                rows={2}
                disabled={isSending || !selectedServiceId}
                className="flex-1 px-3 py-2 rounded-md border border-blue-200 bg-white text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none disabled:opacity-50"
              />
              <button
                type="submit"
                disabled={isSending || !input.trim() || !selectedServiceId}
                className="px-5 py-2 rounded-md bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white font-medium self-end"
              >
                {isSending ? '...' : 'Отправить'}
              </button>
            </form>
          </footer>
        </section>

        <div
          role="separator"
          aria-orientation="vertical"
          aria-label="Изменить ширину панели дашборда"
          onMouseDown={startResize}
          className={`hidden lg:block shrink-0 w-1.5 cursor-col-resize transition-colors relative group ${
            isResizing ? 'bg-blue-500' : 'bg-blue-200 hover:bg-blue-400'
          }`}
        >
          <div className="absolute inset-y-0 -left-1.5 -right-1.5" />
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 flex flex-col gap-1 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none">
            <span className="block w-0.5 h-1 rounded-full bg-blue-700" />
            <span className="block w-0.5 h-1 rounded-full bg-blue-700" />
            <span className="block w-0.5 h-1 rounded-full bg-blue-700" />
          </div>
        </div>

        <aside className="w-full lg:w-[var(--dashboard-width)] shrink-0 min-h-[280px] lg:min-h-0">
          <ResultDashboard
            result={dashboard?.result ?? null}
            toolsUsed={dashboard?.toolsUsed}
            isLoading={isSending}
          />
        </aside>
      </div>

      <ConfirmDialog
        open={confirmLogoutOpen}
        title="Выход из системы"
        message="Вы действительно хотите выйти из системы?"
        confirmLabel="Выйти"
        cancelLabel="Отмена"
        onConfirm={() => {
          void handleLogout()
        }}
        onCancel={() => setConfirmLogoutOpen(false)}
      />
    </div>
  )
}
