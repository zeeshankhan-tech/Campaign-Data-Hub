type HealthBadgeProps = {
  health: string
}

export function HealthBadge({ health }: HealthBadgeProps) {
  const tone = health === 'pass' ? 'ok' : health === 'warn' ? 'warn' : 'fail'
  return <span className={`badge badge-${tone}`}>{health}</span>
}
