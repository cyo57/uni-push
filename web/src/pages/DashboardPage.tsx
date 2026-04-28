import { Suspense, lazy, useEffect, useRef, useState } from "react"
import { useAuth } from "@/hooks/useAuth"
import { useQuery } from "@tanstack/react-query"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"
import {
  Activity,
  BookOpen,
  Flame,
  HeartPulse,
  Mail,
  OctagonAlert,
  Radio,
  ServerCog,
  Siren,
  Users,
} from "lucide-react"
import {
  getDashboardChannelPerformance,
  getDashboardErrorReasons,
  getDashboardHotKeys,
  getMetricsSnapshot,
  getReadyStatus,
  getDashboardStats,
  getDashboardSummary,
} from "@/lib/api"

const DashboardCharts = lazy(() =>
  import("@/pages/DashboardCharts").then((module) => ({ default: module.DashboardCharts }))
)

function getGreeting(): string {
  const hour = new Date().getHours()
  if (hour < 6) return "凌晨好"
  if (hour < 9) return "早上好"
  if (hour < 12) return "上午好"
  if (hour < 14) return "中午好"
  if (hour < 18) return "下午好"
  return "晚上好"
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

function DashboardChartsFallback() {
  return (
    <div className="grid gap-4 lg:grid-cols-3">
      <Card className="border-border/60 bg-card lg:col-span-2">
        <CardHeader className="pb-2">
          <Skeleton className="h-5 w-24" />
        </CardHeader>
        <CardContent className="pt-0">
          <Skeleton className="h-[280px] w-full" />
        </CardContent>
      </Card>
      <Card className="border-border/60 bg-card">
        <CardHeader className="pb-2">
          <Skeleton className="h-5 w-24" />
        </CardHeader>
        <CardContent className="pt-0 space-y-4">
          <div className="flex justify-center">
            <Skeleton className="h-[220px] w-[220px] rounded-full" />
          </div>
          <div className="flex justify-center gap-3">
            <Skeleton className="h-4 w-16" />
            <Skeleton className="h-4 w-16" />
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

export function DashboardPage() {
  const { user } = useAuth()
  const [timeRange, setTimeRange] = useState("7")
  const [shouldLoadCharts, setShouldLoadCharts] = useState(false)
  const chartsAnchorRef = useRef<HTMLDivElement | null>(null)
  const days = parseInt(timeRange)
  const isAdmin = user?.role === "admin"

  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ["dashboard", "stats", days],
    queryFn: () => getDashboardStats(days),
  })

  const { data: summary, isLoading: summaryLoading } = useQuery({
    queryKey: ["dashboard", "summary"],
    queryFn: getDashboardSummary,
  })

  const { data: hotKeys, isLoading: hotKeysLoading } = useQuery({
    queryKey: ["dashboard", "hot-keys", days],
    queryFn: () => getDashboardHotKeys(days),
  })

  const { data: errorReasons, isLoading: errorReasonsLoading } = useQuery({
    queryKey: ["dashboard", "error-reasons", days],
    queryFn: () => getDashboardErrorReasons(days),
  })

  const { data: channelPerformance, isLoading: channelPerformanceLoading } = useQuery({
    queryKey: ["dashboard", "channel-performance", days],
    queryFn: () => getDashboardChannelPerformance(days),
  })

  const { data: readyStatus, isLoading: readyStatusLoading } = useQuery({
    queryKey: ["ops", "readyz"],
    queryFn: getReadyStatus,
    enabled: isAdmin,
    refetchInterval: 30000,
  })

  const { data: metrics, isLoading: metricsLoading } = useQuery({
    queryKey: ["ops", "metrics"],
    queryFn: getMetricsSnapshot,
    enabled: isAdmin,
    refetchInterval: 30000,
  })

  const totalDeliveries = (summary?.success_count ?? 0) + (summary?.failed_count ?? 0)
  const failureRate =
    totalDeliveries > 0 ? ((summary?.failed_count ?? 0) / totalDeliveries) * 100 : 0
  const dedupeRate =
    metrics && metrics.push_requests_total > 0
      ? (metrics.push_requests_deduplicated_total / metrics.push_requests_total) * 100
      : 0

  useEffect(() => {
    if (shouldLoadCharts) return

    const anchor = chartsAnchorRef.current
    if (!anchor) return

    const timer = window.setTimeout(() => {
      setShouldLoadCharts(true)
    }, 1200)

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) {
          setShouldLoadCharts(true)
        }
      },
      { rootMargin: "200px 0px" }
    )

    observer.observe(anchor)

    return () => {
      window.clearTimeout(timer)
      observer.disconnect()
    }
  }, [shouldLoadCharts])

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

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="今日请求"
          value={summary?.request_count.toLocaleString() ?? "0"}
          subtitle="按本地日期统计"
          icon={Mail}
          isLoading={summaryLoading}
        />
        <StatCard
          title="今日成功投递"
          value={summary?.success_count.toLocaleString() ?? "0"}
          subtitle="成功 delivery 数"
          icon={Activity}
          isLoading={summaryLoading}
        />
        <StatCard
          title="今日失败投递"
          value={summary?.failed_count.toLocaleString() ?? "0"}
          subtitle="失败 delivery 数"
          icon={OctagonAlert}
          isLoading={summaryLoading}
        />
        <StatCard
          title="今日失败率"
          value={`${failureRate.toFixed(1)}%`}
          subtitle="失败 / (成功 + 失败)"
          icon={Flame}
          isLoading={summaryLoading}
        />
      </div>

      <div ref={chartsAnchorRef}>
        {shouldLoadCharts ? (
          <Suspense fallback={<DashboardChartsFallback />}>
            <DashboardCharts days={days} />
          </Suspense>
        ) : (
          <DashboardChartsFallback />
        )}
      </div>

      {isAdmin ? (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-sm font-semibold tracking-tight">运行状态</h2>
              <p className="mt-0.5 text-xs text-muted-foreground">
                读取 /readyz 与 /metrics，监控 worker 心跳、积压与死信。
              </p>
            </div>
            <Badge variant={readyStatus?.status === "ok" ? "default" : "destructive"}>
              {readyStatus?.status === "ok" ? "服务就绪" : "服务降级"}
            </Badge>
          </div>

          {readyStatus?.status !== "ok" && !readyStatusLoading ? (
            <Alert variant="destructive">
              <Siren className="h-4 w-4" />
              <AlertTitle>健康检查异常</AlertTitle>
              <AlertDescription>
                {readyStatus?.detail || "请优先检查数据库、Redis 与 worker 心跳。"}
              </AlertDescription>
            </Alert>
          ) : null}

          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard
              title="Worker 心跳"
              value={metrics?.worker_heartbeat_up === 1 ? "在线" : "离线"}
              subtitle={
                readyStatus?.checks
                  ? Object.entries(readyStatus.checks)
                      .map(([key, value]) => `${key}:${value}`)
                      .join(" · ")
                  : "检查 API / Redis / worker"
              }
              icon={HeartPulse}
              isLoading={metricsLoading || readyStatusLoading}
            />
            <StatCard
              title="投递积压"
              value={metrics?.deliveries_inflight.toLocaleString() ?? "0"}
              subtitle="queued / retrying / sending"
              icon={ServerCog}
              isLoading={metricsLoading}
            />
            <StatCard
              title="死信总量"
              value={metrics?.deliveries_dead_letter_total.toLocaleString() ?? "0"}
              subtitle="需人工排查的终态失败"
              icon={Siren}
              isLoading={metricsLoading}
            />
            <StatCard
              title="幂等去重率"
              value={`${dedupeRate.toFixed(1)}%`}
              subtitle={`去重 ${metrics?.push_requests_deduplicated_total ?? 0} / 总推送 ${metrics?.push_requests_total ?? 0}`}
              icon={OctagonAlert}
              isLoading={metricsLoading}
            />
          </div>
        </div>
      ) : null}

      <div className="grid gap-4 xl:grid-cols-2">
        <Card className="border-border/60 bg-card">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-foreground">热点 Push Key</CardTitle>
          </CardHeader>
          <CardContent className="pt-0">
            <div className="rounded-lg border border-border/60 overflow-hidden">
              <Table>
                <TableHeader>
                  <TableRow className="border-border/60 hover:bg-transparent">
                    <TableHead className="text-xs font-medium text-muted-foreground h-9">业务名称</TableHead>
                    <TableHead className="text-xs font-medium text-muted-foreground h-9 text-right">请求数</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {hotKeysLoading ? (
                    Array.from({ length: 4 }).map((_, index) => (
                      <TableRow key={index} className="border-border/40">
                        <TableCell colSpan={2} className="py-3">
                          <Skeleton className="h-5 w-full" />
                        </TableCell>
                      </TableRow>
                    ))
                  ) : hotKeys?.length ? (
                    hotKeys.map((item) => (
                      <TableRow key={item.business_name} className="border-border/40">
                        <TableCell className="py-3 text-sm">{item.business_name}</TableCell>
                        <TableCell className="py-3 text-right text-sm text-muted-foreground">
                          {item.count}
                        </TableCell>
                      </TableRow>
                    ))
                  ) : (
                    <TableRow className="border-border/40">
                      <TableCell colSpan={2} className="py-8 text-center text-sm text-muted-foreground">
                        暂无数据
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>

        <Card className="border-border/60 bg-card">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-foreground">最近错误原因</CardTitle>
          </CardHeader>
          <CardContent className="pt-0">
            <div className="space-y-2">
              {errorReasonsLoading ? (
                Array.from({ length: 4 }).map((_, index) => (
                  <Skeleton key={index} className="h-12 w-full" />
                ))
              ) : errorReasons?.length ? (
                errorReasons.map((item) => (
                  <div
                    key={item.reason}
                    className="flex items-center justify-between rounded-lg border border-border/60 px-3 py-2"
                  >
                    <div className="min-w-0">
                      <p className="truncate text-sm">{item.reason}</p>
                    </div>
                    <Badge variant="outline" className="text-[10px] font-normal">
                      {item.count}
                    </Badge>
                  </div>
                ))
              ) : (
                <div className="rounded-lg border border-border/60 px-3 py-8 text-center text-sm text-muted-foreground">
                  暂无错误数据
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      <Card className="border-border/60 bg-card">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium text-foreground">通道成功率</CardTitle>
        </CardHeader>
        <CardContent className="pt-0">
          <div className="rounded-lg border border-border/60 overflow-hidden">
            <Table>
              <TableHeader>
                <TableRow className="border-border/60 hover:bg-transparent">
                  <TableHead className="text-xs font-medium text-muted-foreground h-9">通道名称</TableHead>
                  <TableHead className="text-xs font-medium text-muted-foreground h-9">类型</TableHead>
                  <TableHead className="text-xs font-medium text-muted-foreground h-9 text-right">成功</TableHead>
                  <TableHead className="text-xs font-medium text-muted-foreground h-9 text-right">失败</TableHead>
                  <TableHead className="text-xs font-medium text-muted-foreground h-9 text-right">成功率</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {channelPerformanceLoading ? (
                  Array.from({ length: 4 }).map((_, index) => (
                    <TableRow key={index} className="border-border/40">
                      <TableCell colSpan={5} className="py-3">
                        <Skeleton className="h-5 w-full" />
                      </TableCell>
                    </TableRow>
                  ))
                ) : channelPerformance?.length ? (
                  channelPerformance.map((item) => (
                    <TableRow key={`${item.channel_name}-${item.channel_type}`} className="border-border/40">
                      <TableCell className="py-3 text-sm">{item.channel_name}</TableCell>
                      <TableCell className="py-3 text-sm text-muted-foreground">{item.channel_type}</TableCell>
                      <TableCell className="py-3 text-right text-sm text-muted-foreground">{item.success_count}</TableCell>
                      <TableCell className="py-3 text-right text-sm text-muted-foreground">{item.failed_count}</TableCell>
                      <TableCell className="py-3 text-right text-sm">{item.success_rate.toFixed(1)}%</TableCell>
                    </TableRow>
                  ))
                ) : (
                  <TableRow className="border-border/40">
                    <TableCell colSpan={5} className="py-8 text-center text-sm text-muted-foreground">
                      暂无通道表现数据
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

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
Authorization: Bearer <Your-Push-Key>
Idempotency-Key: <Client-Request-Id> // 可选，建议生产开启`}
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
