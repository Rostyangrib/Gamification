export interface DashboardStat {
  label: string
  value: string
}

export interface DashboardSection {
  id: string
  title: string
  columns: string[]
  rows: Record<string, unknown>[]
}

export interface DashboardView {
  stats: DashboardStat[]
  sections: DashboardSection[]
  fallbackText?: string
}

const KEY_LABELS: Record<string, string> = {
  activities: 'Активности',
  users: 'Пользователи',
  criteria: 'Критерии завершения',
  rows: 'Оценки',
  grades: 'Оценки',
  tables: 'Таблицы оценок',
}

const TOOL_LABELS: Record<string, string> = {
  core_completion_get_activities_completion_status: 'Статус активностей',
  core_completion_get_course_completion_status: 'Завершение курса',
  core_course_get_courses: 'Курсы',
  core_enrol_get_enrolled_users: 'Записанные пользователи',
  core_enrol_get_users_courses: 'Курсы пользователя',
  core_user_get_users: 'Пользователи',
  core_user_get_users_by_field: 'Пользователи',
  get_course_progress: 'Прогресс курса',
  core_course_completion_status: 'Прогресс курса',
  gradereport_user_get_grade_items: 'Оценки',
  gradereport_user_get_grades_table: 'Таблица оценок',
}

const FIELD_LABELS: Record<string, string> = {
  id: 'ID',
  cmid: 'ID элемента',
  userid: 'ID пользователя',
  courseid: 'ID курса',
  username: 'Логин',
  fullname: 'ФИО',
  email: 'Email',
  shortname: 'Код',
  idnumber: 'Номер',
  module: 'Модуль',
  state: 'Статус',
  completed_at: 'Завершено',
  completed: 'Завершён',
  title: 'Название',
  status: 'Статус',
  complete: 'Выполнено',
  startdate: 'Начало',
  enddate: 'Окончание',
  visible: 'Видимость',
  progress: 'Прогресс',
  progress_percent: 'Прогресс, %',
  categoryid: 'Категория',
  roles: 'Роли',
  groups: 'Группы',
  user: 'Пользователь',
  item: 'Элемент',
  grade: 'Оценка',
  percentage: 'Процент',
  range: 'Диапазон',
  feedback: 'Отзыв',
  name: 'Название',
  type: 'Тип',
  max: 'Макс.',
  min: 'Мин.',
  enablecompletion: 'Отслеживание',
  course: 'Курс',
}

let sectionCounter = 0

