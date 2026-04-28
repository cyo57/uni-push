import { useQuery } from "@tanstack/react-query"
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip,
} from "recharts"
import { BarChart3, PieChartIcon } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { getDashboardChannels, getDashboardRequests } from "@/lib/api"

const AREA_COLOR = "#10b981"

function TrendTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean
  payload?: Array<{ value: number }>
  label?: string
}) {
  if (!active || !payload?.length) return null
  return (
    <div className="rounded-lg border border-border/50 bg-popover px-3 py-2 text-xs shadow-xl">
      <p className="font-medium text-popover-foreground">{label}</p>
      <p className="text-muted-foreground">{payload[0].value.toLocaleString()} 次请求</p>
    </div>
  )
}

function PieTooltip({
  active,
  payload,
}: {
  active?: boolean
  payload?: Array<{ name: string; value: number }>
}) {
  if (!active || !payload?.length) return null
  return (
    <div className="rounded-lg border border-border/50 bg-popover px-3 py-2 text-xs shadow-xl">
      <p className="font-medium text-popover-foreground">{payload[0].name}</p>
      <p className="text-muted-foreground">{payload[0].value.toLocaleString()} 次</p>
    </div>
  )
}

export function DashboardCharts({ days }: { days: number }) {
  const { data: requests, isLoading: requestsLoading } = useQuery({
    queryKey: ["dashboard", "requests", days],
    queryFn: () => getDashboardRequests(days),
  })

  const { data: channels, isLoading: channelsLoading } = useQuery({
    queryKey: ["dashboard", "channels"],
    queryFn: getDashboardChannels,
  })

  return (
    <div className="grid gap-4 lg:grid-cols-3">
      <Card className="border-border/60 bg-card lg:col-span-2">
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center gap-2 text-sm font-medium text-foreground">
            <BarChart3 className="h-4 w-4 text-muted-foreground" />
            请求分布
          </CardTitle>
        </CardHeader>
        <CardContent className="pt-0">
          <div className="h-[320px] w-full">
            {requestsLoading ? (
              <div className="flex h-full items-center justify-center">
                <Skeleton className="h-[280px] w-full" />
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={requests ?? []} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                  <defs>
                    <linearGradient id="areaGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor={AREA_COLOR} stopOpacity={0.3} />
                      <stop offset="95%" stopColor={AREA_COLOR} stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(255,255,255,0.06)" />
                  <XAxis
                    dataKey="date"
                    tickLine={false}
                    axisLine={false}
                    tick={{ fill: "#a1a1aa", fontSize: 12 }}
                    dy={8}
                  />
                  <YAxis
                    tickLine={false}
                    axisLine={false}
                    tick={{ fill: "#a1a1aa", fontSize: 12 }}
                    tickFormatter={(value: number) => `${value}`}
                  />
                  <Tooltip content={<TrendTooltip />} />
                  <Area
                    type="monotone"
                    dataKey="value"
                    stroke={AREA_COLOR}
                    strokeWidth={2}
                    fill="url(#areaGradient)"
                    dot={false}
                    activeDot={{ r: 4, fill: AREA_COLOR, strokeWidth: 0 }}
                  />
                </AreaChart>
              </ResponsiveContainer>
            )}
          </div>
        </CardContent>
      </Card>

      <Card className="border-border/60 bg-card">
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center gap-2 text-sm font-medium text-foreground">
            <PieChartIcon className="h-4 w-4 text-muted-foreground" />
            通道使用率
          </CardTitle>
        </CardHeader>
        <CardContent className="pt-0">
          <div className="h-[260px] w-full">
            {channelsLoading ? (
              <div className="flex h-full items-center justify-center">
                <Skeleton className="h-[220px] w-[220px] rounded-full" />
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Tooltip content={<PieTooltip />} />
                  <Pie
                    data={channels ?? []}
                    dataKey="value"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    innerRadius="65%"
                    outerRadius="90%"
                    strokeWidth={0}
                  >
                    {(channels ?? []).map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                </PieChart>
              </ResponsiveContainer>
            )}
          </div>
          <div className="flex flex-wrap items-center justify-center gap-x-4 gap-y-2 pt-2">
            {(channels ?? []).map((item) => (
              <div key={item.name} className="flex items-center gap-1.5">
                <div
                  className="h-2 w-2 shrink-0 rounded-full"
                  style={{ backgroundColor: item.color }}
                />
                <span className="text-xs text-muted-foreground">{item.name}</span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
