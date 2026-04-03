interface MiniSparkBarProps {
  values: number[]
  color?: string
  width?: number
  height?: number
}

export function MiniSparkBar({ values, color = '#06b6d4', width = 80, height = 24 }: MiniSparkBarProps) {
  if (!values.length) return null
  const max = Math.max(...values, 1)
  const barW = Math.floor(width / values.length) - 1

  return (
    <svg width={width} height={height} className="shrink-0">
      {values.map((v, i) => {
        const h = Math.max(2, Math.round((v / max) * height))
        return (
          <rect
            key={i}
            x={i * (barW + 1)}
            y={height - h}
            width={barW}
            height={h}
            fill={color}
            opacity={0.7}
            rx={1}
          />
        )
      })}
    </svg>
  )
}
