import { useParams, useNavigate } from "react-router-dom"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { getMessage, replayMessage, retryDelivery } from "@/lib/api"
import { formatDateTime } from "@/lib/format"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { ArrowLeft, RotateCcw } from "lucide-react"
import { toast } from "sonner"

const statusVariants: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
  pending: "secondary",
  queued: "secondary",
  sending: "secondary",
  success: "default",
  failed: "destructive",
  retrying: "outline",
  dead_letter: "destructive",
}

const statusClasses: Record<string, string> = {
  pending: "bg-amber-500/10 text-amber-400 hover:bg-amber-500/15",
  queued: "bg-amber-500/10 text-amber-400 hover:bg-amber-500/15",
  sending: "bg-blue-500/10 text-blue-400 hover:bg-blue-500/15",
  success: "bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/15",
  failed: "bg-red-500/10 text-red-400 hover:bg-red-500/15",
  retrying: "bg-orange-500/10 text-orange-400 hover:bg-orange-500/15",
  dead_letter: "bg-red-500/15 text-red-300 hover:bg-red-500/20",
}

const statusLabels: Record<string, string> = {
  pending: "待处理",
  queued: "排队中",
  sending: "发送中",
  success: "成功",
  failed: "失败",
  retrying: "重试中",
  dead_letter: "死信",
}

const messageTypeLabels: Record<string, string> = {
  text: "文本",
  markdown: "Markdown",
}

