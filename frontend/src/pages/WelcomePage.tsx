import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import ConfirmDialog from '../components/ConfirmDialog'
import { useAuth } from '../context/AuthContext'

export default function WelcomePage() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [isLoggingOut, setIsLoggingOut] = useState(false)
  const [confirmLogoutOpen, setConfirmLogoutOpen] = useState(false)

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

  if (!user) return null

  return (
    <div className="min-h-screen flex items-center justify-center bg-blue-50 px-4 py-8">
      <div className="w-full max-w-lg">
        <div className="bg-white border border-blue-200 rounded-lg p-8 shadow-sm text-center">
          <h1 className="text-2xl font-semibold text-blue-900 mb-1">
            Добро пожаловать, {user.name}!
          </h1>
          <p className="text-blue-600 mb-6">{user.email}</p>

          <div className="grid grid-cols-2 gap-3 text-left mb-8">
            {[
              ['Роль', user.role],
              ['Отдел', user.department],
              ['Допуск', String(user.clearance_level)],
              ['Локация', user.location],
            ].map(([label, value]) => (
              <div key={label} className="bg-blue-50 border border-blue-100 rounded-md px-3 py-2">
                <p className="text-blue-500 text-xs">{label}</p>
                <p className="text-blue-900 text-sm font-medium">{value}</p>
              </div>
            ))}
          </div>

          <button
            onClick={() => setConfirmLogoutOpen(true)}
            disabled={isLoggingOut}
            className="px-6 py-2.5 rounded-md border border-blue-300 bg-white hover:bg-blue-50 text-blue-700 font-medium transition disabled:opacity-50"
          >
            {isLoggingOut ? 'Выход...' : 'Выйти'}
          </button>
        </div>
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
