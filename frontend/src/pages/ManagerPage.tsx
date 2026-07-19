import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { isAxiosError } from 'axios'
import toast from 'react-hot-toast'
import api from '../api/client'
import ConfirmDialog from '../components/ConfirmDialog'
import { useAuth } from '../context/AuthContext'

interface Employee {
  id: number
  email: string
  name: string
  role: string
  department: string
  is_active: boolean
  moodle_id?: number | null
}

interface MoodleCourse {
  id: number
  fullname: string
  shortname: string
  progress?: number | null
}

interface ExternalService {
  id: number
  name: string
  url: string
  has_token: boolean
  login: string
}

function errorMessage(err: unknown, fallback: string): string {
  if (isAxiosError(err)) {
    const detail = err.response?.data?.detail
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail)) {
      return detail.map((item) => item.msg || JSON.stringify(item)).join('; ')
    }
  }
  return fallback
}

function showApiError(err: unknown, fallback: string) {
  toast.error(errorMessage(err, fallback), { duration: 8000 })
}

export default function ManagerPage() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const [services, setServices] = useState<ExternalService[]>([])
  const [selectedServiceId, setSelectedServiceId] = useState('')
  const [showAddForm, setShowAddForm] = useState(false)
  const [showEditForm, setShowEditForm] = useState(false)
  const [newName, setNewName] = useState('')
  const [newUrl, setNewUrl] = useState('')
  const [newToken, setNewToken] = useState('')
  const [newLogin, setNewLogin] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [savingService, setSavingService] = useState(false)

  const [employees, setEmployees] = useState<Employee[]>([])
  const [courses, setCourses] = useState<MoodleCourse[]>([])
  const [userCourses, setUserCourses] = useState<MoodleCourse[]>([])

  const [enrolUserId, setEnrolUserId] = useState('')
  const [enrolCourseId, setEnrolCourseId] = useState('')
  const [unenrolUserId, setUnenrolUserId] = useState('')
  const [unenrolCourseId, setUnenrolCourseId] = useState('')

  const [loadingEmployees, setLoadingEmployees] = useState(true)
  const [loadingServices, setLoadingServices] = useState(true)
  const [loadingCourses, setLoadingCourses] = useState(false)
  const [loadingUserCourses, setLoadingUserCourses] = useState(false)
  const [enrolSubmitting, setEnrolSubmitting] = useState(false)
  const [unenrolSubmitting, setUnenrolSubmitting] = useState(false)
  const [isLoggingOut, setIsLoggingOut] = useState(false)
  const [confirmLogoutOpen, setConfirmLogoutOpen] = useState(false)
  const [confirmDeleteOpen, setConfirmDeleteOpen] = useState(false)

  const canManage = user?.role === 'ADMIN' || user?.role === 'MANAGER'

  const selectedService = services.find((item) => String(item.id) === selectedServiceId)

  const loadServices = useCallback(async () => {
    setLoadingServices(true)
    try {
      const { data } = await api.get<ExternalService[]>('/manager/services')
      setServices(data)
      setSelectedServiceId((prev) => {
        if (prev && data.some((item) => String(item.id) === prev)) return prev
        return data[0] ? String(data[0].id) : ''
      })
    } catch (err) {
      showApiError(err, 'Не удалось загрузить сервисы')
    } finally {
      setLoadingServices(false)
    }
  }, [])

  useEffect(() => {
    if (!canManage) return
    const load = async () => {
      setLoadingEmployees(true)
      try {
        const { data } = await api.get<Employee[]>('/manager/employees')
        setEmployees(data)
      } catch (err) {
        showApiError(err, 'Не удалось загрузить сотрудников')
      } finally {
        setLoadingEmployees(false)
      }
    }
    void load()
    void loadServices()
  }, [canManage, loadServices])

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

  const resetServiceForm = () => {
    setNewName('')
    setNewUrl('')
    setNewToken('')
    setNewLogin('')
    setNewPassword('')
    setShowAddForm(false)
    setShowEditForm(false)
  }

  const openAddForm = () => {
    if (showAddForm) {
      resetServiceForm()
      return
    }
    setShowEditForm(false)
    setNewName('')
    setNewUrl('')
    setNewToken('')
    setNewLogin('')
    setNewPassword('')
    setShowAddForm(true)
  }

  const openEditForm = () => {
    if (!selectedService) {
      toast.error('Выберите сервис')
      return
    }
    setShowAddForm(false)
    setNewName(selectedService.name)
    setNewUrl(selectedService.url)
    setNewToken('')
    setNewLogin(selectedService.login || '')
    setNewPassword('')
    setShowEditForm(true)
  }

  const handleAddService = async (e: FormEvent) => {
    e.preventDefault()
    if (!newUrl.trim()) {
      toast.error('Укажите URL')
      return
    }
    if (!newToken.trim() && !(newLogin.trim() && newPassword)) {
      toast.error('Укажите токен или логин с паролем')
      return
    }
    setSavingService(true)
    try {
      const { data } = await api.post<ExternalService>('/manager/services', {
        name: newName.trim(),
        url: newUrl.trim(),
        token: newToken.trim(),
        login: newLogin.trim(),
        password: newPassword,
      })
      toast.success('Сервис добавлен')
      resetServiceForm()
      await loadServices()
      setSelectedServiceId(String(data.id))
    } catch (err) {
      showApiError(err, 'Не удалось добавить сервис')
    } finally {
      setSavingService(false)
    }
  }

  const handleUpdateService = async (e: FormEvent) => {
    e.preventDefault()
    if (!selectedServiceId) {
      toast.error('Выберите сервис')
      return
    }
    if (!newUrl.trim()) {
      toast.error('Укажите URL')
      return
    }
    setSavingService(true)
    try {
      const { data } = await api.put<ExternalService>(`/manager/services/${selectedServiceId}`, {
        name: newName.trim(),
        url: newUrl.trim(),
        token: newToken.trim(),
        login: newLogin.trim(),
        password: newPassword,
      })
      toast.success('Сервис обновлён')
      resetServiceForm()
      await loadServices()
      setSelectedServiceId(String(data.id))
    } catch (err) {
      showApiError(err, 'Не удалось обновить сервис')
    } finally {
      setSavingService(false)
    }
  }

  const handleDeleteService = async () => {
    if (!selectedServiceId) return
    setConfirmDeleteOpen(false)
    try {
      await api.delete(`/manager/services/${selectedServiceId}`)
      toast.success('Сервис удалён')
      setCourses([])
      setUserCourses([])
      await loadServices()
    } catch (err) {
      showApiError(err, 'Не удалось удалить сервис')
    }
  }

  const requireService = () => {
    if (!selectedServiceId) {
      toast.error('Выберите сервис')
      return false
    }
    return true
  }

  const loadCourses = async () => {
    if (!requireService()) return
    setLoadingCourses(true)
    try {
      const { data } = await api.post<MoodleCourse[]>('/manager/moodle/courses', {
        service_id: Number(selectedServiceId),
      })
      setCourses(data)
      if (data.length === 0) toast('Курсы не найдены')
      else toast.success(`Загружено курсов: ${data.length}`)
    } catch (err) {
      showApiError(err, 'Не удалось загрузить курсы Moodle')
      setCourses([])
    } finally {
      setLoadingCourses(false)
    }
  }

  const loadUserCourses = async (userId: string) => {
    setUnenrolCourseId('')
    setUserCourses([])
    if (!userId) return
    if (!requireService()) return
    setLoadingUserCourses(true)
    try {
      const { data } = await api.post<MoodleCourse[]>('/manager/moodle/user-courses', {
        service_id: Number(selectedServiceId),
        user_id: Number(userId),
      })
      setUserCourses(data)
      if (data.length === 0) toast('У сотрудника нет записанных курсов')
    } catch (err) {
      showApiError(err, 'Не удалось загрузить курсы сотрудника')
      setUserCourses([])
    } finally {
      setLoadingUserCourses(false)
    }
  }

  const handleEnrol = async (e: FormEvent) => {
    e.preventDefault()
    if (!requireService()) return
    if (!enrolUserId || !enrolCourseId) {
      toast.error('Выберите сотрудника и курс')
      return
    }
    setEnrolSubmitting(true)
    try {
      await api.post('/manager/moodle/enrol', {
        service_id: Number(selectedServiceId),
        user_id: Number(enrolUserId),
        course_id: Number(enrolCourseId),
      })
      toast.success('Сотрудник записан на курс')
      if (unenrolUserId === enrolUserId) {
        await loadUserCourses(enrolUserId)
      }
    } catch (err) {
      showApiError(err, 'Не удалось записать на курс')
    } finally {
      setEnrolSubmitting(false)
    }
  }

  const handleUnenrol = async (e: FormEvent) => {
    e.preventDefault()
    if (!requireService()) return
    if (!unenrolUserId || !unenrolCourseId) {
      toast.error('Выберите сотрудника и курс для удаления')
      return
    }
    setUnenrolSubmitting(true)
    try {
      await api.post('/manager/moodle/unenrol', {
        service_id: Number(selectedServiceId),
        user_id: Number(unenrolUserId),
        course_id: Number(unenrolCourseId),
      })
      toast.success('Сотрудник удалён с курса')
      await loadUserCourses(unenrolUserId)
      setUnenrolCourseId('')
    } catch (err) {
      showApiError(err, 'Не удалось удалить с курса')
    } finally {
      setUnenrolSubmitting(false)
    }
  }

  if (!user) return null

  if (!canManage) {
    return (
      <div className="min-h-screen bg-blue-50 flex items-center justify-center px-4">
        <div className="bg-white border border-blue-200 rounded-lg p-8 max-w-md text-center">
          <h1 className="text-xl font-semibold text-blue-900 mb-2">Нет доступа</h1>
          <p className="text-blue-600 text-sm mb-6">
            Страница менеджера доступна только ролям MANAGER и ADMIN.
          </p>
          <Link to="/chat" className="text-blue-700 underline text-sm">
            Вернуться в чат
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-blue-50 flex flex-col">
      <header className="bg-white border-b border-blue-200 px-4 py-3 flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-blue-900">Менеджер</h1>
          <p className="text-sm text-blue-600">{user.name} · {user.email}</p>
        </div>
        <div className="flex items-center gap-2">
          <Link
            to="/chat"
            className="px-4 py-2 rounded-md border border-blue-300 bg-white hover:bg-blue-50 text-blue-700 text-sm font-medium"
          >
            Чат
          </Link>
          <button
            onClick={() => setConfirmLogoutOpen(true)}
            disabled={isLoggingOut}
            className="px-4 py-2 rounded-md border border-blue-300 bg-white hover:bg-blue-50 text-blue-700 text-sm font-medium disabled:opacity-50"
          >
            {isLoggingOut ? 'Выход...' : 'Выйти'}
          </button>
        </div>
      </header>

      <main className="flex-1 px-4 py-6">
        <div className="max-w-4xl mx-auto space-y-6">
          <section className="bg-white border border-blue-200 rounded-lg p-5 shadow-sm">
            <h2 className="text-base font-semibold text-blue-900 mb-4">Подключение к Moodle</h2>

            <div className="flex flex-col sm:flex-row gap-3 sm:items-end">
              <label className="block text-sm flex-1">
                <span className="text-blue-700 font-medium">Сервис</span>
                <select
                  value={selectedServiceId}
                  onChange={(e) => {
                    setSelectedServiceId(e.target.value)
                    setCourses([])
                    setUserCourses([])
                    setEnrolCourseId('')
                    setUnenrolCourseId('')
                    resetServiceForm()
                  }}
                  disabled={loadingServices}
                  className="mt-1 w-full px-3 py-2 rounded-md border border-blue-200 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">
                    {loadingServices
                      ? 'Загрузка...'
                      : services.length === 0
                        ? 'Нет сохранённых сервисов'
                        : 'Выберите сервис'}
                  </option>
                  {services.map((svc) => (
                    <option key={svc.id} value={svc.id}>
                      {svc.name} — {svc.url}
                    </option>
                  ))}
                </select>
              </label>
              <button
                type="button"
                onClick={openAddForm}
                className="px-4 py-2 rounded-md border border-blue-300 text-blue-700 text-sm hover:bg-blue-50 whitespace-nowrap"
              >
                {showAddForm ? 'Отмена' : 'Добавить новый сервис'}
              </button>
            </div>

            {selectedService && (
              <p className="mt-2 text-sm text-blue-800">
                {selectedService.has_token ? 'Авторизация: токен' : `Авторизация: логин ${selectedService.login}`}
              </p>
            )}

            {(showAddForm || showEditForm) && (
              <form
                onSubmit={showEditForm ? handleUpdateService : handleAddService}
                className="mt-4 border-t border-blue-100 pt-4 space-y-3"
              >
                <h3 className="text-sm font-semibold text-blue-900">
                  {showEditForm ? 'Редактирование сервиса' : 'Новый сервис'}
                </h3>
                <div className="grid gap-3 sm:grid-cols-2">
                  <label className="block text-sm sm:col-span-2">
                    <span className="text-blue-700 font-medium">Название</span>
                    <input
                      value={newName}
                      onChange={(e) => setNewName(e.target.value)}
                      placeholder="Moodle прод"
                      className="mt-1 w-full px-3 py-2 rounded-md border border-blue-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </label>
                  <label className="block text-sm sm:col-span-2">
                    <span className="text-blue-700 font-medium">URL</span>
                    <input
                      value={newUrl}
                      onChange={(e) => setNewUrl(e.target.value)}
                      placeholder="https://moodle.example.com"
                      required
                      className="mt-1 w-full px-3 py-2 rounded-md border border-blue-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </label>
                  <label className="block text-sm">
                    <span className="text-blue-700 font-medium">Токен</span>
                    <input
                      value={newToken}
                      onChange={(e) => setNewToken(e.target.value)}
                      placeholder={
                        showEditForm
                          ? 'оставьте пустым, чтобы не менять'
                          : 'webservice token'
                      }
                      className="mt-1 w-full px-3 py-2 rounded-md border border-blue-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </label>
                  <label className="block text-sm">
                    <span className="text-blue-700 font-medium">Логин</span>
                    <input
                      value={newLogin}
                      onChange={(e) => setNewLogin(e.target.value)}
                      placeholder="username"
                      className="mt-1 w-full px-3 py-2 rounded-md border border-blue-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </label>
                  <label className="block text-sm sm:col-span-2">
                    <span className="text-blue-700 font-medium">Пароль</span>
                    <input
                      type="password"
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
                      placeholder={
                        showEditForm
                          ? 'оставьте пустым, чтобы не менять'
                          : 'если используете логин'
                      }
                      className="mt-1 w-full px-3 py-2 rounded-md border border-blue-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  </label>
                </div>
                <div className="flex flex-wrap gap-2">
                  <button
                    type="submit"
                    disabled={savingService}
                    className="px-4 py-2 rounded-md bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white text-sm font-medium"
                  >
                    {savingService
                      ? 'Сохранение...'
                      : showEditForm
                        ? 'Сохранить изменения'
                        : 'Сохранить сервис'}
                  </button>
                  <button
                    type="button"
                    onClick={resetServiceForm}
                    className="px-4 py-2 rounded-md border border-blue-300 text-blue-700 text-sm hover:bg-blue-50"
                  >
                    Отмена
                  </button>
                </div>
              </form>
            )}

            <div className="mt-4 flex flex-wrap gap-2">
              <button
                type="button"
                onClick={loadCourses}
                disabled={loadingCourses || !selectedServiceId}
                className="px-4 py-2 rounded-md bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white text-sm font-medium"
              >
                {loadingCourses ? 'Загрузка...' : 'Загрузить курсы Moodle'}
              </button>
              <button
                type="button"
                onClick={openEditForm}
                disabled={!selectedServiceId || showEditForm}
                className="px-4 py-2 rounded-md border border-blue-300 bg-white hover:bg-blue-50 disabled:opacity-50 text-blue-700 text-sm font-medium"
              >
                Редактировать сервис
              </button>
              <button
                type="button"
                onClick={() => {
                  if (!selectedServiceId) return
                  setConfirmDeleteOpen(true)
                }}
                disabled={!selectedServiceId}
                className="px-4 py-2 rounded-md border border-red-300 bg-red-50 hover:bg-red-100 disabled:opacity-50 text-red-700 text-sm font-medium"
              >
                Удалить сервис
              </button>
            </div>
          </section>

          <section className="bg-white border border-blue-200 rounded-lg p-5 shadow-sm">
            <h2 className="text-base font-semibold text-blue-900 mb-4">Записать на курс</h2>
            <form onSubmit={handleEnrol} className="space-y-3">
              <div className="grid gap-3 sm:grid-cols-2">
                <label className="block text-sm">
                  <span className="text-blue-700 font-medium">Сотрудник</span>
                  <select
                    value={enrolUserId}
                    onChange={(e) => setEnrolUserId(e.target.value)}
                    disabled={loadingEmployees}
                    className="mt-1 w-full px-3 py-2 rounded-md border border-blue-200 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="">
                      {loadingEmployees ? 'Загрузка...' : 'Выберите сотрудника'}
                    </option>
                    {employees.map((emp) => (
                      <option key={emp.id} value={emp.id}>
                        {emp.name} · {emp.email}
                        {emp.moodle_id != null ? ` · Moodle #${emp.moodle_id}` : ''} ({emp.role})
                      </option>
                    ))}
                  </select>
                </label>
                <label className="block text-sm">
                  <span className="text-blue-700 font-medium">Курс Moodle</span>
                  <select
                    value={enrolCourseId}
                    onChange={(e) => setEnrolCourseId(e.target.value)}
                    className="mt-1 w-full px-3 py-2 rounded-md border border-blue-200 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="">
                      {courses.length === 0 ? 'Сначала загрузите курсы' : 'Выберите курс'}
                    </option>
                    {courses.map((course) => (
                      <option key={course.id} value={course.id}>
                        {course.fullname}
                        {course.shortname ? ` (${course.shortname})` : ''}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
              <button
                type="submit"
                disabled={enrolSubmitting}
                className="px-4 py-2 rounded-md bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white text-sm font-medium"
              >
                {enrolSubmitting ? 'Запись...' : 'Записать на курс'}
              </button>
            </form>
          </section>

          <section className="bg-white border border-blue-200 rounded-lg p-5 shadow-sm">
            <h2 className="text-base font-semibold text-blue-900 mb-4">Удалить с курса</h2>
            <form onSubmit={handleUnenrol} className="space-y-3">
              <div className="grid gap-3 sm:grid-cols-2">
                <label className="block text-sm">
                  <span className="text-blue-700 font-medium">Сотрудник</span>
                  <select
                    value={unenrolUserId}
                    onChange={(e) => {
                      const value = e.target.value
                      setUnenrolUserId(value)
                      void loadUserCourses(value)
                    }}
                    disabled={loadingEmployees}
                    className="mt-1 w-full px-3 py-2 rounded-md border border-blue-200 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="">
                      {loadingEmployees ? 'Загрузка...' : 'Выберите сотрудника'}
                    </option>
                    {employees.map((emp) => (
                      <option key={emp.id} value={emp.id}>
                        {emp.name} · {emp.email}
                        {emp.moodle_id != null ? ` · Moodle #${emp.moodle_id}` : ''} ({emp.role})
                      </option>
                    ))}
                  </select>
                </label>
                <label className="block text-sm">
                  <span className="text-blue-700 font-medium">Курс сотрудника</span>
                  <select
                    value={unenrolCourseId}
                    onChange={(e) => setUnenrolCourseId(e.target.value)}
                    disabled={!unenrolUserId || loadingUserCourses}
                    className="mt-1 w-full px-3 py-2 rounded-md border border-blue-200 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
                  >
                    <option value="">
                      {loadingUserCourses
                        ? 'Загрузка курсов...'
                        : !unenrolUserId
                          ? 'Сначала выберите сотрудника'
                          : userCourses.length === 0
                            ? 'Нет записанных курсов'
                            : 'Выберите курс'}
                    </option>
                    {userCourses.map((course) => (
                      <option key={course.id} value={course.id}>
                        {course.fullname}
                        {course.progress != null ? ` · ${course.progress}%` : ''}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
              <button
                type="submit"
                disabled={unenrolSubmitting || !unenrolCourseId}
                className="px-4 py-2 rounded-md border border-red-300 bg-red-50 hover:bg-red-100 disabled:opacity-50 text-red-700 text-sm font-medium"
              >
                {unenrolSubmitting ? 'Удаление...' : 'Удалить с курса'}
              </button>
            </form>
          </section>
        </div>
      </main>

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

      <ConfirmDialog
        open={confirmDeleteOpen}
        title="Удаление сервиса"
        message={
          selectedService
            ? `Удалить сервис «${selectedService.name}» (${selectedService.url})?\nЭто действие нельзя отменить.`
            : 'Удалить выбранный сервис? Это действие нельзя отменить.'
        }
        confirmLabel="Удалить"
        cancelLabel="Отмена"
        danger
        onConfirm={() => {
          void handleDeleteService()
        }}
        onCancel={() => setConfirmDeleteOpen(false)}
      />
    </div>
  )
}
