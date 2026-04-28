import { useState } from "react"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import { useAuth } from "@/hooks/useAuth"
import { updateMe } from "@/lib/api"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"

export function ProfilePage() {
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const [displayName, setDisplayName] = useState(user?.display_name ?? "")
  const [currentPassword, setCurrentPassword] = useState("")
  const [newPassword, setNewPassword] = useState("")
  const [confirmPassword, setConfirmPassword] = useState("")

  const updateMutation = useMutation({
    mutationFn: updateMe,
    onSuccess: (data) => {
      if (data.access_token) {
        localStorage.setItem("token", data.access_token)
      }
      queryClient.setQueryData(["me"], data.user)
      setDisplayName(data.user.display_name)
      setCurrentPassword("")
      setNewPassword("")
      setConfirmPassword("")
      toast.success("个人信息已更新")
    },
  })

  function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault()

    if (newPassword && newPassword !== confirmPassword) {
      toast.error("两次输入的新密码不一致")
      return
    }

    const payload: {
      display_name?: string
      current_password?: string
      new_password?: string
    } = {}

    if (displayName.trim() && displayName !== user?.display_name) {
      payload.display_name = displayName
    }
    if (newPassword) {
      payload.current_password = currentPassword
      payload.new_password = newPassword
    }

    if (Object.keys(payload).length === 0) {
      toast.error("没有可提交的变更")
      return
    }

    updateMutation.mutate(payload)
  }

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-lg font-semibold tracking-tight">个人设置</h1>
        <p className="text-sm text-muted-foreground mt-0.5">更新显示名称和登录密码</p>
      </div>

      <Card className="border-border/60 shadow-none">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-medium">账号信息</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-1.5">
                <Label htmlFor="username" className="text-xs font-medium">用户名</Label>
                <Input id="username" value={user?.username ?? ""} disabled className="h-8 text-sm" />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="role" className="text-xs font-medium">角色</Label>
                <Input id="role" value={user?.role ?? ""} disabled className="h-8 text-sm" />
              </div>
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="display_name" className="text-xs font-medium">显示名称</Label>
              <Input
                id="display_name"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                className="h-8 text-sm"
                required
              />
            </div>

            <div className="space-y-1.5">
              <Label className="text-xs font-medium">所属用户组</Label>
              <div className="flex min-h-9 flex-wrap items-center gap-2 rounded-md border border-border/70 bg-muted/20 px-3 py-2">
                {user?.group_ids.length ? (
                  user.group_ids.map((groupId) => (
                    <Badge key={groupId} variant="secondary" className="font-mono text-[10px]">
                      {groupId}
                    </Badge>
                  ))
                ) : (
                  <span className="text-sm text-muted-foreground">当前未加入任何用户组</span>
                )}
              </div>
            </div>

            <div className="grid gap-4 md:grid-cols-3">
              <div className="space-y-1.5">
                <Label htmlFor="current_password" className="text-xs font-medium">当前密码</Label>
                <Input
                  id="current_password"
                  type="password"
                  value={currentPassword}
                  onChange={(e) => setCurrentPassword(e.target.value)}
                  className="h-8 text-sm"
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="new_password" className="text-xs font-medium">新密码</Label>
                <Input
                  id="new_password"
                  type="password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  className="h-8 text-sm"
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="confirm_password" className="text-xs font-medium">确认新密码</Label>
                <Input
                  id="confirm_password"
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  className="h-8 text-sm"
                />
              </div>
            </div>

            <div className="flex justify-end">
              <Button type="submit" size="sm" disabled={updateMutation.isPending}>
                {updateMutation.isPending ? "保存中..." : "保存变更"}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
