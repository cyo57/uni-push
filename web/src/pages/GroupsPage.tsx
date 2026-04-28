import { useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { useSearchParams } from "react-router-dom"
import {
  createGroup,
  deleteGroup,
  getChannels,
  getGroups,
  getUsers,
  grantGroupChannel,
  grantGroupMember,
  revokeGroupChannel,
  revokeGroupMember,
  updateGroup,
} from "@/lib/api"
import type { GroupCreate, GroupOut, GroupUpdate } from "@/lib/api"
import { formatDate } from "@/lib/format"
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
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Skeleton } from "@/components/ui/skeleton"
import { Switch } from "@/components/ui/switch"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Textarea } from "@/components/ui/textarea"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import { toast } from "sonner"
import { ChevronLeft, ChevronRight, Pencil, Plus, Radio, RotateCcw, Trash2, Users } from "lucide-react"

const PAGE_SIZE = 10

const roleLabels = {
  admin: "管理员",
  user: "普通用户",
} as const

const statusOptions = [
  { label: "启用", value: "active" },
  { label: "停用", value: "inactive" },
] as const

type GroupStatusFilter = (typeof statusOptions)[number]["value"]

function toggleArrayValue<T extends string>(values: T[], value: T, checked: boolean) {
  if (checked) {
    return Array.from(new Set([...values, value]))
  }

  return values.filter((item) => item !== value)
}

