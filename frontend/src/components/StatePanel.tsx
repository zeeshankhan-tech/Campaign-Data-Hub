type StatePanelProps = {
  status: 'loading' | 'error' | 'empty'
  message: string
}

export function StatePanel({ status, message }: StatePanelProps) {
  const className =
    status === 'error' ? 'state-panel error' : status === 'empty' ? 'state-panel muted' : 'state-panel'
  return (
    <div className={className} role="status" aria-live="polite">
      {message}
    </div>
  )
}
