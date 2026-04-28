import { useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { useSearchParams } from "react-router-dom"
import { getChannels, getGroups, getUsers, createUser, updateUser } from "@/lib/api"
import type { UserCreate, UserOut, UserRole, UserUpdate } from "@/lib/api"
import { formatDate } from "@/lib/format"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
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
import { ScrollArea } from "@/components/ui/scroll-area"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Skeleton } from "@/components/ui/skeleton"
import { Switch } from "@/components/ui/switch"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import { toast } from "sonner"
import { Blocks, ChevronLeft, ChevronRight, Pencil, Plus, Radio, RotateCcw } from "lucide-react"

const PAGE_SIZE = 10

const roleLabels: Record<UserRole, string> = {
  admin: "管理员",
  user: "普通用户",
}

const statusOptions = [
  { label: "启用", value: "active" },
  { label: "停用", value: "inactive" },
] as const

type UserStatusFilter = (typeof statusOptions)[number]["value"]

function toggleArrayValue<T extends string>(values: T[], value: T, checked: boolean) {
  if (checked) {
    return Array.from(new Set([...values, value]))
  }

  return values.filter((item) => item !== value)
}

export function UsersPage() {
  const queryClient = useQueryClient()
  const [searchParams] = useSearchParams()
  const [page, setPage] = useState(0)
  const [search, setSearch] = useState("")
  const [selectedRoles, setSelectedRoles] = useState<UserRole[]>([])
  const [selectedStatuses, setSelectedStatuses] = useState<UserStatusFilter[]>([])
  const [selectedGroupFilters, setSelectedGroupFilters] = useState<string[]>([])
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editingUser, setEditingUser] = useState<UserOut | null>(null)
  const [userActive, setUserActive] = useState(true)
  const [formRole, setFormRole] = useState<UserRole>("user")
  const [selectedEditGroupIds, setSelectedEditGroupIds] = useState<string[]>([])
  const highlightedId = searchParams.get("highlight")

  const { data, isLoading } = useQuery({
    queryKey: [
      "users",
      page,
      search,
      selectedRoles.join(","),
      selectedStatuses.join(","),
      selectedGroupFilters.join(","),
    ],
    queryFn: () =>
      getUsers(page * PAGE_SIZE, PAGE_SIZE, {
        q: search || undefined,
        roles: selectedRoles,
        statuses: selectedStatuses,
        group_ids: selectedGroupFilters,
      }),
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
      queryClient.invalidateQueries({ queryKey: ["groups"] })
      setDialogOpen(false)
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: UserUpdate }) => updateUser(id, payload),
    onSuccess: () => {
      toast.success("用户已更新")
      queryClient.invalidateQueries({ queryKey: ["users"] })
      queryClient.invalidateQueries({ queryKey: ["groups"] })
      setDialogOpen(false)
      setEditingUser(null)
    },
  })

  function resetFilters() {
    setPage(0)
    setSearch("")
    setSelectedRoles([])
    setSelectedStatuses([])
    setSelectedGroupFilters([])
  }

  function openCreate() {
    setEditingUser(null)
    setUserActive(true)
    setFormRole("user")
    setSelectedEditGroupIds([])
    setDialogOpen(true)
  }

  function openEdit(user: UserOut) {
    setEditingUser(user)
    setUserActive(user.is_active)
    setFormRole(user.role)
    setSelectedEditGroupIds(user.group_ids)
    setDialogOpen(true)
  }

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const formData = new FormData(event.currentTarget)

    if (editingUser) {
      const payload: UserUpdate = {
        display_name: String(formData.get("display_name") || ""),
        role: formRole,
        is_active: userActive,
        group_ids: selectedEditGroupIds,
      }
      const password = String(formData.get("password") || "")
      if (password) {
        payload.password = password
      }
      updateMutation.mutate({ id: editingUser.id, payload })
      return
    }

    const payload: UserCreate = {
      username: String(formData.get("username") || ""),
      display_name: String(formData.get("display_name") || ""),
      password: String(formData.get("password") || ""),
      role: formRole,
      group_ids: selectedEditGroupIds,
    }
    createMutation.mutate(payload)
  }

  const items = data?.items ?? []
  const total = data?.total ?? 0
  const totalPages = Math.ceil(total / PAGE_SIZE)
  const groups = groupsData?.items ?? []
  const channels = channelsData?.items ?? []
  const groupsById = new Map(groups.map((group) => [group.id, group]))
  const hasActiveFilters =
    Boolean(search) ||
    selectedRoles.length > 0 ||
    selectedStatuses.length > 0 ||
    selectedGroupFilters.length > 0

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold tracking-tight">用户管理</h1>
          <p className="mt-0.5 text-sm text-muted-foreground">
            维护控制台账号、角色、用户组与启用状态
          </p>
        </div>
        <Button onClick={openCreate} size="sm" className="h-8 text-xs">
          <Plus className="mr-1.5 h-3.5 w-3.5" />
          新建用户
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
            placeholder="搜索用户名、显示名称"
            className="h-8 text-sm md:max-w-sm"
          />
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Badge variant="outline" className="font-normal">
              共 {total} 人
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
            <p className="text-xs font-medium text-muted-foreground">角色</p>
            <div className="flex flex-wrap gap-2">
              {(Object.keys(roleLabels) as UserRole[]).map((role) => (
                <label
                  key={role}
                  className="flex items-center gap-2 rounded-md border border-border/60 px-3 py-2 text-sm"
                >
                  <Checkbox
                    checked={selectedRoles.includes(role)}
                    onCheckedChange={(checked) => {
                      setPage(0)
                      setSelectedRoles((previous) =>
                        toggleArrayValue(previous, role, checked === true)
                      )
                    }}
                  />
                  <span>{roleLabels[role]}</span>
                </label>
              ))}
            </div>
          </div>

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
            <p className="text-xs font-medium text-muted-foreground">按用户组筛选</p>
            <ScrollArea className="h-32 rounded-md border border-border/60 p-3">
              <div className="space-y-2">
                {groups.length === 0 ? (
                  <p className="text-sm text-muted-foreground">暂无用户组</p>
                ) : (
                  groups.map((group) => (
                    <label key={group.id} className="flex items-center gap-2 text-sm">
                      <Checkbox
                        checked={selectedGroupFilters.includes(group.id)}
                        onCheckedChange={(checked) => {
                          setPage(0)
                          setSelectedGroupFilters((previous) =>
                            toggleArrayValue(previous, group.id, checked === true)
                          )
                        }}
                      />
                      <span>{group.name}</span>
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
                <TableHead className="h-9 text-xs font-medium text-muted-foreground">用户名</TableHead>
                <TableHead className="h-9 text-xs font-medium text-muted-foreground">显示名称</TableHead>
                <TableHead className="h-9 text-xs font-medium text-muted-foreground">角色</TableHead>
                <TableHead className="h-9 text-xs font-medium text-muted-foreground">所属组</TableHead>
                <TableHead className="h-9 text-xs font-medium text-muted-foreground">可用通道</TableHead>
                <TableHead className="h-9 text-xs font-medium text-muted-foreground">状态</TableHead>
                <TableHead className="h-9 text-xs font-medium text-muted-foreground">创建时间</TableHead>
                <TableHead className="h-9 text-right text-xs font-medium text-muted-foreground">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading ? (
                Array.from({ length: 5 }).map((_, index) => (
                  <TableRow key={index} className="border-border/40">
                    <TableCell colSpan={8} className="py-3">
                      <Skeleton className="h-5 w-full" />
                    </TableCell>
                  </TableRow>
                ))
              ) : items.length === 0 ? (
                <TableRow className="border-border/40">
                  <TableCell colSpan={8} className="py-8 text-center text-sm text-muted-foreground">
                    暂无用户
                  </TableCell>
                </TableRow>
              ) : (
                items.map((user) => {
                  const groupLinks = user.group_ids
                    .map((groupId) => groupsById.get(groupId))
                    .filter((group): group is NonNullable<typeof group> => Boolean(group))
                  const inheritedChannels = channels.filter((channel) =>
                    channel.authorized_group_ids.some((groupId) => user.group_ids.includes(groupId))
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
                          className="text-[10px] font-normal"
                        >
                          {roleLabels[user.role]}
                        </Badge>
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
                      <TableCell className="py-3">
                        {inheritedChannels.length > 0 ? (
                          <Tooltip>
                            <TooltipTrigger>
                              <Badge variant="outline" className="gap-1 text-[10px] font-normal">
                                <Radio className="h-3 w-3" />
                                {inheritedChannels.length} 条
                              </Badge>
                            </TooltipTrigger>
                            <TooltipContent>
                              {inheritedChannels.map((channel) => channel.name).join("、")}
                            </TooltipContent>
                          </Tooltip>
                        ) : (
                          <span className="text-sm text-muted-foreground">-</span>
                        )}
                      </TableCell>
                      <TableCell className="py-3">
                        {user.is_active ? (
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
        <DialogContent className="max-w-2xl border-border/60">
          <DialogHeader>
            <DialogTitle className="text-base">{editingUser ? "编辑用户" : "新建用户"}</DialogTitle>
            <DialogDescription className="text-xs">
              {editingUser ? "更新当前用户的基础信息与用户组关系" : "创建一个新的平台用户"}
            </DialogDescription>
          </DialogHeader>
          <form onSubmit={handleSubmit} className="space-y-4">
            {!editingUser ? (
              <div className="space-y-1.5">
                <Label htmlFor="username" className="text-xs font-medium">用户名</Label>
                <Input id="username" name="username" required minLength={3} className="h-8 text-sm" />
              </div>
            ) : null}

            <div className="grid gap-4 md:grid-cols-2">
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
                <Label htmlFor="role" className="text-xs font-medium">角色</Label>
                <Select value={formRole} onValueChange={(value) => setFormRole(value as UserRole)}>
                  <SelectTrigger className="h-8 text-sm">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="admin">管理员</SelectItem>
                    <SelectItem value="user">普通用户</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="password" className="text-xs font-medium">
                密码 {editingUser ? "（留空则保持不变）" : ""}
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

            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label className="text-xs font-medium">所属用户组</Label>
                <Badge variant="outline" className="text-[10px] font-normal">
                  已选 {selectedEditGroupIds.length} 个
                </Badge>
              </div>
              <ScrollArea className="h-40 rounded-md border border-border/60 p-3">
                <div className="space-y-2">
                  {groups.length === 0 ? (
                    <p className="text-sm text-muted-foreground">暂无可选用户组</p>
                  ) : (
                    groups.map((group) => (
                      <label key={group.id} className="flex items-center gap-2 text-sm">
                        <Checkbox
                          checked={selectedEditGroupIds.includes(group.id)}
                          onCheckedChange={(checked) =>
                            setSelectedEditGroupIds((previous) =>
                              toggleArrayValue(previous, group.id, checked === true)
                            )
                          }
                        />
                        <span>{group.name}</span>
                      </label>
                    ))
                  )}
                </div>
              </ScrollArea>
            </div>

            {editingUser ? (
              <div className="flex items-center justify-between rounded-lg border border-border/70 bg-muted/30 px-3 py-2.5">
                <div className="space-y-0.5">
                  <Label htmlFor="is_active" className="cursor-pointer text-sm font-medium">
                    启用用户
                  </Label>
                  <p className="text-xs text-muted-foreground">
                    关闭后该账号会立即失去控制台访问权限。
                  </p>
                </div>
                <Switch id="is_active" checked={userActive} onCheckedChange={setUserActive} />
              </div>
            ) : null}

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
    </div>
  )
}
