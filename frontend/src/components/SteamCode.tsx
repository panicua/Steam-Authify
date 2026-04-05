import { useEffect, useRef, useState } from 'react'
import { toast } from 'sonner'

interface SteamCodeProps {
  code: string
  expiresIn: number
  onExpired?: () => void
}

export default function SteamCode({ code, expiresIn, onExpired }: SteamCodeProps) {
  const [remaining, setRemaining] = useState(expiresIn)
  const onExpiredRef = useRef(onExpired)
  onExpiredRef.current = onExpired

  useEffect(() => {
    setRemaining(expiresIn)
  }, [expiresIn, code])

  useEffect(() => {
    if (remaining <= 0) {
      onExpiredRef.current?.()
      return
    }
    const timer = setTimeout(() => setRemaining((r) => r - 1), 1000)
    return () => clearTimeout(timer)
  }, [remaining])

  const progress = remaining / 30

  const copyCode = () => {
    navigator.clipboard.writeText(code)
    toast.success('Copied!')
  }

  return (
    <div className="flex items-center gap-3">
      <span
        className="cursor-pointer rounded px-1 font-mono text-3xl font-bold tracking-[0.3em] transition-colors hover:bg-muted active:bg-muted/70"
        onClick={copyCode}
        title="Click to copy"
      >
        {code}
      </span>
      <div className="relative h-10 w-10">
        <svg className="h-10 w-10 -rotate-90" viewBox="0 0 36 36">
          <circle
            cx="18" cy="18" r="15"
            fill="none"
            stroke="currentColor"
            strokeWidth="3"
            className="text-muted"
          />
          <circle
            cx="18" cy="18" r="15"
            fill="none"
            stroke="currentColor"
            strokeWidth="3"
            strokeDasharray={`${progress * 94.25} 94.25`}
            strokeLinecap="round"
            className={remaining <= 5 ? 'text-destructive' : 'text-primary'}
          />
        </svg>
        <span className="absolute inset-0 flex items-center justify-center text-xs font-medium">
          {remaining}
        </span>
      </div>
    </div>
  )
}
