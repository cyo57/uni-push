import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useAuth } from "@/hooks/useAuth"
import {
  getChannels,
  createChannel,
  updateChannel,
  deleteChannel,
  testChannel,
  grantChannelPermission,
  revokeChannelPermission,
  getUsers,
} from "@/lib/api"
import type { ChannelCreate, ChannelUpdate, ChannelOut, ChannelType } from "@/lib/api"
import { formatDate } from "@/lib/format"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
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
import { toast } from "sonner"
import {
  Plus,
  Pencil,
  Trash2,
  TestTube,
  Users,
  ChevronLeft,
  ChevronRight,
  Copy,
  Check,
} from "lucide-react"

const PAGE_SIZE = 10

const typeLabels: Record<ChannelType, string> = {
  wecom_bot: "企业微信机器人",
  dingtalk_bot: "钉钉机器人",
}

const roleLabels = {
  admin: "管理员",
  user: "普通用户",
} as const

export function ChannelsPage() {
  const { isAdmin } = useAuth()
  const queryClient = useQueryClient()
  const [page, setPage] = useState(0)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editingChannel, setEditingChannel] = useState<ChannelOut | null>(null)
  const [channelEnabled, setChannelEnabled] = useState(true)
  const [deleteId, setDeleteId] = useState<string | null>(null)
  const [testId, setTestId] = useState<string | null>(null)
  const [testResult, setTestResult] = useState<{
    success: boolean
    status_code: number | null
    response_body: string | null
    error: string | null
  } | null>(null)
  const [permDialogOpen, setPermDialogOpen] = useState(false)
  const [permChannel, setPermChannel] = useState<ChannelOut | null>(null)
  const [permissionUserIds, setPermissionUserIds] = useState<string[]>([])
  const [copiedId, setCopiedId] = useState<string | null>(null)

  const { data, isLoading } = useQuery({
    queryKey: ["channels", page],
    queryFn: () => getChannels(page * PAGE_SIZE, PAGE_SIZE),
  })

  const { data: usersData } = useQuery({
    queryKey: ["users"],
    queryFn: () => getUsers(0, 200),
    enabled: permDialogOpen && isAdmin,
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
    mutationFn: ({ id, payload }: { id: string; payload: ChannelUpdate }) =>
      updateChannel(id, payload),
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
      setDeleteId(null)
    },
  })

  const testMutation = useMutation({
    mutationFn: (id: string) => testChannel(id, {}),
    onSuccess: (data) => {
      setTestResult(data)
    },
  })

  const grantMutation = useMutation({
    mutationFn: ({ channelId, userId }: { channelId: string; userId: string }) =>
      grantChannelPermission(channelId, userId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["channels"] })
    },
  })

  const revokeMutation = useMutation({
    mutationFn: ({ channelId, userId }: { channelId: string; userId: string }) =>
      revokeChannelPermission(channelId, userId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["channels"] })
    },
  })

  function openCreate() {
    setEditingChannel(null)
    setChannelEnabled(true)
    setDialogOpen(true)
  }

  function openEdit(channel: ChannelOut) {
    setEditingChannel(channel)
    setChannelEnabled(channel.is_enabled)
    setDialogOpen(true)
  }

  function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault()
    const form = e.currentTarget
    const fd = new FormData(form)
    const payload: ChannelCreate = {
      name: fd.get("name") as string,
      type: fd.get("type") as ChannelType,
      webhook_url: fd.get("webhook_url") as string,
      secret: (fd.get("secret") as string) || undefined,
      is_enabled: channelEnabled,
      per_minute_limit: parseInt(fd.get("per_minute_limit") as string) || 60,
    }
    if (editingChannel) {
      const updatePayload: ChannelUpdate = {}
      if (payload.name !== editingChannel.name) updatePayload.name = payload.name
      if (payload.type !== editingChannel.type) updatePayload.type = payload.type
      if (payload.webhook_url !== editingChannel.webhook_url) updatePayload.webhook_url = payload.webhook_url
      if (payload.secret !== (editingChannel.secret || undefined)) updatePayload.secret = payload.secret
      if (payload.is_enabled !== editingChannel.is_enabled) updatePayload.is_enabled = payload.is_enabled
      if (payload.per_minute_limit !== editingChannel.per_minute_limit) updatePayload.per_minute_limit = payload.per_minute_limit
      updateMutation.mutate({ id: editingChannel.id, payload: updatePayload })
    } else {
      createMutation.mutate(payload)
    }
  }

  function openTest(id: string) {
    setTestId(id)
    setTestResult(null)
    testMutation.mutate(id)
  }

  function openPerm(channel: ChannelOut) {
    setPermChannel(channel)
    setPermissionUserIds(channel.authorized_user_ids)
    setPermDialogOpen(true)
  }

  function handlePermissionChange(userId: string, checked: boolean) {
    if (!permChannel) return

    const previous = permissionUserIds
    const next = checked
      ? Array.from(new Set([...permissionUserIds, userId]))
      : permissionUserIds.filter((id) => id !== userId)

    setPermissionUserIds(next)
    setPermChannel({
      ...permChannel,
      authorized_user_ids: next,
    })

    const rollback = () => {
      setPermissionUserIds(previous)
      setPermChannel({
        ...permChannel,
        authorized_user_ids: previous,
      })
    }

    if (checked) {
      grantMutation.mutate(
        {
          channelId: permChannel.id,
          userId,
        },
        { onError: rollback }
      )
    } else {
      revokeMutation.mutate(
        {
          channelId: permChannel.id,
          userId,
        },
        { onError: rollback }
      )
    }
  }

  const items = data?.items ?? []
  const total = data?.total ?? 0
  const totalPages = Math.ceil(total / PAGE_SIZE)

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold tracking-tight">通道管理</h1>
          <p className="text-sm text-muted-foreground mt-0.5">管理通知投递通道与访问权限</p>
        </div>
        {isAdmin && (
          <Button onClick={openCreate} size="sm" className="h-8 text-xs">
            <Plus className="mr-1.5 h-3.5 w-3.5" />
            新建通道
          </Button>
        )}
      </div>

      <div className="rounded-lg border border-border/60 overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow className="border-border/60 hover:bg-transparent">
              <TableHead className="text-xs font-medium text-muted-foreground h-9">名称</TableHead>
              <TableHead className="text-xs font-medium text-muted-foreground h-9">类型</TableHead>
              <TableHead className="text-xs font-medium text-muted-foreground h-9">状态</TableHead>
              <TableHead className="text-xs font-medium text-muted-foreground h-9">每分钟限流</TableHead>
              <TableHead className="text-xs font-medium text-muted-foreground h-9">创建时间</TableHead>
              <TableHead className="text-xs font-medium text-muted-foreground h-9 text-right">操作</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              Array.from({ length: 5 }).map((_, i) => (
                <TableRow key={i} className="border-border/40">
                  <TableCell colSpan={6} className="py-3">
                    <Skeleton className="h-5 w-full" />
                  </TableCell>
                </TableRow>
              ))
            ) : items.length === 0 ? (
              <TableRow className="border-border/40">
                <TableCell colSpan={6} className="py-8 text-center text-sm text-muted-foreground">
                  暂无通道
                </TableCell>
              </TableRow>
            ) : (
              items.map((channel) => (
                <TableRow key={channel.id} className="border-border/40">
                  <TableCell className="py-3 text-sm font-medium">{channel.name}</TableCell>
                  <TableCell className="py-3">
                    <Badge variant="secondary" className="text-[10px] font-normal">
                      {typeLabels[channel.type]}
                    </Badge>
                  </TableCell>
                  <TableCell className="py-3">
                    {channel.is_enabled ? (
                      <Badge variant="default" className="text-[10px] font-normal bg-emerald-500/15 text-emerald-400 hover:bg-emerald-500/20">
                        启用
                      </Badge>
                    ) : (
                      <Badge variant="outline" className="text-[10px] font-normal text-muted-foreground">
                        停用
                      </Badge>
                    )}
                  </TableCell>
                  <TableCell className="py-3 text-sm text-muted-foreground">{channel.per_minute_limit}</TableCell>
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
                      {isAdmin && (
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
                            onClick={() => openPerm(channel)}
                            title="权限管理"
                          >
                            <Users className="h-3.5 w-3.5" />
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
                      )}
                    </div>
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
            onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
            disabled={page >= totalPages - 1}
          >
            <ChevronRight className="h-3.5 w-3.5" />
          </Button>
        </div>
      )}

      {/* Create / Edit Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-md border-border/60">
          <DialogHeader>
            <DialogTitle className="text-base">
              {editingChannel ? "编辑通道" : "新建通道"}
            </DialogTitle>
            <DialogDescription className="text-xs">
              {editingChannel
                ? "更新当前通道的配置项"
                : "创建一个新的通知投递通道"}
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="name" className="text-xs font-medium">名称</Label>
              <Input
                id="name"
                name="name"
                defaultValue={editingChannel?.name}
                required
                className="h-8 text-sm"
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="type" className="text-xs font-medium">类型</Label>
              <Select
                name="type"
                defaultValue={editingChannel?.type ?? "wecom_bot"}
              >
                <SelectTrigger className="h-8 text-sm">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="wecom_bot">企业微信机器人</SelectItem>
                  <SelectItem value="dingtalk_bot">钉钉机器人</SelectItem>
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
              <Input
                id="secret"
                name="secret"
                defaultValue={editingChannel?.secret ?? ""}
                className="h-8 text-sm"
              />
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
            <div className="flex items-center justify-between rounded-lg border border-border/70 bg-muted/30 px-3 py-2.5">
              <div className="space-y-0.5">
                <Label htmlFor="is_enabled" className="cursor-pointer text-sm font-medium">
                  启用通道
                </Label>
                <p className="text-xs text-muted-foreground">
                  关闭后该通道不会再接收新的推送请求。
                </p>
              </div>
              <Switch
                id="is_enabled"
                checked={channelEnabled}
                onCheckedChange={setChannelEnabled}
              />
            </div>
            <DialogFooter>
              <Button
                type="submit"
                size="sm"
                disabled={createMutation.isPending || updateMutation.isPending}
              >
                {createMutation.isPending || updateMutation.isPending
                  ? "保存中..."
                  : "保存"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Delete Confirm */}
      <AlertDialog open={!!deleteId} onOpenChange={() => setDeleteId(null)}>
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

      {/* Test Result Dialog */}
      <Dialog open={!!testId} onOpenChange={() => setTestId(null)}>
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
              {testResult.status_code !== null && (
                <div>
                  <span className="text-xs text-muted-foreground">状态码：</span>{" "}
                  {testResult.status_code}
                </div>
              )}
              {testResult.error && (
                <div className="text-destructive text-xs">
                  <span className="font-medium">错误：</span> {testResult.error}
                </div>
              )}
              {testResult.response_body && (
                <div>
                  <span className="text-xs text-muted-foreground">响应内容：</span>
                  <pre className="mt-1 max-h-40 overflow-auto rounded-md bg-muted p-2 text-[10px]">
                    {testResult.response_body}
                  </pre>
                </div>
              )}
            </div>
          ) : null}
        </DialogContent>
      </Dialog>

      {/* Permissions Dialog */}
      <Dialog open={permDialogOpen} onOpenChange={setPermDialogOpen}>
        <DialogContent className="border-border/60">
          <DialogHeader>
            <DialogTitle className="text-base">通道权限</DialogTitle>
            <DialogDescription className="text-xs">
              为“{permChannel?.name}”配置可访问的用户
            </DialogDescription>
          </DialogHeader>
          <div className="max-h-80 overflow-auto space-y-1">
            {usersData?.items.map((user) => {
              const granted = permissionUserIds.includes(user.id)
              return (
                <div
                  key={user.id}
                  className="flex items-center justify-between rounded-md px-2 py-2 hover:bg-muted/50"
                >
                  <div>
                    <p className="text-sm font-medium">{user.display_name}</p>
                    <p className="text-[10px] text-muted-foreground">
                      @{user.username}（{roleLabels[user.role]}）
                    </p>
                  </div>
                  <Switch
                    checked={granted}
                    onCheckedChange={(checked) => handlePermissionChange(user.id, checked)}
                  />
                </div>
              )
            })}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}
