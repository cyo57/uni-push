import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { useNavigate } from "react-router-dom"
import { exportMessages, getMessages } from "@/lib/api"
import type { MessageStatus } from "@/lib/api"
import { formatDateTime } from "@/lib/format"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { Input } from "@/components/ui/input"
import { Skeleton } from "@/components/ui/skeleton"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { toast } from "sonner"
import { ChevronLeft, ChevronRight, Download, RotateCcw } from "lucide-react"

const PAGE_SIZE = 20

const statusClasses: Record<MessageStatus, string> = {
  queued: "bg-amber-500/10 text-amber-400 hover:bg-amber-500/15",
  processing: "bg-blue-500/10 text-blue-400 hover:bg-blue-500/15",
  success: "bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/15",
  partial_success: "bg-orange-500/10 text-orange-400 hover:bg-orange-500/15",
  failed: "bg-red-500/10 text-red-400 hover:bg-red-500/15",
}

const typeLabels: Record<string, string> = {
  text: "文本",
  markdown: "Markdown",
}

const statusLabels: Record<MessageStatus, string> = {
  queued: "排队中",
  processing: "处理中",
  success: "成功",
  partial_success: "部分成功",
  failed: "失败",
}

const statusOptions: { label: string; value: MessageStatus }[] = [
  { label: "排队中", value: "queued" },
  { label: "处理中", value: "processing" },
  { label: "成功", value: "success" },
  { label: "部分成功", value: "partial_success" },
  { label: "失败", value: "failed" },
]

function toggleStatus(values: MessageStatus[], value: MessageStatus, checked: boolean) {
  if (checked) {
    return Array.from(new Set([...values, value]))
  }

  return values.filter((item) => item !== value)
}

