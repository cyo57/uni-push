import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { Link, useSearchParams } from "react-router-dom"
import { getChannels, getGroups, getUsers, createUser, updateUser } from "@/lib/api"
import type { UserCreate, UserUpdate, UserOut } from "@/lib/api"
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
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { toast } from "sonner"
import { Blocks, ChevronLeft, ChevronRight, Pencil, Plus, Radio } from "lucide-react"

const PAGE_SIZE = 10
const roleLabels = {
  admin: "管理员",
  user: "普通用户",
} as const

export function UsersPage() {
  const queryClient = useQueryClient()
  const [searchParams] = useSearchParams()
  const [page, setPage] = useState(0)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editingUser, setEditingUser] = useState<UserOut | null>(null)
  const [userActive, setUserActive] = useState(true)
  const highlightedId = searchParams.get("highlight")

  const { data, isLoading } = useQuery({
    queryKey: ["users", page],
    queryFn: () => getUsers(page * PAGE_SIZE, PAGE_SIZE),
  })

  const { data: groupsData } = useQuery({
    queryKey: ["groups", "all"],
    queryFn: () => getGroups(0, 200),
  })

  const { data: channelsData } = useQuery({
    queryKey: ["channels", "all"],
    queryFn: () => getChannels(0, 200),
  })

  const createMutation = useMutation({
    mutationFn: createUser,
    onSuccess: () => {
      toast.success("用户已创建")
      queryClient.invalidateQueries({ queryKey: ["users"] })
      setDialogOpen(false)
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: UserUpdate }) =>
      updateUser(id, payload),
    onSuccess: () => {
      toast.success("用户已更新")
      queryClient.invalidateQueries({ queryKey: ["users"] })
      setDialogOpen(false)
      setEditingUser(null)
    },
  })

  function openCreate() {
    setEditingUser(null)
    setUserActive(true)
    setDialogOpen(true)
  }

  function openEdit(user: UserOut) {
    setEditingUser(user)
    setUserActive(user.is_active)
    setDialogOpen(true)
  }

  function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault()
    const form = e.currentTarget
    const fd = new FormData(form)

    if (editingUser) {
      const payload: UserUpdate = {}
      const displayName = fd.get("display_name") as string
      const password = fd.get("password") as string
      const role = fd.get("role") as "admin" | "user"
      if (displayName) payload.display_name = displayName
      if (password) payload.password = password
      if (role) payload.role = role
      payload.is_active = userActive

      updateMutation.mutate({ id: editingUser.id, payload })
    } else {
      const payload: UserCreate = {
        username: fd.get("username") as string,
        display_name: fd.get("display_name") as string,
        password: fd.get("password") as string,
        role: (fd.get("role") as "admin" | "user") || "user",
      }
      createMutation.mutate(payload)
    }
  }

  const items = data?.items ?? []
  const total = data?.total ?? 0
  const totalPages = Math.ceil(total / PAGE_SIZE)
  const groupsById = new Map((groupsData?.items ?? []).map((group) => [group.id, group]))
  const channels = channelsData?.items ?? []

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold tracking-tight">用户管理</h1>
          <p className="text-sm text-muted-foreground mt-0.5">维护控制台账号、角色与启用状态</p>
        </div>
        <Button onClick={openCreate} size="sm" className="h-8 text-xs">
          <Plus className="mr-1.5 h-3.5 w-3.5" />
          新建用户
        </Button>
      </div>

      <TooltipProvider>
      <div className="rounded-lg border border-border/60 overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow className="border-border/60 hover:bg-transparent">
              <TableHead className="text-xs font-medium text-muted-foreground h-9">用户名</TableHead>
              <TableHead className="text-xs font-medium text-muted-foreground h-9">显示名称</TableHead>
              <TableHead className="text-xs font-medium text-muted-foreground h-9">角色</TableHead>
              <TableHead className="text-xs font-medium text-muted-foreground h-9">所属组</TableHead>
              <TableHead className="text-xs font-medium text-muted-foreground h-9">可用通道</TableHead>
              <TableHead className="text-xs font-medium text-muted-foreground h-9">状态</TableHead>
              <TableHead className="text-xs font-medium text-muted-foreground h-9">创建时间</TableHead>
              <TableHead className="text-xs font-medium text-muted-foreground h-9 text-right">操作</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              Array.from({ length: 5 }).map((_, i) => (
                <TableRow key={i} className="border-border/40">
                  <TableCell colSpan={8} className="py-3">
                    <Skeleton className="h-5 w-full" />
                  </TableCell>
                </TableRow>
              ))
            ) : items.length === 0 ? (
              <TableRow className="border-border/40">
                <TableCell
                  colSpan={8}
                  className="py-8 text-center text-sm text-muted-foreground"
                >
                  暂无用户
                </TableCell>
              </TableRow>
            ) : (
              items.map((user) => {
                const groupLinks = user.group_ids
                  .map((groupId) => groupsById.get(groupId))
                  .filter((group): group is NonNullable<typeof group> => Boolean(group))
                const directChannels = channels.filter((channel) =>
                  channel.authorized_user_ids.includes(user.id)
                )
                const inheritedChannels = channels.filter((channel) =>
                  channel.authorized_group_ids.some((groupId) => user.group_ids.includes(groupId))
                )
                const accessibleChannels = Array.from(
                  new Map(
                    [...directChannels, ...inheritedChannels].map((channel) => [channel.id, channel])
                  ).values()
                )

                return (
                <TableRow
                  key={user.id}
                  className={
                    highlightedId === user.id
                      ? "border-l-2 border-l-primary bg-primary/5"
                      : "border-border/40"
                  }
                >
                  <TableCell className="py-3 text-sm font-medium">{user.username}</TableCell>
                  <TableCell className="py-3 text-sm">{user.display_name}</TableCell>
                  <TableCell className="py-3">
                    <Badge
                      variant={user.role === "admin" ? "default" : "secondary"}
                      className={`text-[10px] font-normal ${
                        user.role === "admin"
                          ? "bg-primary/10 text-foreground hover:bg-primary/15"
                          : ""
                      }`}
                    >
                      {roleLabels[user.role]}
                    </Badge>
                  </TableCell>
                  <TableCell className="py-3">
                    {groupLinks.length > 0 ? (
                      <div className="flex flex-wrap items-center gap-1.5">
                        <Tooltip>
                          <TooltipTrigger>
                            <Badge variant="outline" className="gap-1 text-[10px] font-normal">
                              <Blocks className="h-3 w-3" />
                              {groupLinks.length} 个组
                            </Badge>
                          </TooltipTrigger>
                          <TooltipContent>
                            {groupLinks.map((group) => group.name).join("、")}
                          </TooltipContent>
                        </Tooltip>
                        {groupLinks.slice(0, 2).map((group) => (
                          <Link key={group.id} to={`/groups?highlight=${group.id}`}>
                            <Badge variant="secondary" className="text-[10px] font-normal">
                              {group.name}
                            </Badge>
                          </Link>
                        ))}
                        {groupLinks.length > 2 ? (
                          <Badge variant="secondary" className="text-[10px] font-normal">
                            +{groupLinks.length - 2}
                          </Badge>
                        ) : null}
                      </div>
                    ) : (
                      <span className="text-sm text-muted-foreground">-</span>
                    )}
                  </TableCell>
                  <TableCell className="py-3">
                    {accessibleChannels.length > 0 ? (
                      <div className="flex flex-wrap items-center gap-1.5">
                        <Tooltip>
                          <TooltipTrigger>
                            <Badge variant="outline" className="gap-1 text-[10px] font-normal">
                              <Radio className="h-3 w-3" />
                              {accessibleChannels.length} 条
                            </Badge>
                          </TooltipTrigger>
                          <TooltipContent>
                            直授 {directChannels.length} / 继承 {inheritedChannels.length}
                          </TooltipContent>
                        </Tooltip>
                        {accessibleChannels.slice(0, 2).map((channel) => (
                          <Link key={channel.id} to={`/channels?highlight=${channel.id}`}>
                            <Badge variant="secondary" className="text-[10px] font-normal">
                              {channel.name}
                            </Badge>
                          </Link>
                        ))}
                        {accessibleChannels.length > 2 ? (
                          <Badge variant="secondary" className="text-[10px] font-normal">
                            +{accessibleChannels.length - 2}
                          </Badge>
                        ) : null}
                      </div>
                    ) : (
                      <span className="text-sm text-muted-foreground">-</span>
                    )}
                  </TableCell>
                  <TableCell className="py-3">
                    {user.is_active ? (
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
                    {formatDate(user.created_at)}
                  </TableCell>
                  <TableCell className="py-3 text-right">
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-7 w-7"
                      onClick={() => openEdit(user)}
                      title="编辑用户"
                    >
                      <Pencil className="h-3.5 w-3.5" />
                    </Button>
                  </TableCell>
                </TableRow>
              )})
            )}
          </TableBody>
        </Table>
      </div>
      </TooltipProvider>

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
            <DialogTitle className="text-base">{editingUser ? "编辑用户" : "新建用户"}</DialogTitle>
            <DialogDescription className="text-xs">
              {editingUser
                ? "更新当前用户的基础信息"
                : "创建一个新的平台用户"}
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleSubmit} className="space-y-4">
            {!editingUser && (
              <div className="space-y-1.5">
                <Label htmlFor="username" className="text-xs font-medium">用户名</Label>
                <Input
                  id="username"
                  name="username"
                  required
                  minLength={3}
                  className="h-8 text-sm"
                />
              </div>
            )}
            <div className="space-y-1.5">
              <Label htmlFor="display_name" className="text-xs font-medium">显示名称</Label>
              <Input
                id="display_name"
                name="display_name"
                defaultValue={editingUser?.display_name}
                required
                className="h-8 text-sm"
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="password" className="text-xs font-medium">
                密码 {editingUser && "（留空则保持不变）"}
              </Label>
              <Input
                id="password"
                name="password"
                type="password"
                required={!editingUser}
                minLength={8}
                className="h-8 text-sm"
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="role" className="text-xs font-medium">角色</Label>
              <Select
                name="role"
                defaultValue={editingUser?.role ?? "user"}
              >
                <SelectTrigger className="h-8 text-sm">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="admin">管理员</SelectItem>
                  <SelectItem value="user">普通用户</SelectItem>
                </SelectContent>
              </Select>
            </div>
            {editingUser && (
              <div className="flex items-center justify-between rounded-lg border border-border/70 bg-muted/30 px-3 py-2.5">
                <div className="space-y-0.5">
                  <Label htmlFor="is_active" className="cursor-pointer text-sm font-medium">
                    启用用户
                  </Label>
                  <p className="text-xs text-muted-foreground">
                    关闭后该账号会立即失去控制台访问权限。
                  </p>
                </div>
                <Switch
                  id="is_active"
                  checked={userActive}
                  onCheckedChange={setUserActive}
                />
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
    </div>
  )
}
