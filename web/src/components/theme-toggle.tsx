import { useEffect, useState } from "react"
import { Moon, Sun } from "lucide-react"
import { useTheme } from "next-themes"
import { Button } from "@/components/ui/button"

export function ThemeToggle({
  className,
  compact = false,
}: {
  className?: string
  compact?: boolean
}) {
  const { resolvedTheme, setTheme } = useTheme()
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)
  }, [])

  const isDark = mounted && resolvedTheme === "dark"

  return (
    <Button
      type="button"
      variant="outline"
      size={compact ? "sm" : "default"}
      className={className}
      onClick={() => setTheme(isDark ? "light" : "dark")}
      title={isDark ? "切换到浅色模式" : "切换到深色模式"}
    >
      {isDark ? (
        <Sun className="h-3.5 w-3.5" />
      ) : (
        <Moon className="h-3.5 w-3.5" />
      )}
      <span>{isDark ? "浅色" : "深色"}</span>
    </Button>
  )
}
