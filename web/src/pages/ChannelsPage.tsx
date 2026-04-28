import { useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { useSearchParams } from "react-router-dom"
import { useAuth } from "@/hooks/useAuth"
import { createChannel, deleteChannel, getChannels, getGroups, testChannel, updateChannel } from "@/lib/api"
import type { ChannelCreate, ChannelOut, ChannelType, ChannelUpdate } from "@/lib/api"
import { formatDate } from "@/lib/format"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Skeleton } from "@/components/ui/skeleton"
import { Switch } from "@/components/ui/switch"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import { toast } from "sonner"
import { Blocks, Check, ChevronLeft, ChevronRight, Copy, Pencil, Plus, TestTube, Trash2 } from "lucide-react"

const PAGE_SIZE = 10

const typeLabels: Record<ChannelType, string> = {
  wecom_bot: "企业微信机器人",
  dingtalk_bot: "钉钉机器人",
  feishu_bot: "飞书机器人",
  generic_webhook: "自定义 Webhook",
}

export function ChannelsPage() {
  const { isAdmin } = useAuth()
  const queryClient = useQueryClient()
  const [searchParams] = useSearchParams()
  const [page, setPage] = useState(0)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editingChannel, setEditingChannel] = useState<ChannelOut | null>(null)
  const [channelEnabled, setChannelEnabled] = useState(true)
  const [channelType, setChannelType] = useState<ChannelType>("wecom_bot")
  const [deleteId, setDeleteId] = useState<string | null>(null)
  const [testId, setTestId] = useState<string | null>(null)
  const [testResult, setTestResult] = useState<{
    success: boolean
    status_code: number | null
    response_body: string | null
    error: string | null
  } | null>(null)
  const [copiedId, setCopiedId] = useState<string | null>(null)
  const highlightedId = searchParams.get("highlight")

  const { data, isLoading } = useQuery({
    queryKey: ["channels", page],
    queryFn: () => getChannels(page * PAGE_SIZE, PAGE_SIZE),
  })

  const { data: groupsData } = useQuery({
    queryKey: ["groups", "all"],
    queryFn: () => getGroups(0, 200),
    enabled: isAdmin,
  })

  const createMutation = useMutation({
    mutationFn: createChannel,
    onSuccess: () => {
      toast.success("通道已创建")
      queryClient.invalidateQueries({ queryKey: ["channels"] })
      setDialogOpen(false)
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: ChannelUpdate }) => updateChannel(id, payload),
    onSuccess: () => {
      toast.success("通道已更新")
      queryClient.invalidateQueries({ queryKey: ["channels"] })
      setDialogOpen(false)
      setEditingChannel(null)
    },
  })

  const deleteMutation = useMutation({
    mutationFn: deleteChannel,
    onSuccess: () => {
      toast.success("通道已删除")
      queryClient.invalidateQueries({ queryKey: ["channels"] })
      queryClient.invalidateQueries({ queryKey: ["groups"] })
      setDeleteId(null)
    },
  })

  const testMutation = useMutation({
    mutationFn: (id: string) => testChannel(id, {}),
    onSuccess: (result) => {
      setTestResult(result)
    },
  })

  function openCreate() {
    setEditingChannel(null)
    setChannelEnabled(true)
    setChannelType("wecom_bot")
    setDialogOpen(true)
  }

  function openEdit(channel: ChannelOut) {
    setEditingChannel(channel)
    setChannelEnabled(channel.is_enabled)
    setChannelType(channel.type)
    setDialogOpen(true)
  }

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const formData = new FormData(event.currentTarget)
    const payload: ChannelCreate = {
      name: String(formData.get("name") || ""),
      type: channelType,
      webhook_url: String(formData.get("webhook_url") || ""),
      secret: String(formData.get("secret") || "") || undefined,
      is_enabled: channelEnabled,
      per_minute_limit: parseInt(String(formData.get("per_minute_limit") || "60"), 10) || 60,
    }

    if (editingChannel) {
      const updatePayload: ChannelUpdate = {
        name: payload.name,
        type: payload.type,
        webhook_url: payload.webhook_url,
        is_enabled: payload.is_enabled,
        per_minute_limit: payload.per_minute_limit,
      }
      if (payload.secret) {
        updatePayload.secret = payload.secret
      }
      updateMutation.mutate({ id: editingChannel.id, payload: updatePayload })
      return
    }

    createMutation.mutate(payload)
  }

  function openTest(id: string) {
    setTestId(id)
    setTestResult(null)
    testMutation.mutate(id)
  }

  const items = data?.items ?? []
  const total = data?.total ?? 0
  const totalPages = Math.ceil(total / PAGE_SIZE)
  const groupsById = new Map((groupsData?.items ?? []).map((group) => [group.id, group]))

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold tracking-tight">通道管理</h1>
          <p className="mt-0.5 text-sm text-muted-foreground">
            管理通知投递通道与用户组授权范围
          </p>
        </div>
        {isAdmin ? (
          <Button onClick={openCreate} size="sm" className="h-8 text-xs">
            <Plus className="mr-1.5 h-3.5 w-3.5" />
            新建通道
          </Button>
        ) : null}
      </div>

      <TooltipProvider>
        <div className="overflow-hidden rounded-lg border border-border/60">
          <Table>
          <TableHeader>
            <TableRow className="border-border/60 hover:bg-transparent">
              <TableHead className="h-9 text-xs font-medium text-muted-foreground">名称</TableHead>
              <TableHead className="h-9 text-xs font-medium text-muted-foreground">类型</TableHead>
              <TableHead className="h-9 text-xs font-medium text-muted-foreground">状态</TableHead>
              <TableHead className="h-9 text-xs font-medium text-muted-foreground">每分钟限流</TableHead>
              <TableHead className="h-9 text-xs font-medium text-muted-foreground">授权用户组</TableHead>
              <TableHead className="h-9 text-xs font-medium text-muted-foreground">创建时间</TableHead>
              <TableHead className="h-9 text-right text-xs font-medium text-muted-foreground">操作</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              Array.from({ length: 5 }).map((_, index) => (
                <TableRow key={index} className="border-border/40">
                  <TableCell colSpan={7} className="py-3">
                    <Skeleton className="h-5 w-full" />
                  </TableCell>
                </TableRow>
              ))
            ) : items.length === 0 ? (
              <TableRow className="border-border/40">
                <TableCell colSpan={7} className="py-8 text-center text-sm text-muted-foreground">
                  暂无通道
                </TableCell>
              </TableRow>
            ) : (
              items.map((channel) => {
                const groupLinks = channel.authorized_group_ids
                  .map((groupId) => groupsById.get(groupId))
                  .filter((group): group is NonNullable<typeof group> => Boolean(group))

                return (
                  <TableRow
                    key={channel.id}
                    className={
                      highlightedId === channel.id
                        ? "border-l-2 border-l-primary bg-primary/5"
                        : "border-border/40"
                    }
                  >
                    <TableCell className="py-3 text-sm font-medium">{channel.name}</TableCell>
                    <TableCell className="py-3">
                      <Badge variant="secondary" className="text-[10px] font-normal">
                        {typeLabels[channel.type]}
                      </Badge>
                    </TableCell>
                    <TableCell className="py-3">
                      {channel.is_enabled ? (
                        <Badge className="bg-emerald-500/15 text-[10px] font-normal text-emerald-400 hover:bg-emerald-500/20">
                          启用
                        </Badge>
                      ) : (
                        <Badge variant="outline" className="text-[10px] font-normal text-muted-foreground">
                          停用
                        </Badge>
                      )}
                    </TableCell>
                    <TableCell className="py-3 text-sm text-muted-foreground">
                      {channel.per_minute_limit}
                    </TableCell>
                    <TableCell className="py-3">
                      {groupLinks.length > 0 ? (
                        <Tooltip>
                          <TooltipTrigger>
                            <Badge variant="outline" className="gap-1 text-[10px] font-normal">
                              <Blocks className="h-3 w-3" />
                              {groupLinks.length} 个组
                            </Badge>
                          </TooltipTrigger>
                          <TooltipContent>{groupLinks.map((group) => group.name).join("、")}</TooltipContent>
                        </Tooltip>
                      ) : (
                        <span className="text-sm text-muted-foreground">-</span>
                      )}
                    </TableCell>
                    <TableCell className="py-3 text-sm text-muted-foreground">
                      {formatDate(channel.created_at)}
                    </TableCell>
                    <TableCell className="py-3 text-right">
                      <div className="flex justify-end gap-1">
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-7 w-7"
                          onClick={() => {
                            navigator.clipboard.writeText(channel.id)
                            setCopiedId(channel.id)
                            toast.success("渠道 ID 已复制")
                            setTimeout(() => setCopiedId(null), 1500)
                          }}
                          title="复制渠道 ID"
                        >
                          {copiedId === channel.id ? (
                            <Check className="h-3.5 w-3.5 text-emerald-500" />
                          ) : (
                            <Copy className="h-3.5 w-3.5" />
                          )}
                        </Button>
                        {isAdmin ? (
                          <>
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-7 w-7"
                              onClick={() => openTest(channel.id)}
                              title="测试通道"
                            >
                              <TestTube className="h-3.5 w-3.5" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-7 w-7"
                              onClick={() => openEdit(channel)}
                              title="编辑通道"
                            >
                              <Pencil className="h-3.5 w-3.5" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-7 w-7"
                              onClick={() => setDeleteId(channel.id)}
                              title="删除通道"
                            >
                              <Trash2 className="h-3.5 w-3.5" />
                            </Button>
                          </>
                        ) : null}
                      </div>
                    </TableCell>
                  </TableRow>
                )
              })
            )}
          </TableBody>
          </Table>
        </div>
      </TooltipProvider>

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

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-md border-border/60">
          <DialogHeader>
            <DialogTitle className="text-base">{editingChannel ? "编辑通道" : "新建通道"}</DialogTitle>
            <DialogDescription className="text-xs">
              {editingChannel ? "更新当前通道的配置项" : "创建一个新的通知投递通道"}
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="name" className="text-xs font-medium">名称</Label>
              <Input id="name" name="name" defaultValue={editingChannel?.name} required className="h-8 text-sm" />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="type" className="text-xs font-medium">类型</Label>
              <Select value={channelType} onValueChange={(value) => setChannelType(value as ChannelType)}>
                <SelectTrigger className="h-8 text-sm">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="wecom_bot">企业微信机器人</SelectItem>
                  <SelectItem value="dingtalk_bot">钉钉机器人</SelectItem>
                  <SelectItem value="feishu_bot">飞书机器人</SelectItem>
                  <SelectItem value="generic_webhook">自定义 Webhook</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="webhook_url" className="text-xs font-medium">Webhook 地址</Label>
              <Input
                id="webhook_url"
                name="webhook_url"
                defaultValue={editingChannel?.webhook_url}
                required
                className="h-8 text-sm"
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="secret" className="text-xs font-medium">密钥</Label>
              <Input id="secret" name="secret" defaultValue="" className="h-8 text-sm" />
              {editingChannel?.has_secret ? (
                <p className="text-[11px] text-muted-foreground">
                  当前已配置密钥：{editingChannel.secret_preview ?? "已隐藏"}；留空则保持不变
                </p>
              ) : null}
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="per_minute_limit" className="text-xs font-medium">每分钟限流</Label>
              <Input
                id="per_minute_limit"
                name="per_minute_limit"
                type="number"
                min={1}
                max={10000}
                defaultValue={editingChannel?.per_minute_limit ?? 60}
                required
                className="h-8 text-sm"
              />
            </div>
            <div className="rounded-lg border border-border/70 bg-muted/30 px-3 py-2.5">
              <p className="text-xs text-muted-foreground">
                通道访问权限已统一通过用户组维护。如需授权，请前往“用户组”页面为组绑定通道。
              </p>
            </div>
            <div className="flex items-center justify-between rounded-lg border border-border/70 bg-muted/30 px-3 py-2.5">
              <div className="space-y-0.5">
                <Label htmlFor="is_enabled" className="cursor-pointer text-sm font-medium">
                  启用通道
                </Label>
                <p className="text-xs text-muted-foreground">关闭后该通道不会再接收新的推送请求。</p>
              </div>
              <Switch id="is_enabled" checked={channelEnabled} onCheckedChange={setChannelEnabled} />
            </div>
            <DialogFooter>
              <Button
                type="submit"
                size="sm"
                disabled={createMutation.isPending || updateMutation.isPending}
              >
                {createMutation.isPending || updateMutation.isPending ? "保存中..." : "保存"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      <AlertDialog open={Boolean(deleteId)} onOpenChange={() => setDeleteId(null)}>
        <AlertDialogContent className="border-border/60">
          <AlertDialogHeader>
            <AlertDialogTitle className="text-base">确认删除通道？</AlertDialogTitle>
            <AlertDialogDescription className="text-xs">
              删除后无法撤销，该通道会被标记为已删除。
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel className="h-8 text-xs">取消</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => deleteId && deleteMutation.mutate(deleteId)}
              className="h-8 text-xs bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              删除
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <Dialog open={Boolean(testId)} onOpenChange={() => setTestId(null)}>
        <DialogContent className="border-border/60">
          <DialogHeader>
            <DialogTitle className="text-base">通道测试结果</DialogTitle>
          </DialogHeader>
          {testMutation.isPending ? (
            <Skeleton className="h-20 w-full" />
          ) : testResult ? (
            <div className="space-y-2 text-sm">
              <div className="flex items-center gap-2">
                <span className="text-xs text-muted-foreground">是否成功：</span>
                <Badge
                  variant={testResult.success ? "default" : "destructive"}
                  className="text-[10px] font-normal"
                >
                  {testResult.success ? "是" : "否"}
                </Badge>
              </div>
              {testResult.status_code !== null ? (
                <div>
                  <span className="text-xs text-muted-foreground">状态码：</span> {testResult.status_code}
                </div>
              ) : null}
              {testResult.error ? (
                <div className="text-xs text-destructive">
                  <span className="font-medium">错误：</span> {testResult.error}
                </div>
              ) : null}
              {testResult.response_body ? (
                <div>
                  <span className="text-xs text-muted-foreground">响应内容：</span>
                  <pre className="mt-1 max-h-40 overflow-auto rounded-md bg-muted p-2 text-[10px]">
                    {testResult.response_body}
                  </pre>
                </div>
              ) : null}
            </div>
          ) : null}
        </DialogContent>
      </Dialog>
    </div>
  )
}
