import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { useNavigate } from "react-router-dom"
import { getAuditLogs } from "@/lib/api"
import type { AuditLogFilters, AuditLogOut } from "@/lib/api"
import { formatDateTime } from "@/lib/format"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Skeleton } from "@/components/ui/skeleton"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { ChevronLeft, ChevronRight, FileSearch } from "lucide-react"

const PAGE_SIZE = 20

const targetTypeOptions = [
  { label: "全部对象", value: "all" },
  { label: "认证", value: "auth" },
  { label: "用户", value: "user" },
  { label: "用户组", value: "group" },
  { label: "通道", value: "channel" },
  { label: "Push Key", value: "push_key" },
  { label: "消息", value: "message" },
  { label: "投递", value: "delivery" },
]

const targetTypeLabels: Record<string, string> = {
  auth: "认证",
  user: "用户",
  group: "用户组",
  channel: "通道",
  push_key: "Push Key",
  message: "消息",
  delivery: "投递",
}

function readDetailString(detail: Record<string, unknown>, key: string) {
  const value = detail[key]
  return typeof value === "string" && value ? value : null
}

function getAuditTargetPath(entry: AuditLogOut) {
  switch (entry.target_type) {
    case "user":
      return entry.target_id ? `/users?highlight=${entry.target_id}` : null
    case "group":
      return entry.target_id ? `/groups?highlight=${entry.target_id}` : null
    case "channel":
      return entry.target_id ? `/channels?highlight=${entry.target_id}` : null
    case "push_key":
      return entry.target_id ? `/push-keys?highlight=${entry.target_id}` : null
    case "message":
      return entry.target_id ? `/messages/${entry.target_id}` : null
    case "delivery": {
      const messageId = readDetailString(entry.detail, "message_id")
      return messageId ? `/messages/${messageId}` : null
    }
    default:
      return null
  }
}