export function MessagesPage() {
  const navigate = useNavigate()
  const [page, setPage] = useState(0)
  const [search, setSearch] = useState("")
  const [statusFilters, setStatusFilters] = useState<MessageStatus[]>([])

  const { data, isLoading } = useQuery({
    queryKey: ["messages", page, search, statusFilters.join(",")],
    queryFn: () =>
      getMessages(page * PAGE_SIZE, PAGE_SIZE, {
        q: search || undefined,
        status: statusFilters,
      }),
  })

  async function handleExport() {
    const blob = await exportMessages({
      q: search || undefined,
      status: statusFilters,
    })
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement("a")
    link.href = url
    link.download = "messages.csv"
    link.click()
    window.URL.revokeObjectURL(url)
    toast.success("消息记录已导出")
  }

  function resetFilters() {
    setPage(0)
    setSearch("")
    setStatusFilters([])
  }

  const items = data?.items ?? []
  const total = data?.total ?? 0
  const totalPages = Math.ceil(total / PAGE_SIZE)
  const hasActiveFilters = Boolean(search) || statusFilters.length > 0

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-lg font-semibold tracking-tight">消息记录</h1>
        <p className="mt-0.5 text-sm text-muted-foreground">
          查看每条推送消息的投递结果、使用人、密钥与通道信息
        </p>
      </div>

      <div className="space-y-4 rounded-lg border border-border/60 bg-card p-4">
        <div className="flex flex-col gap-3 md:flex-row md:items-center">
          <Input
            value={search}
            onChange={(event) => {
              setPage(0)
              setSearch(event.target.value)
            }}
            placeholder="搜索消息 ID、密钥名称、标题、使用人"
            className="h-8 text-sm md:max-w-sm"
          />
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Badge variant="outline" className="font-normal">
              共 {total} 条
            </Badge>
            {hasActiveFilters ? (
              <Button variant="ghost" size="sm" className="h-7 px-2 text-xs" onClick={resetFilters}>
                <RotateCcw className="mr-1 h-3 w-3" />
                清空筛选
              </Button>
            ) : null}
          </div>
          <Button variant="outline" size="sm" className="h-8 text-xs md:ml-auto" onClick={handleExport}>
            <Download className="mr-1.5 h-3.5 w-3.5" />
            导出 CSV
          </Button>
        </div>

        <div className="space-y-2">
          <p className="text-xs font-medium text-muted-foreground">状态筛选</p>
          <div className="flex flex-wrap gap-2">
            {statusOptions.map((status) => (
              <label
                key={status.value}
                className="flex items-center gap-2 rounded-md border border-border/60 px-3 py-2 text-sm"
              >
                <Checkbox
                  checked={statusFilters.includes(status.value)}
                  onCheckedChange={(checked) => {
                    setPage(0)
                    setStatusFilters((previous) =>
                      toggleStatus(previous, status.value, checked === true)
                    )
                  }}
                />
                <span>{status.label}</span>
              </label>
            ))}
          </div>
        </div>
      </div>

      <div className="overflow-hidden rounded-lg border border-border/60">
        <Table>
          <TableHeader>
            <TableRow className="border-border/60 hover:bg-transparent">
              <TableHead className="h-9 text-xs font-medium text-muted-foreground">ID</TableHead>
              <TableHead className="h-9 text-xs font-medium text-muted-foreground">使用人</TableHead>
              <TableHead className="h-9 text-xs font-medium text-muted-foreground">密钥名称</TableHead>
              <TableHead className="h-9 text-xs font-medium text-muted-foreground">标题</TableHead>
              <TableHead className="h-9 text-xs font-medium text-muted-foreground">渠道</TableHead>
              <TableHead className="h-9 text-xs font-medium text-muted-foreground">类型</TableHead>
              <TableHead className="h-9 text-xs font-medium text-muted-foreground">状态</TableHead>
              <TableHead className="h-9 text-xs font-medium text-muted-foreground">投递情况</TableHead>
              <TableHead className="h-9 text-xs font-medium text-muted-foreground">创建时间</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              Array.from({ length: 5 }).map((_, index) => (
                <TableRow key={index} className="border-border/40">
                  <TableCell colSpan={9} className="py-3">
                    <Skeleton className="h-5 w-full" />
                  </TableCell>
                </TableRow>
              ))
            ) : items.length === 0 ? (
              <TableRow className="border-border/40">
                <TableCell colSpan={9} className="py-8 text-center text-sm text-muted-foreground">
                  暂无消息
                </TableCell>
              </TableRow>
            ) : (
              items.map((msg) => (
                <TableRow
                  key={msg.id}
                  className="cursor-pointer border-border/40 transition-colors hover:bg-muted/30"
                  onClick={() => navigate(`/messages/${msg.id}`)}
                >
                  <TableCell className="py-3 font-mono text-[10px] text-muted-foreground">
                    {msg.id}
                  </TableCell>
                  <TableCell className="py-3 text-sm">{msg.user_display_name}</TableCell>
                  <TableCell className="py-3 text-sm">{msg.push_key_business_name}</TableCell>
                  <TableCell className="max-w-xs py-3 text-sm truncate">{msg.title}</TableCell>
                  <TableCell className="py-3">
                    <div className="flex flex-wrap items-center gap-1.5">
                      {msg.channel_names.slice(0, 2).map((channelName) => (
                        <Badge key={channelName} variant="secondary" className="text-[10px] font-normal">
                          {channelName}
                        </Badge>
                      ))}
                      {msg.channel_names.length > 2 ? (
                        <Badge variant="outline" className="text-[10px] font-normal">
                          +{msg.channel_names.length - 2}
                        </Badge>
                      ) : null}
                    </div>
                  </TableCell>
                  <TableCell className="py-3">
                    <Badge variant="secondary" className="text-[10px] font-normal">
                      {typeLabels[msg.message_type] ?? msg.message_type}
                    </Badge>
                  </TableCell>
                  <TableCell className="py-3">
                    <Badge className={`text-[10px] font-normal ${statusClasses[msg.status]}`}>
                      {statusLabels[msg.status]}
                    </Badge>
                  </TableCell>
                  <TableCell className="py-3">
                    <span className="text-sm text-muted-foreground">
                      {msg.success_count}/{msg.delivery_count}
                    </span>
                    {msg.failed_count > 0 ? (
                      <span className="ml-1 text-sm text-red-400">（失败 {msg.failed_count}）</span>
                    ) : null}
                  </TableCell>
                  <TableCell className="py-3 text-sm text-muted-foreground">
                    {formatDateTime(msg.created_at)}
                  </TableCell>
                </TableRow>
              ))
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
    </div>
  )
}
