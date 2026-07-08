import { useCallback, useEffect, useRef, useState } from 'react'

interface UseHorizontalResizeOptions {
  defaultWidth: number
  minWidth: number
  maxWidth: number
  storageKey?: string
}

export function useHorizontalResize({
  defaultWidth,
  minWidth,
  maxWidth,
  storageKey,
}: UseHorizontalResizeOptions) {
  const containerRef = useRef<HTMLDivElement>(null)
  const widthRef = useRef(defaultWidth)

  const [width, setWidth] = useState(() => {
    if (!storageKey) return defaultWidth
    const saved = localStorage.getItem(storageKey)
    const parsed = saved ? Number(saved) : defaultWidth
    return Number.isFinite(parsed) ? parsed : defaultWidth
  })
  const [isResizing, setIsResizing] = useState(false)

  widthRef.current = width

  const startResize = useCallback(() => {
    setIsResizing(true)
  }, [])

  useEffect(() => {
    if (!isResizing) return

    const onMouseMove = (event: MouseEvent) => {
      const container = containerRef.current
      if (!container) return

      const rect = container.getBoundingClientRect()
      const dynamicMax = Math.min(maxWidth, rect.width * 0.75)
      const nextWidth = Math.min(dynamicMax, Math.max(minWidth, rect.right - event.clientX))
      setWidth(nextWidth)
    }

    const onMouseUp = () => {
      setIsResizing(false)
      if (storageKey) {
        localStorage.setItem(storageKey, String(widthRef.current))
      }
    }

    document.body.style.cursor = 'col-resize'
    document.body.style.userSelect = 'none'

    window.addEventListener('mousemove', onMouseMove)
    window.addEventListener('mouseup', onMouseUp)

    return () => {
      document.body.style.cursor = ''
      document.body.style.userSelect = ''
      window.removeEventListener('mousemove', onMouseMove)
      window.removeEventListener('mouseup', onMouseUp)
    }
  }, [isResizing, maxWidth, minWidth, storageKey])

  return {
    containerRef,
    width,
    isResizing,
    startResize,
  }
}