function nextSectionId(): string {
  sectionCounter += 1
  return `section-${sectionCounter}`
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function isRowList(value: unknown): value is Record<string, unknown>[] {
  return (
    Array.isArray(value) &&
    value.length > 0 &&
    value.every((item) => isRecord(item) && !hasNestedTable(item))
  )
}

function hasNestedTable(row: Record<string, unknown>): boolean {
  return Object.values(row).some(
    (value) =>
      Array.isArray(value) &&
      value.length > 0 &&
      value.every((item) => isRecord(item)),
  )
}

export function formatCellValue(value: unknown): string {
  if (value === null || value === undefined || value === '') return '—'
  if (typeof value === 'boolean') return value ? 'Да' : 'Нет'
  if (Array.isArray(value)) {
    if (value.length === 0) return '—'
    if (value.every((item) => typeof item === 'string' || typeof item === 'number')) {
      return value.map(String).join(', ')
    }
    if (value.every((item) => isRecord(item) && 'name' in item)) {
      return value
        .map((item) => String((item as { name?: unknown }).name ?? ''))
        .filter(Boolean)
        .join(', ')
    }
    return JSON.stringify(value)
  }
  if (isRecord(value)) return JSON.stringify(value)
  return String(value)
}

export function columnLabel(key: string): string {
  return FIELD_LABELS[key] ?? key.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}

function sectionTitle(key: string, prefix?: string): string {
  const normalized = key.replace(/_\d+$/, '')
  const label = TOOL_LABELS[normalized] ?? KEY_LABELS[key] ?? columnLabel(key)
  return prefix ? `${prefix}: ${label}` : label
}

function buildSection(title: string, rows: Record<string, unknown>[]): DashboardSection {
  const columns = Array.from(
    rows.reduce((set, row) => {
      Object.keys(row).forEach((key) => {
        if (key !== 'grades') set.add(key)
      })
      return set
    }, new Set<string>()),
  )

  return {
    id: nextSectionId(),
    title,
    columns,
    rows,
  }
}

function collectScalars(data: Record<string, unknown>): DashboardStat[] {
  return Object.entries(data)
    .filter(([, value]) => !Array.isArray(value) && !isRecord(value))
    .map(([key, value]) => ({
      label: columnLabel(key),
      value: formatCellValue(value),
    }))
}

function extractFromObject(
  data: Record<string, unknown>,
  titlePrefix?: string,
  sections: DashboardSection[] = [],
  stats: DashboardStat[] = [],
): { sections: DashboardSection[]; stats: DashboardStat[] } {
  if (typeof data.error === 'string') {
    return { sections, stats }
  }

  if (Array.isArray(data.tables)) {
    for (const table of data.tables) {
      if (!isRecord(table) || !Array.isArray(table.rows) || !isRowList(table.rows)) continue
      const suffix = table.user ? ` — ${formatCellValue(table.user)}` : ''
      sections.push(buildSection(`${sectionTitle('tables')}${suffix}`, table.rows))
    }
  }

  if (Array.isArray(data.users)) {
    const gradeSections: Record<string, unknown>[][] = []
    const plainUsers: Record<string, unknown>[] = []

    for (const entry of data.users) {
      if (!isRecord(entry)) continue
      if (Array.isArray(entry.grades) && isRowList(entry.grades)) {
        gradeSections.push(entry.grades)
        const userName = formatCellValue(entry.user ?? entry.userid ?? 'Пользователь')
        sections.push(buildSection(`Оценки: ${userName}`, entry.grades))
      } else {
        plainUsers.push(entry)
      }
    }

    if (plainUsers.length > 0) {
      sections.push(buildSection(sectionTitle('users', titlePrefix), plainUsers))
    }

    if (gradeSections.length > 0 || plainUsers.length > 0) {
      stats.push(...collectScalars(data))
      return { sections, stats }
    }
  }

  const arrayEntries = Object.entries(data).filter(
    ([key, value]) => key !== 'tables' && Array.isArray(value) && (value as unknown[]).length > 0,
  )

  if (arrayEntries.length > 0) {
    for (const [key, value] of arrayEntries) {
      if (isRowList(value)) {
        sections.push(buildSection(sectionTitle(key, titlePrefix), value))
      }
    }
    stats.push(...collectScalars(data))
    return { sections, stats }
  }

  const scalarStats = collectScalars(data)
  if (scalarStats.length > 0) {
    stats.push(...scalarStats)
  }

  return { sections, stats }
}

function isToolResultMap(data: Record<string, unknown>): boolean {
  return Object.keys(data).some((key) => key in TOOL_LABELS || key.replace(/_\d+$/, '') in TOOL_LABELS)
}

export function buildDashboardView(result: unknown): DashboardView {
  sectionCounter = 0

  if (result === null || result === undefined) {
    return { stats: [], sections: [], fallbackText: 'Нет данных для отображения' }
  }

  if (typeof result === 'string') {
    return { stats: [], sections: [], fallbackText: result }
  }

  if (Array.isArray(result)) {
    if (isRowList(result)) {
      return {
        stats: [{ label: 'Записей', value: String(result.length) }],
        sections: [buildSection('Результат', result)],
      }
    }
    return { stats: [], sections: [], fallbackText: JSON.stringify(result, null, 2) }
  }

  if (!isRecord(result)) {
    return { stats: [], sections: [], fallbackText: String(result) }
  }

  if (typeof result.error === 'string') {
    return { stats: [], sections: [], fallbackText: result.error }
  }

  if (typeof result.message === 'string' && Object.keys(result).length === 1) {
    return { stats: [], sections: [], fallbackText: result.message }
  }

  if (isToolResultMap(result)) {
    const sections: DashboardSection[] = []
    const stats: DashboardStat[] = []

    for (const [key, value] of Object.entries(result)) {
      const prefix = sectionTitle(key.replace(/_\d+$/, ''))
      if (Array.isArray(value) && isRowList(value)) {
        sections.push(buildSection(prefix, value))
        continue
      }
      if (isRecord(value)) {
        const extracted = extractFromObject(value, prefix)
        sections.push(...extracted.sections)
        stats.push(...extracted.stats)
      }
    }

    if (sections.length > 0 || stats.length > 0) {
      return { stats, sections }
    }
  }

  const extracted = extractFromObject(result)
  if (extracted.sections.length > 0 || extracted.stats.length > 0) {
    return extracted
  }

  return { stats: [], sections: [], fallbackText: JSON.stringify(result, null, 2) }
}

export function summarizeResult(result: unknown): string {
  const view = buildDashboardView(result)
  if (view.sections.length > 0) {
    const totalRows = view.sections.reduce((sum, section) => sum + section.rows.length, 0)
    const titles = view.sections.map((section) => section.title).join(', ')
    return `Получено ${totalRows} записей: ${titles}. Подробности — в таблице справа.`
  }
  if (view.stats.length > 0) {
    return 'Данные отображены в панели справа.'
  }
  if (view.fallbackText) {
    return view.fallbackText
  }
  return 'Ответ получен.'
}
