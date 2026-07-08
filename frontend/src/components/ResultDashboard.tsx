import { buildDashboardView, columnLabel, formatCellValue } from '../utils/resultDashboard'

interface ResultDashboardProps {
  result: unknown | null
  toolsUsed?: string[]
  isLoading?: boolean
}

export default function ResultDashboard({ result, toolsUsed = [], isLoading = false }: ResultDashboardProps) {
  const view = result === null || result === undefined ? null : buildDashboardView(result)
  const hasContent =
    view !== null &&
    (view.sections.length > 0 || view.stats.length > 0 || Boolean(view.fallbackText))

  return (
    <div className="h-full flex flex-col bg-slate-50">
      <div className="px-4 py-3 border-b border-blue-200 bg-white">
        <h2 className="text-sm font-semibold text-blue-900">Дашборд</h2>
        <p className="text-xs text-blue-600 mt-0.5">
          {isLoading ? 'Загрузка данных...' : 'Актуальные данные последнего запроса'}
        </p>
        {toolsUsed.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1.5">
            {toolsUsed.map((tool) => (
              <span
                key={tool}
                className="inline-flex items-center rounded-full bg-blue-100 px-2 py-0.5 text-[10px] font-medium text-blue-700"
              >
                {tool}
              </span>
            ))}
          </div>
        )}
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {isLoading && (
          <div className="rounded-xl border border-blue-200 bg-white p-6 animate-pulse">
            <div className="h-4 w-32 rounded bg-blue-100 mb-4" />
            <div className="space-y-2">
              <div className="h-8 rounded bg-blue-50" />
              <div className="h-8 rounded bg-blue-50" />
              <div className="h-8 rounded bg-blue-50" />
            </div>
          </div>
        )}

        {!isLoading && !hasContent && (
          <div className="rounded-xl border border-dashed border-blue-200 bg-white p-8 text-center">
            <p className="text-sm text-blue-700 font-medium">Таблица появится здесь</p>
            <p className="text-xs text-blue-500 mt-2">
              Отправьте запрос в чат — структура таблицы сформируется автоматически
            </p>
          </div>
        )}

        {!isLoading && view && view.stats.length > 0 && (
          <div className="grid grid-cols-2 gap-3">
            {view.stats.map((stat) => (
              <div
                key={`${stat.label}-${stat.value}`}
                className="rounded-xl border border-blue-200 bg-white px-3 py-3 shadow-sm"
              >
                <p className="text-[11px] uppercase tracking-wide text-blue-500">{stat.label}</p>
                <p className="mt-1 text-sm font-semibold text-blue-900 break-words">{stat.value}</p>
              </div>
            ))}
          </div>
        )}

        {!isLoading &&
          view &&
          view.sections.map((section) => (
            <div
              key={section.id}
              className="rounded-xl border border-blue-200 bg-white shadow-sm overflow-hidden"
            >
              <div className="px-4 py-3 border-b border-blue-100 bg-gradient-to-r from-blue-50 to-white">
                <h3 className="text-sm font-semibold text-blue-900">{section.title}</h3>
                <p className="text-xs text-blue-500 mt-0.5">{section.rows.length} записей</p>
              </div>

              <div className="overflow-x-auto">
                <table className="min-w-full text-sm">
                  <thead className="bg-blue-900/5">
                    <tr>
                      {section.columns.map((column) => (
                        <th
                          key={column}
                          className="px-3 py-2 text-left text-[11px] font-semibold uppercase tracking-wide text-blue-700 whitespace-nowrap"
                        >
                          {columnLabel(column)}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {section.rows.map((row, rowIndex) => (
                      <tr
                        key={`${section.id}-row-${rowIndex}`}
                        className={rowIndex % 2 === 0 ? 'bg-white' : 'bg-blue-50/40'}
                      >
                        {section.columns.map((column) => (
                          <td
                            key={`${section.id}-${rowIndex}-${column}`}
                            className="px-3 py-2 text-blue-900 align-top whitespace-nowrap max-w-[220px] truncate"
                            title={formatCellValue(row[column])}
                          >
                            {formatCellValue(row[column])}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ))}

        {!isLoading && view && view.sections.length === 0 && view.fallbackText && (
          <div className="rounded-xl border border-blue-200 bg-white p-4">
            <p className="text-xs font-medium uppercase tracking-wide text-blue-500 mb-2">Ответ</p>
            <pre className="whitespace-pre-wrap break-words text-sm text-blue-900 font-sans">
              {view.fallbackText}
            </pre>
          </div>
        )}
      </div>
    </div>
  )
}
