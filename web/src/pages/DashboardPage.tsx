import { useState } from "react"
import { useAuth } from "@/hooks/useAuth"
import { useQuery } from "@tanstack/react-query"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"
import { Skeleton } from "@/components/ui/skeleton"
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
import {
  Users,
  Radio,
  Mail,
  Activity,
  BarChart3,
  PieChartIcon,
  BookOpen,
} from "lucide-react"
import {
  getDashboardStats,
  getDashboardRequests,
  getDashboardChannels,
} from "@/lib/api"

const AREA_COLOR = "#10b981"

function getGreeting(): string {
  const hour = new Date().getHours()
  if (hour < 6) return "凌晨好"
  if (hour < 9) return "早上好"
  if (hour < 12) return "上午好"
  if (hour < 14) return "中午好"
  if (hour < 18) return "下午好"
  return "晚上好"
}

function TrendTooltip({ active, payload, label }: { active?: boolean; payload?: Array<{ value: number }>; label?: string }) {
  if (!active || !payload?.length) return null
  return (
    <div className="rounded-lg border border-border/50 bg-popover px-3 py-2 text-xs shadow-xl">
      <p className="font-medium text-popover-foreground">{label}</p>
      <p className="text-muted-foreground">{payload[0].value.toLocaleString()} 次请求</p>
    </div>
  )
}

function PieTooltip({ active, payload }: { active?: boolean; payload?: Array<{ name: string; value: number }> }) {
  if (!active || !payload?.length) return null
  return (
    <div className="rounded-lg border border-border/50 bg-popover px-3 py-2 text-xs shadow-xl">
      <p className="font-medium text-popover-foreground">{payload[0].name}</p>
      <p className="text-muted-foreground">{payload[0].value.toLocaleString()} 次</p>
    </div>
  )
}

