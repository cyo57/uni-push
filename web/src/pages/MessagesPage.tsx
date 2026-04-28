import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { useNavigate } from "react-router-dom"
import { exportMessages, getMessages } from "@/lib/api"
import type { MessageStatus } from "@/lib/api"
import { formatDateTime } from "@/lib/format"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { ChevronLeft, ChevronRight, Download } from "lucide-react"
import { toast } from "sonner"

const PAGE_SIZE = 20
type MessageFilterValue = MessageStatus | "all"

const statusVariants: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
  queued: "secondary",
  processing: "secondary",
  success: "default",
  partial_success: "outline",
  failed: "destructive",
}

const statusClasses: Record<string, string> = {
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

const statusLabels: Record<string, string> = {
  queued: "排队中",
  processing: "处理中",
  success: "成功",
  partial_success: "部分成功",
  failed: "失败",
}

export function MessagesPage() {
  const navigate = useNavigate()
  const [page, setPage] = useState(0)
  const [search, setSearch] = useState("")
  const [statusFilter, setStatusFilter] = useState<MessageFilterValue>("all")
  const effectiveStatus = statusFilter === "all" ? undefined : statusFilter

  const { data, isLoading } = useQuery({
    queryKey: ["messages", page, search, statusFilter],
    queryFn: () =>
      getMessages(page * PAGE_SIZE, PAGE_SIZE, {
        q: search || undefined,
        status: effectiveStatus,
      }),
  })

  async function handleExport() {
    const blob = await exportMessages({
      q: search || undefined,
      status: effectiveStatus,
    })
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement("a")
    link.href = url
    link.download = "messages.csv"
    link.click()
    window.URL.revokeObjectURL(url)
    toast.success("消息记录已导出")
  }

  const items = data?.items ?? []
  const total = data?.total ?? 0
  const totalPages = Math.ceil(total / PAGE_SIZE)

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-lg font-semibold tracking-tight">消息记录</h1>
        <p className="text-sm text-muted-foreground mt-0.5">查看每条推送消息的投递结果</p>
      </div>

      <div className="flex flex-col gap-3 rounded-lg border border-border/60 bg-card p-3 md:flex-row md:items-center">
        <Input
          value={search}
          onChange={(e) => {
            setPage(0)
            setSearch(e.target.value)
          }}
          placeholder="搜索消息 ID、业务名称、标题"
          className="h-8 text-sm"
        />
        <Select
          value={statusFilter}
          onValueChange={(value) => {
            setPage(0)
            setStatusFilter((value ?? "all") as MessageFilterValue)
          }}
        >
          <SelectTrigger className="h-8 w-full text-sm md:w-44">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">全部状态</SelectItem>
            <SelectItem value="queued">排队中</SelectItem>
            <SelectItem value="processing">处理中</SelectItem>
            <SelectItem value="success">成功</SelectItem>
            <SelectItem value="partial_success">部分成功</SelectItem>
            <SelectItem value="failed">失败</SelectItem>
          </SelectContent>
        </Select>
        <Button variant="outline" size="sm" className="h-8 text-xs" onClick={handleExport}>
          <Download className="mr-1.5 h-3.5 w-3.5" />
          导出 CSV
        </Button>
      </div>

      <div className="rounded-lg border border-border/60 overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow className="border-border/60 hover:bg-transparent">
              <TableHead className="text-xs font-medium text-muted-foreground h-9">ID</TableHead>
              <TableHead className="text-xs font-medium text-muted-foreground h-9">业务</TableHead>
              <TableHead className="text-xs font-medium text-muted-foreground h-9">标题</TableHead>
              <TableHead className="text-xs font-medium text-muted-foreground h-9">类型</TableHead>
              <TableHead className="text-xs font-medium text-muted-foreground h-9">状态</TableHead>
              <TableHead className="text-xs font-medium text-muted-foreground h-9">投递情况</TableHead>
              <TableHead className="text-xs font-medium text-muted-foreground h-9">创建时间</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              Array.from({ length: 5 }).map((_, i) => (
                <TableRow key={i} className="border-border/40">
                  <TableCell colSpan={7} className="py-3">
                    <Skeleton className="h-5 w-full" />
                  </TableCell>
                </TableRow>
              ))
            ) : items.length === 0 ? (
              <TableRow className="border-border/40">
                <TableCell
                  colSpan={7}
                  className="py-8 text-center text-sm text-muted-foreground"
                >
                  暂无消息
                </TableCell>
              </TableRow>
            ) : (
              items.map((msg) => (
                <TableRow
                  key={msg.id}
                  className="cursor-pointer border-border/40 hover:bg-muted/30 transition-colors"
                  onClick={() => navigate(`/messages/${msg.id}`)}
                >
                  <TableCell className="py-3 font-mono text-[10px] text-muted-foreground">
                    {msg.id}
                  </TableCell>
                  <TableCell className="py-3 text-sm">{msg.push_key_business_name}</TableCell>
                  <TableCell className="py-3 text-sm max-w-xs truncate">
                    {msg.title}
                  </TableCell>
                  <TableCell className="py-3">
                    <Badge variant="secondary" className="text-[10px] font-normal">
                      {typeLabels[msg.message_type] ?? msg.message_type}
                    </Badge>
                  </TableCell>
                  <TableCell className="py-3">
                    <Badge
                      variant={statusVariants[msg.status] ?? "outline"}
                      className={`text-[10px] font-normal ${statusClasses[msg.status] ?? ""}`}
                    >
                      {statusLabels[msg.status] ?? msg.status}
                    </Badge>
                  </TableCell>
                  <TableCell className="py-3">
                    <span className="text-sm text-muted-foreground">
                      {msg.success_count}/{msg.delivery_count}
                    </span>
                    {msg.failed_count > 0 && (
                      <span className="ml-1 text-sm text-red-400">
                        （失败 {msg.failed_count}）
                      </span>
                    )}
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

      {totalPages > 1 && (
        <div className="flex items-center justify-end gap-2">
          <Button
            variant="outline"
            size="sm"
            className="h-7 w-7 p-0"
            onClick={() => setPage((p) => Math.max(0, p - 1))}
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
            onClick={() =>
              setPage((p) => Math.min(totalPages - 1, p + 1))
            }
            disabled={page >= totalPages - 1}
          >
            <ChevronRight className="h-3.5 w-3.5" />
          </Button>
        </div>
      )}
    </div>
  )
}
