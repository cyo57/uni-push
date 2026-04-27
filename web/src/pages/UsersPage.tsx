import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { getUsers, createUser, updateUser } from "@/lib/api"
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
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { toast } from "sonner"
import {
  Plus,
  Pencil,
  ChevronLeft,
  ChevronRight,
} from "lucide-react"

const PAGE_SIZE = 10
const roleLabels = {
  admin: "管理员",
  user: "普通用户",
} as const

export function UsersPage() {
  const queryClient = useQueryClient()
  const [page, setPage] = useState(0)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editingUser, setEditingUser] = useState<UserOut | null>(null)
  const [userActive, setUserActive] = useState(true)

  const { data, isLoading } = useQuery({
    queryKey: ["users", page],
    queryFn: () => getUsers(page * PAGE_SIZE, PAGE_SIZE),
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

      <div className="rounded-lg border border-border/60 overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow className="border-border/60 hover:bg-transparent">
              <TableHead className="text-xs font-medium text-muted-foreground h-9">用户名</TableHead>
              <TableHead className="text-xs font-medium text-muted-foreground h-9">显示名称</TableHead>
              <TableHead className="text-xs font-medium text-muted-foreground h-9">角色</TableHead>
              <TableHead className="text-xs font-medium text-muted-foreground h-9">状态</TableHead>
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
                <TableCell
                  colSpan={6}
                  className="py-8 text-center text-sm text-muted-foreground"
                >
                  暂无用户
                </TableCell>
              </TableRow>
            ) : (
              items.map((user) => (
                <TableRow key={user.id} className="border-border/40">
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