function StatCard({
  title,
  value,
  subtitle,
  icon: Icon,
  isLoading,
}: {
  title: string
  value: string
  subtitle: string
  icon: React.ComponentType<{ className?: string }>
  isLoading?: boolean
}) {
  return (
    <Card className="border-border/60 bg-card">
      <CardContent className="p-4">
        <div className="flex items-start justify-between">
          <div className="space-y-1.5">
            <p className="text-xs font-medium text-muted-foreground">{title}</p>
            {isLoading ? (
              <Skeleton className="h-7 w-20" />
            ) : (
              <p className="text-2xl font-bold tracking-tight text-foreground">{value}</p>
            )}
            <p className="text-[11px] text-muted-foreground">{subtitle}</p>
          </div>
          <div className="flex h-7 w-7 items-center justify-center rounded-md bg-secondary">
            <Icon className="h-3.5 w-3.5 text-muted-foreground" />
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

export function DashboardPage() {
  const { user } = useAuth()
  const [timeRange, setTimeRange] = useState("7")
  const days = parseInt(timeRange)

  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ["dashboard", "stats", days],
    queryFn: () => getDashboardStats(days),
  })

  const { data: requests, isLoading: requestsLoading } = useQuery({
    queryKey: ["dashboard", "requests", days],
    queryFn: () => getDashboardRequests(days),
  })

  const { data: channels, isLoading: channelsLoading } = useQuery({
    queryKey: ["dashboard", "channels"],
    queryFn: getDashboardChannels,
  })

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <h1 className="text-2xl font-bold tracking-tight text-foreground">
          {getGreeting()}，{user?.display_name ?? "用户"}
        </h1>
        <ToggleGroup
          value={[timeRange]}
          onValueChange={(v) => {
            if (v.length > 0) setTimeRange(v[0])
          }}
          className="rounded-lg border border-border bg-card p-0.5"
        >
          <ToggleGroupItem
            value="7"
            className="h-8 rounded-md px-3 text-xs font-medium data-[state=on]:bg-secondary data-[state=on]:text-secondary-foreground"
          >
            7天
          </ToggleGroupItem>
          <ToggleGroupItem
            value="15"
            className="h-8 rounded-md px-3 text-xs font-medium data-[state=on]:bg-secondary data-[state=on]:text-secondary-foreground"
          >
            15天
          </ToggleGroupItem>
          <ToggleGroupItem
            value="30"
            className="h-8 rounded-md px-3 text-xs font-medium data-[state=on]:bg-secondary data-[state=on]:text-secondary-foreground"
          >
            30天
          </ToggleGroupItem>
        </ToggleGroup>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="平台用户"
          value={stats?.total_users.toLocaleString() ?? "0"}
          subtitle="注册用户数"
          icon={Users}
          isLoading={statsLoading}
        />
        <StatCard
          title="推送渠道"
          value={stats?.total_channels.toLocaleString() ?? "0"}
          subtitle="活跃通道数"
          icon={Radio}
          isLoading={statsLoading}
        />
        <StatCard
          title="累计消息"
          value={stats?.total_messages.toLocaleString() ?? "0"}
          subtitle="历史累计推送"
          icon={Mail}
          isLoading={statsLoading}
        />
        <StatCard
          title={`最近${timeRange}天`}
          value={stats?.recent_requests.toLocaleString() ?? "0"}
          subtitle="推送请求数"
          icon={Activity}
          isLoading={statsLoading}
        />
      </div>

      {/* Charts */}
      <div className="grid gap-4 lg:grid-cols-3">
        {/* Request Distribution */}
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
                      tickFormatter={(v: number) => `${v}`}
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

        {/* Channel Usage */}
        <Card className="border-border/60 bg-card">
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2 text-sm font-medium text-foreground">
              <PieChartIcon className="h-4 w-4 text-muted-foreground" />
              渠道使用率
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

      {/* API Documentation */}
      <Card className="border-border/60 bg-card">
        <CardHeader className="pb-2">
          <CardTitle className="flex items-center gap-2 text-sm font-medium text-foreground">
            <BookOpen className="h-4 w-4 text-muted-foreground" />
            使用文档
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4 pt-0">
          <div className="space-y-1.5">
            <p className="text-xs font-medium text-foreground">推送接口</p>
            <div className="flex items-center gap-2 rounded-md bg-secondary/50 px-3 py-2 font-mono text-xs text-foreground">
              <span className="shrink-0 rounded bg-primary/15 px-1.5 py-0.5 text-[10px] font-semibold text-primary">POST</span>
              <span>/api/v1/push</span>
            </div>
          </div>

          <div className="space-y-1.5">
            <p className="text-xs font-medium text-foreground">请求头</p>
            <pre className="overflow-x-auto rounded-md bg-secondary/50 p-3 font-mono text-[11px] leading-relaxed text-foreground">
{`Content-Type: application/json
Authorization: Bearer <Your-Push-Key>`}
            </pre>
          </div>

          <div className="space-y-1.5">
            <p className="text-xs font-medium text-foreground">请求体</p>
            <pre className="overflow-x-auto rounded-md bg-secondary/50 p-3 font-mono text-[11px] leading-relaxed text-foreground">
{`{
  "title": "通知标题",
  "content": "消息内容",
  "type": "text",
  "channel_ids": ["channel-uuid-1", "channel-uuid-2"] // 可选，默认使用推送密钥的默认渠道
}`}
            </pre>
          </div>

          <div className="space-y-1.5">
            <p className="text-xs font-medium text-foreground">cURL 示例</p>
            <pre className="overflow-x-auto rounded-md bg-secondary/50 p-3 font-mono text-[11px] leading-relaxed text-foreground">
{`curl -X POST https://your-domain.com/api/v1/push \\
  -H "Content-Type: application/json" \\
  -H "Authorization: Bearer <Your-Push-Key>" \\
  -d '{"title":"通知","content":"测试消息","type":"text","channel_ids":["channel-uuid-1"]}'`}
            </pre>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