export function GroupsPage() {
  const queryClient = useQueryClient()
  const [searchParams] = useSearchParams()
  const [page, setPage] = useState(0)
  const [search, setSearch] = useState("")
  const [selectedStatuses, setSelectedStatuses] = useState<GroupStatusFilter[]>([])
  const [selectedMemberFilters, setSelectedMemberFilters] = useState<string[]>([])
  const [selectedChannelFilters, setSelectedChannelFilters] = useState<string[]>([])
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editingGroup, setEditingGroup] = useState<GroupOut | null>(null)
  const [groupActive, setGroupActive] = useState(true)
  const [deleteId, setDeleteId] = useState<string | null>(null)
  const [memberDialogOpen, setMemberDialogOpen] = useState(false)
  const [channelDialogOpen, setChannelDialogOpen] = useState(false)
  const [activeGroup, setActiveGroup] = useState<GroupOut | null>(null)
  const [selectedMemberIds, setSelectedMemberIds] = useState<string[]>([])
  const [selectedChannelIds, setSelectedChannelIds] = useState<string[]>([])
  const highlightedId = searchParams.get("highlight")

  const { data, isLoading } = useQuery({
    queryKey: [
      "groups",
      page,
      search,
      selectedStatuses.join(","),
      selectedMemberFilters.join(","),
      selectedChannelFilters.join(","),
    ],
    queryFn: () =>
      getGroups(page * PAGE_SIZE, PAGE_SIZE, {
        q: search || undefined,
        statuses: selectedStatuses,
        member_user_ids: selectedMemberFilters,
        channel_ids: selectedChannelFilters,
      }),
  })

  const { data: usersData } = useQuery({
    queryKey: ["users", "all"],
    queryFn: () => getUsers(0, 200),
  })

  const { data: channelsData } = useQuery({
    queryKey: ["channels", "all"],
    queryFn: () => getChannels(0, 200),
  })

  const createMutation = useMutation({
    mutationFn: createGroup,
    onSuccess: () => {
      toast.success("用户组已创建")
      queryClient.invalidateQueries({ queryKey: ["groups"] })
      setDialogOpen(false)
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: GroupUpdate }) => updateGroup(id, payload),
    onSuccess: () => {
      toast.success("用户组已更新")
      queryClient.invalidateQueries({ queryKey: ["groups"] })
      setDialogOpen(false)
      setEditingGroup(null)
    },
  })

  const deleteMutation = useMutation({
    mutationFn: deleteGroup,
    onSuccess: () => {
      toast.success("用户组已删除")
      queryClient.invalidateQueries({ queryKey: ["groups"] })
      queryClient.invalidateQueries({ queryKey: ["users"] })
      queryClient.invalidateQueries({ queryKey: ["channels"] })
      setDeleteId(null)
    },
  })

  const memberMutation = useMutation({
    mutationFn: async ({
      groupId,
      userId,
      checked,
    }: {
      groupId: string
      userId: string
      checked: boolean
    }) => (checked ? grantGroupMember(groupId, userId) : revokeGroupMember(groupId, userId)),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["groups"] })
      queryClient.invalidateQueries({ queryKey: ["users"] })
    },
  })

  const channelMutation = useMutation({
    mutationFn: async ({
      groupId,
      channelId,
      checked,
    }: {
      groupId: string
      channelId: string
      checked: boolean
    }) => (checked ? grantGroupChannel(groupId, channelId) : revokeGroupChannel(groupId, channelId)),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["groups"] })
      queryClient.invalidateQueries({ queryKey: ["channels"] })
    },
  })

  function resetFilters() {
    setPage(0)
    setSearch("")
    setSelectedStatuses([])
    setSelectedMemberFilters([])
    setSelectedChannelFilters([])
  }

  function openCreate() {
    setEditingGroup(null)
    setGroupActive(true)
    setDialogOpen(true)
  }

  function openEdit(group: GroupOut) {
    setEditingGroup(group)
    setGroupActive(group.is_active)
    setDialogOpen(true)
  }

  function openMembers(group: GroupOut) {
    setActiveGroup(group)
    setSelectedMemberIds(group.member_user_ids)
    setMemberDialogOpen(true)
  }

  function openChannels(group: GroupOut) {
    setActiveGroup(group)
    setSelectedChannelIds(group.channel_ids)
    setChannelDialogOpen(true)
  }

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const formData = new FormData(event.currentTarget)
    const payload: GroupCreate = {
      name: String(formData.get("name") || ""),
      description: String(formData.get("description") || "") || undefined,
      is_active: groupActive,
    }

    if (editingGroup) {
      updateMutation.mutate({
        id: editingGroup.id,
        payload: {
          name: payload.name,
          description: payload.description,
          is_active: payload.is_active,
        },
      })
      return
    }

    createMutation.mutate(payload)
  }

  function handleMemberChecked(userId: string, checked: boolean) {
    if (!activeGroup) return
    const previous = selectedMemberIds
    const next = toggleArrayValue(selectedMemberIds, userId, checked)
    setSelectedMemberIds(next)

    memberMutation.mutate(
      { groupId: activeGroup.id, userId, checked },
      {
        onError: () => {
          setSelectedMemberIds(previous)
        },
      }
    )
  }

  function handleChannelChecked(channelId: string, checked: boolean) {
    if (!activeGroup) return
    const previous = selectedChannelIds
    const next = toggleArrayValue(selectedChannelIds, channelId, checked)
    setSelectedChannelIds(next)

    channelMutation.mutate(
      { groupId: activeGroup.id, channelId, checked },
      {
        onError: () => {
          setSelectedChannelIds(previous)
        },
      }
    )
  }

  const items = data?.items ?? []
  const total = data?.total ?? 0
  const totalPages = Math.ceil(total / PAGE_SIZE)
  const users = usersData?.items ?? []
  const channels = channelsData?.items ?? []
  const usersById = new Map(users.map((user) => [user.id, user]))
  const channelsById = new Map(channels.map((channel) => [channel.id, channel]))
  const hasActiveFilters =
    Boolean(search) ||
    selectedStatuses.length > 0 ||
    selectedMemberFilters.length > 0 ||
    selectedChannelFilters.length > 0

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold tracking-tight">用户组</h1>
          <p className="mt-0.5 text-sm text-muted-foreground">
            通过用户组批量管理成员与通道授权范围
          </p>
        </div>
        <Button onClick={openCreate} size="sm" className="h-8 text-xs">
          <Plus className="mr-1.5 h-3.5 w-3.5" />
          新建用户组
        </Button>
      </div>

      <div className="space-y-4 rounded-lg border border-border/60 bg-card p-4">
        <div className="flex flex-col gap-3 md:flex-row md:items-center">
          <Input
            value={search}
            onChange={(event) => {
              setPage(0)
              setSearch(event.target.value)
            }}
            placeholder="搜索用户组名称、描述"
            className="h-8 text-sm md:max-w-sm"
          />
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Badge variant="outline" className="font-normal">
              共 {total} 组
            </Badge>
            {hasActiveFilters ? (
              <Button variant="ghost" size="sm" className="h-7 px-2 text-xs" onClick={resetFilters}>
                <RotateCcw className="mr-1 h-3 w-3" />
                清空筛选
              </Button>
            ) : null}
          </div>
        </div>

        <div className="grid gap-4 xl:grid-cols-3">
          <div className="space-y-2">
            <p className="text-xs font-medium text-muted-foreground">状态</p>
            <div className="flex flex-wrap gap-2">
              {statusOptions.map((status) => (
                <label
                  key={status.value}
                  className="flex items-center gap-2 rounded-md border border-border/60 px-3 py-2 text-sm"
                >
                  <Checkbox
                    checked={selectedStatuses.includes(status.value)}
                    onCheckedChange={(checked) => {
                      setPage(0)
                      setSelectedStatuses((previous) =>
                        toggleArrayValue(previous, status.value, checked === true)
                      )
                    }}
                  />
                  <span>{status.label}</span>
                </label>
              ))}
            </div>
          </div>

          <div className="space-y-2">
            <p className="text-xs font-medium text-muted-foreground">按成员筛选</p>
            <ScrollArea className="h-32 rounded-md border border-border/60 p-3">
              <div className="space-y-2">
                {users.length === 0 ? (
                  <p className="text-sm text-muted-foreground">暂无用户</p>
                ) : (
                  users.map((user) => (
                    <label key={user.id} className="flex items-center gap-2 text-sm">
                      <Checkbox
                        checked={selectedMemberFilters.includes(user.id)}
                        onCheckedChange={(checked) => {
                          setPage(0)
                          setSelectedMemberFilters((previous) =>
                            toggleArrayValue(previous, user.id, checked === true)
                          )
                        }}
                      />
                      <span>{user.display_name}</span>
                    </label>
                  ))
                )}
              </div>
            </ScrollArea>
          </div>

          <div className="space-y-2">
            <p className="text-xs font-medium text-muted-foreground">按通道筛选</p>
            <ScrollArea className="h-32 rounded-md border border-border/60 p-3">
              <div className="space-y-2">
                {channels.length === 0 ? (
                  <p className="text-sm text-muted-foreground">暂无通道</p>
                ) : (
                  channels.map((channel) => (
                    <label key={channel.id} className="flex items-center gap-2 text-sm">
                      <Checkbox
                        checked={selectedChannelFilters.includes(channel.id)}
                        onCheckedChange={(checked) => {
                          setPage(0)
                          setSelectedChannelFilters((previous) =>
                            toggleArrayValue(previous, channel.id, checked === true)
                          )
                        }}
                      />
                      <span>{channel.name}</span>
                    </label>
                  ))
                )}
              </div>
            </ScrollArea>
          </div>
        </div>
      </div>

      <TooltipProvider>
      <div className="overflow-hidden rounded-lg border border-border/60">
        <Table>
          <TableHeader>
            <TableRow className="border-border/60 hover:bg-transparent">
              <TableHead className="h-9 text-xs font-medium text-muted-foreground">名称</TableHead>
              <TableHead className="h-9 text-xs font-medium text-muted-foreground">状态</TableHead>
              <TableHead className="h-9 text-xs font-medium text-muted-foreground">成员预览</TableHead>
              <TableHead className="h-9 text-xs font-medium text-muted-foreground">通道预览</TableHead>
              <TableHead className="h-9 text-xs font-medium text-muted-foreground">更新时间</TableHead>
              <TableHead className="h-9 text-right text-xs font-medium text-muted-foreground">操作</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              Array.from({ length: 5 }).map((_, index) => (
                <TableRow key={index} className="border-border/40">
                  <TableCell colSpan={6} className="py-3">
                    <Skeleton className="h-5 w-full" />
                  </TableCell>
                </TableRow>
              ))
            ) : items.length === 0 ? (
              <TableRow className="border-border/40">
                <TableCell colSpan={6} className="py-8 text-center text-sm text-muted-foreground">
                  暂无用户组
                </TableCell>
              </TableRow>
            ) : (
              items.map((group) => {
                const memberLinks = group.member_user_ids
                  .map((userId) => usersById.get(userId))
                  .filter((user): user is NonNullable<typeof user> => Boolean(user))
                const channelLinks = group.channel_ids
                  .map((channelId) => channelsById.get(channelId))
                  .filter((channel): channel is NonNullable<typeof channel> => Boolean(channel))

                return (
                  <TableRow
                    key={group.id}
                    className={
                      highlightedId === group.id
                        ? "border-l-2 border-l-primary bg-primary/5"
                        : "border-border/40"
                    }
                  >
                    <TableCell className="py-3">
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-medium">{group.name}</span>
                          {group.description ? (
                            <Badge variant="outline" className="text-[10px] font-normal">
                              已备注
                            </Badge>
                          ) : null}
                        </div>
                        <p className="line-clamp-1 text-xs text-muted-foreground">
                          {group.description || "暂无说明"}
                        </p>
                      </div>
                    </TableCell>
                    <TableCell className="py-3">
                      <Badge
                        variant={group.is_active ? "default" : "outline"}
                        className={
                          group.is_active
                            ? "bg-emerald-500/15 text-[10px] font-normal text-emerald-400 hover:bg-emerald-500/20"
                            : "text-[10px] font-normal text-muted-foreground"
                        }
                      >
                        {group.is_active ? "启用" : "停用"}
                      </Badge>
                    </TableCell>
                    <TableCell className="py-3">
                      {memberLinks.length > 0 ? (
                        <Tooltip>
                          <TooltipTrigger>
                            <Badge variant="outline" className="gap-1 text-[10px] font-normal">
                              <Users className="h-3 w-3" />
                              {memberLinks.length} 人
                            </Badge>
                          </TooltipTrigger>
                          <TooltipContent>
                            {memberLinks.map((user) => user.display_name).join("、")}
                          </TooltipContent>
                        </Tooltip>
                      ) : (
                        <span className="text-sm text-muted-foreground">-</span>
                      )}
                    </TableCell>
                    <TableCell className="py-3">
                      {channelLinks.length > 0 ? (
                        <Tooltip>
                          <TooltipTrigger>
                            <Badge variant="outline" className="gap-1 text-[10px] font-normal">
                              <Radio className="h-3 w-3" />
                              {channelLinks.length} 条
                            </Badge>
                          </TooltipTrigger>
                          <TooltipContent>
                            {channelLinks.map((channel) => channel.name).join("、")}
                          </TooltipContent>
                        </Tooltip>
                      ) : (
                        <span className="text-sm text-muted-foreground">-</span>
                      )}
                    </TableCell>
                    <TableCell className="py-3 text-sm text-muted-foreground">
                      {formatDate(group.updated_at)}
                    </TableCell>
                    <TableCell className="py-3">
                      <div className="flex justify-end gap-1">
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-7 w-7"
                          onClick={() => openMembers(group)}
                          title="管理成员"
                        >
                          <Users className="h-3.5 w-3.5" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-7 w-7"
                          onClick={() => openChannels(group)}
                          title="管理通道"
                        >
                          <Radio className="h-3.5 w-3.5" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-7 w-7"
                          onClick={() => openEdit(group)}
                          title="编辑用户组"
                        >
                          <Pencil className="h-3.5 w-3.5" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-7 w-7 text-destructive hover:text-destructive"
                          onClick={() => setDeleteId(group.id)}
                          title="删除用户组"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
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
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>{editingGroup ? "编辑用户组" : "新建用户组"}</DialogTitle>
            <DialogDescription>
              {editingGroup ? "更新用户组基础信息" : "创建用于批量授权的新用户组"}
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="name">名称</Label>
              <Input id="name" name="name" required defaultValue={editingGroup?.name} className="h-9" />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="description">描述</Label>
              <Textarea
                id="description"
                name="description"
                defaultValue={editingGroup?.description ?? ""}
                placeholder="例如：值班组、项目组、告警订阅组"
                className="min-h-24 resize-none"
              />
            </div>
            <div className="flex items-center justify-between rounded-lg border border-border/70 bg-muted/30 px-3 py-3">
              <div className="space-y-0.5">
                <Label htmlFor="is_active" className="cursor-pointer">
                  启用用户组
                </Label>
                <p className="text-xs text-muted-foreground">
                  停用后保留关联关系，但不再作为有效授权来源。
                </p>
              </div>
              <Switch id="is_active" checked={groupActive} onCheckedChange={setGroupActive} />
            </div>
            <DialogFooter>
              <Button type="submit" disabled={createMutation.isPending || updateMutation.isPending}>
                {createMutation.isPending || updateMutation.isPending ? "保存中..." : "保存"}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      <Dialog open={memberDialogOpen} onOpenChange={setMemberDialogOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>{activeGroup?.name || "用户组"}成员</DialogTitle>
            <DialogDescription>选择后会立即生效，用户的通道可见范围会同步刷新。</DialogDescription>
          </DialogHeader>
          <ScrollArea className="max-h-[60vh] pr-4">
            <div className="space-y-2">
              {users.map((user) => (
                <label
                  key={user.id}
                  className="flex cursor-pointer items-start justify-between rounded-lg border border-border/60 px-3 py-3"
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium">{user.display_name}</span>
                      <Badge variant={user.role === "admin" ? "default" : "secondary"}>
                        {roleLabels[user.role]}
                      </Badge>
                    </div>
                    <p className="text-xs text-muted-foreground">{user.username}</p>
                  </div>
                  <Checkbox
                    checked={selectedMemberIds.includes(user.id)}
                    onCheckedChange={(checked) => handleMemberChecked(user.id, checked === true)}
                  />
                </label>
              ))}
            </div>
          </ScrollArea>
        </DialogContent>
      </Dialog>

      <Dialog open={channelDialogOpen} onOpenChange={setChannelDialogOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>{activeGroup?.name || "用户组"}通道权限</DialogTitle>
            <DialogDescription>组成员会自动继承这里选择的通道访问权限。</DialogDescription>
          </DialogHeader>
          <ScrollArea className="max-h-[60vh] pr-4">
            <div className="space-y-2">
              {channels.map((channel) => (
                <label
                  key={channel.id}
                  className="flex cursor-pointer items-start justify-between rounded-lg border border-border/60 px-3 py-3"
                >
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium">{channel.name}</span>
                      <Badge variant="secondary">{channel.type}</Badge>
                      {!channel.is_enabled ? <Badge variant="outline">停用</Badge> : null}
                    </div>
                    <p className="text-xs text-muted-foreground">{channel.webhook_url}</p>
                  </div>
                  <Checkbox
                    checked={selectedChannelIds.includes(channel.id)}
                    onCheckedChange={(checked) => handleChannelChecked(channel.id, checked === true)}
                  />
                </label>
              ))}
            </div>
          </ScrollArea>
        </DialogContent>
      </Dialog>

      <AlertDialog open={Boolean(deleteId)} onOpenChange={(open) => !open && setDeleteId(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>确认删除用户组？</AlertDialogTitle>
            <AlertDialogDescription>
              删除后将同时移除组成员关系和组授权关系，此操作不可撤销。
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>取消</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => deleteId && deleteMutation.mutate(deleteId)}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              删除
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
