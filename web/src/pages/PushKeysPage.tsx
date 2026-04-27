import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import {
  getPushKeys,
  createPushKey,
  updatePushKey,
  rotatePushKey,
  getChannels,
} from "@/lib/api"
import type { PushKeyCreate, PushKeyUpdate, PushKeyOut } from "@/lib/api"
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
import { Checkbox } from "@/components/ui/checkbox"
import { toast } from "sonner"
import {
  Plus,
  Pencil,
  RefreshCw,
  ChevronLeft,
  ChevronRight,
  Copy,
} from "lucide-react"

const PAGE_SIZE = 10

export function PushKeysPage() {
  const queryClient = useQueryClient()
  const [page, setPage] = useState(0)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editingKey, setEditingKey] = useState<PushKeyOut | null>(null)
  const [rotateId, setRotateId] = useState<string | null>(null)
  const [newKeyValue, setNewKeyValue] = useState<string | null>(null)
  const [selectedChannels, setSelectedChannels] = useState<string[]>([])
  const [defaultChannel, setDefaultChannel] = useState<string>("")
  const [keyActive, setKeyActive] = useState(true)

  const { data, isLoading } = useQuery({
    queryKey: ["push-keys", page],
    queryFn: () => getPushKeys(page * PAGE_SIZE, PAGE_SIZE),
  })

  const { data: channelsData } = useQuery({
    queryKey: ["channels"],
    queryFn: () => getChannels(0, 200),
  })

  const createMutation = useMutation({
    mutationFn: createPushKey,
    onSuccess: (data) => {
      toast.success("推送密钥已创建")
      queryClient.invalidateQueries({ queryKey: ["push-keys"] })
      setNewKeyValue(data.plaintext_key)
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: PushKeyUpdate }) =>
      updatePushKey(id, payload),
    onSuccess: () => {
      toast.success("推送密钥已更新")
      queryClient.invalidateQueries({ queryKey: ["push-keys"] })
      setDialogOpen(false)
      setEditingKey(null)
      setSelectedChannels([])
    },
  })

  const rotateMutation = useMutation({
    mutationFn: rotatePushKey,
    onSuccess: (data) => {
      toast.success("推送密钥已轮换")
      queryClient.invalidateQueries({ queryKey: ["push-keys"] })
      setRotateId(null)
      setNewKeyValue(data.plaintext_key)
    },
  })

  function openCreate() {
    setEditingKey(null)
    setSelectedChannels([])
    setDefaultChannel("")
    setKeyActive(true)
    setNewKeyValue(null)
    setDialogOpen(true)
  }

  function openEdit(key: PushKeyOut) {
    setEditingKey(key)
    setSelectedChannels(key.channels.map((c) => c.id))
    setDefaultChannel(key.default_channel_id)
    setKeyActive(key.is_active)
    setNewKeyValue(null)
    setDialogOpen(true)
  }

  function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault()
    const form = e.currentTarget
    const fd = new FormData(form)
    const businessName = fd.get("business_name") as string
    const perMinuteLimit = parseInt(fd.get("per_minute_limit") as string) || 60

    if (!defaultChannel) {
      toast.error("请选择默认通道")
      return
    }
    if (selectedChannels.length === 0) {
      toast.error("请至少选择一个通道")
      return
    }

    if (editingKey) {
      const payload: PushKeyUpdate = {
        business_name: businessName,
        per_minute_limit: perMinuteLimit,
        channel_ids: selectedChannels,
        default_channel_id: defaultChannel,
        is_active: keyActive,
      }
      updateMutation.mutate({ id: editingKey.id, payload })
    } else {
      const payload: PushKeyCreate = {
        business_name: businessName,
        per_minute_limit: perMinuteLimit,
        channel_ids: selectedChannels,
        default_channel_id: defaultChannel,
      }
      createMutation.mutate(payload)
    }
  }

  const items = data?.items ?? []
  const total = data?.total ?? 0
  const totalPages = Math.ceil(total / PAGE_SIZE)

  const allChannels = channelsData?.items ?? []

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold tracking-tight">推送密钥</h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            管理业务侧调用推送接口使用的密钥
          </p>
        </div>
        <Button onClick={openCreate} size="sm" className="h-8 text-xs">
          <Plus className="mr-1.5 h-3.5 w-3.5" />
          新建密钥
        </Button>
      </div>

      <div className="rounded-lg border border-border/60 overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow className="border-border/60 hover:bg-transparent">
              <TableHead className="text-xs font-medium text-muted-foreground h-9">业务名称</TableHead>
              <TableHead className="text-xs font-medium text-muted-foreground h-9">密钥摘要</TableHead>
              <TableHead className="text-xs font-medium text-muted-foreground h-9">状态</TableHead>
              <TableHead className="text-xs font-medium text-muted-foreground h-9">默认通道</TableHead>
              <TableHead className="text-xs font-medium text-muted-foreground h-9">关联通道数</TableHead>
              <TableHead className="text-xs font-medium text-muted-foreground h-9">创建时间</TableHead>
              <TableHead className="text-xs font-medium text-muted-foreground h-9 text-right">操作</TableHead>
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
                  暂无推送密钥
                </TableCell>
              </TableRow>
            ) : (
              items.map((key) => (
                <TableRow key={key.id} className="border-border/40">
                  <TableCell className="py-3 text-sm font-medium">
                    {key.business_name}
                  </TableCell>
                  <TableCell className="py-3">
                    <code className="rounded bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground">
                      {key.key_hint}
                    </code>
                  </TableCell>
                  <TableCell className="py-3">
                    {key.is_active ? (
                      <Badge variant="default" className="text-[10px] font-normal bg-emerald-500/15 text-emerald-400 hover:bg-emerald-500/20">
                        启用
                      </Badge>
                    ) : (
                      <Badge variant="outline" className="text-[10px] font-normal text-muted-foreground">
                        停用
                      </Badge>
                    )}
                  </TableCell>
                  <TableCell className="py-3 text-sm text-muted-foreground">
                    {key.channels.find((c) => c.id === key.default_channel_id)
                      ?.name ?? key.default_channel_id}
                  </TableCell>
                  <TableCell className="py-3 text-sm text-muted-foreground">{key.channels.length}</TableCell>
                  <TableCell className="py-3 text-sm text-muted-foreground">
                    {formatDate(key.created_at)}
                  </TableCell>
                  <TableCell className="py-3 text-right">
                    <div className="flex justify-end gap-1">
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-7 w-7"
                        onClick={() => setRotateId(key.id)}
                        title="轮换密钥"
                      >
                        <RefreshCw className="h-3.5 w-3.5" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-7 w-7"
                        onClick={() => openEdit(key)}
                        title="编辑密钥"
                      >
                        <Pencil className="h-3.5 w-3.5" />
                      </Button>
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
            onClick={() =>
              setPage((p) => Math.min(totalPages - 1, p + 1))
            }
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
              {editingKey ? "编辑推送密钥" : "新建推送密钥"}
            </DialogTitle>
            <DialogDescription className="text-xs">
              {editingKey
                ? "更新推送密钥与通道绑定配置"
                : "为你的业务创建一个新的推送密钥"}
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="business_name" className="text-xs font-medium">业务名称</Label>
              <Input
                id="business_name"
                name="business_name"
                defaultValue={editingKey?.business_name}
                required
                className="h-8 text-sm"
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="per_minute_limit" className="text-xs font-medium">
                每分钟限流
              </Label>
              <Input
                id="per_minute_limit"
                name="per_minute_limit"
                type="number"
                min={1}
                max={10000}
                defaultValue={editingKey?.per_minute_limit ?? 60}
                required
                className="h-8 text-sm"
              />
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs font-medium">可用通道</Label>
              <div className="space-y-2 rounded-md border border-border/60 p-3">
                {allChannels.length === 0 ? (
                  <p className="text-sm text-muted-foreground">
                    暂无可用通道
                  </p>
                ) : (
                  allChannels.map((channel) => (
                    <div
                      key={channel.id}
                      className="flex items-center gap-2"
                    >
                      <Checkbox
                        id={`ch-${channel.id}`}
                        checked={selectedChannels.includes(channel.id)}
                        onCheckedChange={(checked) => {
                          setSelectedChannels((prev) =>
                            checked
                              ? [...prev, channel.id]
                              : prev.filter((id) => id !== channel.id)
                          )
                        }}
                      />
                      <Label
                        htmlFor={`ch-${channel.id}`}
                        className="text-sm font-normal"
                      >
                        {channel.name}
                      </Label>
                    </div>
                  ))
                )}
              </div>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="default_channel" className="text-xs font-medium">默认通道</Label>
              <Select
                value={defaultChannel}
                onValueChange={(v) => setDefaultChannel(v ?? "")}
              >
                <SelectTrigger className="h-8 text-sm">
                  <SelectValue placeholder="请选择默认通道" />
                </SelectTrigger>
                <SelectContent>
                  {allChannels.map((channel) => (
                    <SelectItem key={channel.id} value={channel.id}>
                      {channel.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            {editingKey && (
              <div className="flex items-center gap-2">
                <Switch
                  id="is_active"
                  checked={keyActive}
                  onCheckedChange={setKeyActive}
                />
                <Label htmlFor="is_active" className="text-xs font-medium">启用密钥</Label>
              </div>
            )}
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

      {/* Rotate Confirm */}
      <AlertDialog
        open={!!rotateId}
        onOpenChange={() => setRotateId(null)}
      >
        <AlertDialogContent className="border-border/60">
          <AlertDialogHeader>
            <AlertDialogTitle className="text-base">确认轮换密钥？</AlertDialogTitle>
            <AlertDialogDescription className="text-xs">
              旧密钥会立即失效，系统将生成一个新的密钥。
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel className="h-8 text-xs">取消</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => rotateId && rotateMutation.mutate(rotateId)}
              className="h-8 text-xs"
            >
              立即轮换
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* New Key Display */}
      <Dialog
        open={!!newKeyValue}
        onOpenChange={() => setNewKeyValue(null)}
      >
        <DialogContent className="border-border/60">
          <DialogHeader>
            <DialogTitle className="text-base">新密钥已生成</DialogTitle>
            <DialogDescription className="text-xs">
              请立即复制保存，该密钥只会展示这一次。
            </DialogDescription>
          </DialogHeader>
          <div className="flex items-center gap-2">
            <code className="flex-1 rounded-md bg-muted p-3 text-[10px] break-all text-muted-foreground">
              {newKeyValue}
            </code>
            <Button
              variant="outline"
              size="icon"
              className="h-9 w-9 shrink-0"
              onClick={() => {
                if (newKeyValue) {
                  navigator.clipboard.writeText(newKeyValue)
                  toast.success("已复制到剪贴板")
                }
              }}
            >
              <Copy className="h-3.5 w-3.5" />
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}
