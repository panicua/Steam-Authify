import { useEffect, useRef } from 'react'

interface TelegramLoginButtonProps {
  botName: string
  onAuth: (user: TelegramUser) => void
  buttonSize?: 'large' | 'medium' | 'small'
  cornerRadius?: number
}

export interface TelegramUser {
  id: number
  first_name?: string
  last_name?: string
  username?: string
  photo_url?: string
  auth_date: number
  hash: string
}

const CALLBACK_NAME = '__tg_login_callback'

// Register the global callback once, outside React lifecycle.
// This ensures it survives StrictMode's mount/unmount/remount cycle
// and is always available when the Telegram popup returns.
let onAuthHandler: ((user: TelegramUser) => void) | null = null
;((window as unknown) as Record<string, unknown>)[CALLBACK_NAME] = (user: TelegramUser) => {
  onAuthHandler?.(user)
}

export default function TelegramLoginButton({
  botName,
  onAuth,
  buttonSize = 'large',
  cornerRadius = 8,
}: TelegramLoginButtonProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const mountedRef = useRef(false)

  // Always keep the handler pointing to the latest onAuth
  onAuthHandler = onAuth

  useEffect(() => {
    // Skip the first mount in StrictMode — only render the widget once
    // the effect is "stable" (i.e. after the cleanup+remount cycle).
    // In production (no StrictMode), this fires on first mount normally.
    if (mountedRef.current) return
    mountedRef.current = true

    const script = document.createElement('script')
    script.src = 'https://telegram.org/js/telegram-widget.js?22'
    script.async = true
    script.setAttribute('data-telegram-login', botName)
    script.setAttribute('data-size', buttonSize)
    script.setAttribute('data-radius', String(cornerRadius))
    script.setAttribute('data-onauth', `${CALLBACK_NAME}(user)`)
    script.setAttribute('data-request-access', 'write')

    const container = containerRef.current
    if (container) {
      container.innerHTML = ''
      container.appendChild(script)
    }

    // No cleanup that destroys the widget — the iframe and its popup
    // opener reference must survive React's lifecycle.
  }, [botName, buttonSize, cornerRadius])

  return <div ref={containerRef} />
}
