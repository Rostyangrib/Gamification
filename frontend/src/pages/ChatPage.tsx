import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { isAxiosError } from 'axios'
import toast from 'react-hot-toast'
import api from '../api/client'
import { useAuth } from '../context/AuthContext'

interface ChatMessage {
  id: number
  role: 'user' | 'assistant' | 'error'
  content: string
  toolsUsed?: string[]
}

interface ChatApiResponse {
  result: unknown
  tools_used: string[]
}

let messageId = 0

function formatResult(result: unknown): string {
  if (typeof result === 'string') return result
  return JSON.stringify(result, null, 2)
}

export default function ChatPage() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const [input, setInput] = useState('')
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [isSending, setIsSending] = useState(false)
  const [isLoggingOut, setIsLoggingOut] = useState(false)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleLogout = async () => {
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

    setInput('')
    setMessages((prev) => [...prev, { id: ++messageId, role: 'user', content: text }])
    setIsSending(true)

    try {
      const { data } = await api.post<ChatApiResponse>('/chat', { message: text })
      setMessages((prev) => [
        ...prev,
        {
          id: ++messageId,
          role: 'assistant',
          content: formatResult(data.result),
          toolsUsed: data.tools_used,
        },
      ])
    } catch (err) {
      let errorText = 'Не удалось выполнить запрос'
      if (isAxiosError(err)) {
        const detail = err.response?.data?.detail
        errorText = typeof detail === 'string' ? detail : errorText
      }
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
    <div className="min-h-screen bg-blue-50 flex flex-col">
      <header className="bg-white border-b border-blue-200 px-4 py-3 flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-blue-900">Чат</h1>
          <p className="text-sm text-blue-600">{user.name} · {user.email}</p>
        </div>
        <button
          onClick={handleLogout}
          disabled={isLoggingOut}
          className="px-4 py-2 rounded-md border border-blue-300 bg-white hover:bg-blue-50 text-blue-700 text-sm font-medium disabled:opacity-50"
        >
          {isLoggingOut ? 'Выход...' : 'Выйти'}
        </button>
      </header>

      <main className="flex-1 overflow-y-auto px-4 py-6">
        <div className="max-w-3xl mx-auto space-y-4">
          {messages.length === 0 && (
            <div className="bg-white border border-blue-200 rounded-lg p-6 text-center text-blue-600 text-sm">
              Начните диалог
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
              <pre className="whitespace-pre-wrap break-words text-sm font-sans">{msg.content}</pre>
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

      <footer className="bg-white border-t border-blue-200 px-4 py-4">
        <form onSubmit={sendMessage} className="max-w-3xl mx-auto flex gap-3">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Введите сообщение..."
            rows={2}
            disabled={isSending}
            className="flex-1 px-3 py-2 rounded-md border border-blue-200 bg-white text-gray-900 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={isSending || !input.trim()}
            className="px-5 py-2 rounded-md bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white font-medium self-end"
          >
            {isSending ? '...' : 'Отправить'}
          </button>
        </form>
      </footer>
    </div>
  )
}