export function MessageDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const { data, isLoading } = useQuery({
    queryKey: ["message", id],
    queryFn: () => getMessage(id!),
    enabled: !!id,
  })

  const replayMutation = useMutation({
    mutationFn: replayMessage,
    onSuccess: (result) => {
      toast.success(`已重放消息：${result.message_id}`)
    },
  })

  const retryMutation = useMutation({
    mutationFn: ({ messageId, deliveryId }: { messageId: string; deliveryId: string }) =>
      retryDelivery(messageId, deliveryId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["message", id] })
      await queryClient.invalidateQueries({ queryKey: ["messages"] })
      toast.success("失败投递已重新入队")
    },
  })

  if (isLoading) {
    return (
      <div className="space-y-5">
        <Skeleton className="h-7 w-48" />
        <Skeleton className="h-40 w-full" />
        <Skeleton className="h-40 w-full" />
      </div>
    )
  }

  if (!data) {
    return (
      <div className="text-center text-sm text-muted-foreground py-12">
        未找到该消息
      </div>
    )
  }

  return (
    <div className="space-y-5">
      <div className="flex items-center gap-3">
        <Button variant="outline" size="icon" className="h-8 w-8" onClick={() => navigate("/messages")}>
          <ArrowLeft className="h-3.5 w-3.5" />
        </Button>
        <div>
          <h1 className="text-lg font-semibold tracking-tight">消息详情</h1>
          <p className="text-[10px] text-muted-foreground font-mono">{data.id}</p>
        </div>
        <Button
          variant="outline"
          size="sm"
          className="ml-auto h-8 text-xs"
          onClick={() => replayMutation.mutate(data.id)}
          disabled={replayMutation.isPending}
        >
          <RotateCcw className="mr-1.5 h-3.5 w-3.5" />
          {replayMutation.isPending ? "重放中..." : "重放消息"}
        </Button>
      </div>

      <Card className="border-border/60 shadow-none">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-medium">基本信息</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4 md:grid-cols-2">
          <div>
            <span className="text-xs text-muted-foreground">标题</span>
            <p className="text-sm font-medium mt-0.5">{data.title}</p>
          </div>
          <div>
            <span className="text-xs text-muted-foreground">业务</span>
            <p className="text-sm font-medium mt-0.5">{data.push_key_business_name}</p>
          </div>
          <div>
            <span className="text-xs text-muted-foreground">来源</span>
            <p className="text-sm font-medium mt-0.5">{data.source}</p>
          </div>
          <div>
            <span className="text-xs text-muted-foreground">类型</span>
            <div className="mt-0.5">
              <Badge variant="secondary" className="text-[10px] font-normal">{messageTypeLabels[data.message_type] ?? data.message_type}</Badge>
            </div>
          </div>
          <div>
            <span className="text-xs text-muted-foreground">状态</span>
            <div className="mt-0.5">
              <Badge
                variant={statusVariants[data.status] ?? "outline"}
                className={`text-[10px] font-normal ${statusClasses[data.status] ?? ""}`}
              >
                {statusLabels[data.status] ?? data.status}
              </Badge>
            </div>
          </div>
          <div>
            <span className="text-xs text-muted-foreground">创建时间</span>
            <p className="text-sm font-medium mt-0.5">{formatDateTime(data.created_at)}</p>
          </div>
          <div className="md:col-span-2">
            <span className="text-xs text-muted-foreground">消息内容</span>
            <pre className="mt-1.5 max-h-60 overflow-auto rounded-md bg-muted p-3 text-xs whitespace-pre-wrap text-muted-foreground">
              {data.content}
            </pre>
          </div>
          <div className="md:col-span-2">
            <span className="text-xs text-muted-foreground">请求载荷</span>
            <pre className="mt-1.5 max-h-60 overflow-auto rounded-md bg-muted p-3 text-[10px] text-muted-foreground">
              {JSON.stringify(data.request_payload, null, 2)}
            </pre>
          </div>
        </CardContent>
      </Card>

      <Card className="border-border/60 shadow-none">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-medium">投递明细</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="rounded-lg border border-border/60 overflow-hidden">
            <Table>
              <TableHeader>
                <TableRow className="border-border/60 hover:bg-transparent">
                  <TableHead className="text-xs font-medium text-muted-foreground h-9">通道</TableHead>
                  <TableHead className="text-xs font-medium text-muted-foreground h-9">状态</TableHead>
                  <TableHead className="text-xs font-medium text-muted-foreground h-9">尝试次数</TableHead>
                  <TableHead className="text-xs font-medium text-muted-foreground h-9">下次重试</TableHead>
                  <TableHead className="text-xs font-medium text-muted-foreground h-9">送达时间</TableHead>
                  <TableHead className="text-xs font-medium text-muted-foreground h-9">错误信息</TableHead>
                  <TableHead className="text-xs font-medium text-muted-foreground h-9 text-right">操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.deliveries.length === 0 ? (
                  <TableRow className="border-border/40">
                    <TableCell colSpan={7} className="py-8 text-center text-sm text-muted-foreground">
                      暂无投递记录
                    </TableCell>
                  </TableRow>
                ) : (
                  data.deliveries.map((delivery) => (
                    <TableRow key={delivery.id} className="border-border/40">
                      <TableCell className="py-3">
                        <div>
                          <p className="text-sm font-medium">{delivery.channel_name}</p>
                          <p className="text-[10px] text-muted-foreground">{delivery.channel_type}</p>
                        </div>
                      </TableCell>
                      <TableCell className="py-3">
                        <Badge
                          variant={statusVariants[delivery.status] ?? "outline"}
                          className={`text-[10px] font-normal ${statusClasses[delivery.status] ?? ""}`}
                        >
                          {statusLabels[delivery.status] ?? delivery.status}
                        </Badge>
                      </TableCell>
                      <TableCell className="py-3 text-sm text-muted-foreground">{delivery.attempt_count}</TableCell>
                      <TableCell className="py-3 text-sm text-muted-foreground">
                        {formatDateTime(delivery.next_retry_at)}
                      </TableCell>
                      <TableCell className="py-3 text-sm text-muted-foreground">
                        {formatDateTime(delivery.delivered_at)}
                      </TableCell>
                      <TableCell className="py-3">
                        {delivery.final_error ? (
                          <span className="text-xs text-red-400">{delivery.final_error}</span>
                        ) : (
                          <span className="text-sm text-muted-foreground">-</span>
                        )}
                      </TableCell>
                      <TableCell className="py-3 text-right">
                        {delivery.status === "failed" || delivery.status === "dead_letter" ? (
                          <Button
                            variant="outline"
                            size="sm"
                            className="h-7 text-xs"
                            onClick={() =>
                              retryMutation.mutate({
                                messageId: data.id,
                                deliveryId: delivery.id,
                              })
                            }
                            disabled={retryMutation.isPending}
                          >
                            重试投递
                          </Button>
                        ) : (
                          <span className="text-sm text-muted-foreground">-</span>
                        )}
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>

          {data.deliveries.map((delivery) => (
            <div key={delivery.id} className="rounded-lg border border-border/60 bg-muted/10 p-4">
              <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium">{delivery.channel_name}</span>
                    <Badge
                      variant={statusVariants[delivery.status] ?? "outline"}
                      className={`text-[10px] font-normal ${statusClasses[delivery.status] ?? ""}`}
                    >
                      {statusLabels[delivery.status] ?? delivery.status}
                    </Badge>
                  </div>
                  <p className="mt-1 text-xs text-muted-foreground">{delivery.channel_type}</p>
                </div>
                <div className="grid gap-2 text-xs text-muted-foreground md:grid-cols-3">
                  <span>开始处理：{formatDateTime(delivery.processing_started_at)}</span>
                  <span>进入死信：{formatDateTime(delivery.dead_lettered_at)}</span>
                  <span>HTTP 状态：{delivery.last_response_status ?? "-"}</span>
                </div>
              </div>

              <div className="mt-4 grid gap-4 xl:grid-cols-2">
                <div className="space-y-2">
                  <p className="text-xs font-medium">适配器载荷</p>
                  <ScrollArea className="h-48 rounded-md border border-border/60 bg-background p-3">
                    <pre className="text-[10px] text-muted-foreground">
                      {JSON.stringify(delivery.adapter_payload, null, 2)}
                    </pre>
                  </ScrollArea>
                </div>
                <div className="space-y-2">
                  <p className="text-xs font-medium">响应与错误</p>
                  <ScrollArea className="h-48 rounded-md border border-border/60 bg-background p-3">
                    <pre className="whitespace-pre-wrap break-all text-[10px] text-muted-foreground">
                      {delivery.last_response_body || delivery.final_error || "暂无响应内容"}
                    </pre>
                  </ScrollArea>
                </div>
              </div>

              <div className="mt-4 space-y-2">
                <p className="text-xs font-medium">尝试日志</p>
                {delivery.attempt_logs.length > 0 ? (
                  <div className="rounded-lg border border-border/60 overflow-hidden">
                    <Table>
                      <TableHeader>
                        <TableRow className="border-border/60 hover:bg-transparent">
                          <TableHead className="h-8 text-[11px] text-muted-foreground">时间</TableHead>
                          <TableHead className="h-8 text-[11px] text-muted-foreground">状态码</TableHead>
                          <TableHead className="h-8 text-[11px] text-muted-foreground">错误</TableHead>
                          <TableHead className="h-8 text-[11px] text-muted-foreground">重试延迟</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {delivery.attempt_logs.map((log, index) => (
                          <TableRow key={`${delivery.id}-${index}`} className="border-border/40">
                            <TableCell className="py-2 text-xs text-muted-foreground">
                              {formatDateTime(log.at)}
                            </TableCell>
                            <TableCell className="py-2 text-xs text-muted-foreground">
                              {log.status_code ?? "-"}
                            </TableCell>
                            <TableCell className="py-2 text-xs text-muted-foreground">
                              {log.error || "-"}
                            </TableCell>
                            <TableCell className="py-2 text-xs text-muted-foreground">
                              {log.retry_scheduled_in_seconds
                                ? `${log.retry_scheduled_in_seconds}s`
                                : "-"}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>
                ) : (
                  <div className="rounded-md border border-dashed border-border/60 px-3 py-4 text-xs text-muted-foreground">
                    暂无尝试日志
                  </div>
                )}
              </div>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  )
}