export function AuditLogsPage() {
  const navigate = useNavigate()
  const [page, setPage] = useState(0)
  const [action, setAction] = useState("")
  const [targetType, setTargetType] = useState("all")
  const [actorUserId, setActorUserId] = useState("")
  const [activeEntry, setActiveEntry] = useState<AuditLogOut | null>(null)

  const filters: AuditLogFilters = {
    action: action || undefined,
    target_type: targetType === "all" ? undefined : targetType,
    actor_user_id: actorUserId || undefined,
  }

  const { data, isLoading } = useQuery({
    queryKey: ["audit-logs", page, action, targetType, actorUserId],
    queryFn: () => getAuditLogs(page * PAGE_SIZE, PAGE_SIZE, filters),
  })

  const items = data?.items ?? []
  const total = data?.total ?? 0
  const totalPages = Math.ceil(total / PAGE_SIZE)

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-lg font-semibold tracking-tight">审计日志</h1>
        <p className="mt-0.5 text-sm text-muted-foreground">
          追踪登录、授权、用户组、Push Key 与消息重放等关键操作。
        </p>
      </div>

      <div className="grid gap-3 rounded-lg border border-border/60 bg-card p-3 md:grid-cols-4">
        <Input
          value={action}
          onChange={(event) => {
            setPage(0)
            setAction(event.target.value)
          }}
          placeholder="按 action 筛选"
          className="h-9"
        />
        <Select
          value={targetType}
          onValueChange={(value) => {
            setPage(0)
            setTargetType(value ?? "all")
          }}
        >
          <SelectTrigger className="h-9">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {targetTypeOptions.map((option) => (
              <SelectItem key={option.value} value={option.value}>
                {option.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Input
          value={actorUserId}
          onChange={(event) => {
            setPage(0)
            setActorUserId(event.target.value)
          }}
          placeholder="按操作者用户 ID 筛选"
          className="h-9"
        />
        <div className="flex items-center rounded-md border border-dashed border-border/70 px-3 text-xs text-muted-foreground">
          共 {total} 条记录
        </div>
      </div>

      <div className="rounded-lg border border-border/60 overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow className="border-border/60 hover:bg-transparent">
              <TableHead className="h-9 text-xs font-medium text-muted-foreground">时间</TableHead>
              <TableHead className="h-9 text-xs font-medium text-muted-foreground">动作</TableHead>
              <TableHead className="h-9 text-xs font-medium text-muted-foreground">对象</TableHead>
              <TableHead className="h-9 text-xs font-medium text-muted-foreground">操作者</TableHead>
              <TableHead className="h-9 text-xs font-medium text-muted-foreground">目标 ID</TableHead>
              <TableHead className="h-9 text-right text-xs font-medium text-muted-foreground">
                明细
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              Array.from({ length: 8 }).map((_, index) => (
                <TableRow key={index} className="border-border/40">
                  <TableCell colSpan={6} className="py-3">
                    <Skeleton className="h-5 w-full" />
                  </TableCell>
                </TableRow>
              ))
            ) : items.length === 0 ? (
              <TableRow className="border-border/40">
                <TableCell colSpan={6} className="py-10 text-center text-sm text-muted-foreground">
                  暂无审计记录
                </TableCell>
              </TableRow>
            ) : (
              items.map((item) => {
                const targetPath = getAuditTargetPath(item)

                return (
                  <TableRow key={item.id} className="border-border/40">
                    <TableCell className="py-3 text-sm text-muted-foreground">
                      {formatDateTime(item.created_at)}
                    </TableCell>
                    <TableCell className="py-3">
                      <Badge variant="secondary" className="font-mono text-[10px]">
                        {item.action}
                      </Badge>
                    </TableCell>
                    <TableCell className="py-3 text-sm">
                      {targetTypeLabels[item.target_type] ?? item.target_type}
                    </TableCell>
                    <TableCell className="py-3 text-sm text-muted-foreground">
                      {item.actor_username || item.actor_user_id || "-"}
                    </TableCell>
                    <TableCell className="py-3 font-mono text-[10px] text-muted-foreground">
                      {item.target_id || "-"}
                    </TableCell>
                    <TableCell className="py-3 text-right">
                      <div className="flex justify-end gap-2">
                        {targetPath ? (
                          <Button
                            variant="outline"
                            size="sm"
                            className="h-7 text-xs"
                            onClick={() => navigate(targetPath)}
                          >
                            跳转
                          </Button>
                        ) : null}
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-7 text-xs"
                          onClick={() => setActiveEntry(item)}
                        >
                          <FileSearch className="mr-1.5 h-3.5 w-3.5" />
                          查看
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                )
              })
            )}
          </TableBody>
        </Table>
      </div>

      {totalPages > 1 ? (
        <div className="flex items-center justify-end gap-2">
          <Button
            variant="outline"
            size="sm"
            className="h-7 w-7 p-0"
            onClick={() => setPage((value) => Math.max(0, value - 1))}
            disabled={page === 0}
          >
            <ChevronLeft className="h-3.5 w-3.5" />
          </Button>
          <span className="text-xs text-muted-foreground">
            第 {page + 1} 页，共 {totalPages} 页
          </span>
          <Button
            variant="outline"
            size="sm"
            className="h-7 w-7 p-0"
            onClick={() => setPage((value) => Math.min(totalPages - 1, value + 1))}
            disabled={page >= totalPages - 1}
          >
            <ChevronRight className="h-3.5 w-3.5" />
          </Button>
        </div>
      ) : null}

      <Dialog open={Boolean(activeEntry)} onOpenChange={(open) => !open && setActiveEntry(null)}>
        <DialogContent className="max-w-3xl">
          <DialogHeader>
            <DialogTitle>审计明细</DialogTitle>
          </DialogHeader>
          {activeEntry ? (
            <div className="space-y-4">
              <div className="grid gap-3 md:grid-cols-2">
                <div className="rounded-lg border border-border/60 p-3">
                  <p className="text-xs text-muted-foreground">动作</p>
                  <p className="mt-1 font-mono text-sm">{activeEntry.action}</p>
                </div>
                <div className="rounded-lg border border-border/60 p-3">
                  <p className="text-xs text-muted-foreground">对象</p>
                  <p className="mt-1 text-sm">
                    {targetTypeLabels[activeEntry.target_type] ?? activeEntry.target_type}
                  </p>
                </div>
                <div className="rounded-lg border border-border/60 p-3">
                  <p className="text-xs text-muted-foreground">操作者</p>
                  <p className="mt-1 text-sm">
                    {activeEntry.actor_username || activeEntry.actor_user_id || "-"}
                  </p>
                </div>
                <div className="rounded-lg border border-border/60 p-3">
                  <p className="text-xs text-muted-foreground">时间</p>
                  <p className="mt-1 text-sm">{formatDateTime(activeEntry.created_at)}</p>
                </div>
              </div>
              {getAuditTargetPath(activeEntry) ? (
                <div className="flex justify-end">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      const targetPath = getAuditTargetPath(activeEntry)
                      if (!targetPath) return
                      setActiveEntry(null)
                      navigate(targetPath)
                    }}
                  >
                    跳转到对象
                  </Button>
                </div>
              ) : null}
              <div className="rounded-lg border border-border/60 bg-muted/20 p-3">
                <p className="text-xs text-muted-foreground">详细载荷</p>
                <pre className="mt-2 max-h-[50vh] overflow-auto whitespace-pre-wrap break-all text-xs text-foreground">
                  {JSON.stringify(activeEntry.detail, null, 2)}
                </pre>
              </div>
            </div>
          ) : null}
        </DialogContent>
      </Dialog>
    </div>
  )
}
