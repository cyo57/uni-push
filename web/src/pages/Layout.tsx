import { Link, useLocation, Outlet, Navigate } from "react-router-dom"
import { useAuth } from "@/hooks/useAuth"
import { Button } from "@/components/ui/button"
import { ThemeToggle } from "@/components/theme-toggle"
import {
  LayoutDashboard,
  Radio,
  KeyRound,
  Mail,
  Users,
  LogOut,
  Menu,
  X,
} from "lucide-react"
import { useState } from "react"

const navItems = [
  { path: "/", label: "概览", icon: LayoutDashboard },
  { path: "/channels", label: "通道管理", icon: Radio },
  { path: "/push-keys", label: "推送密钥", icon: KeyRound },
  { path: "/messages", label: "消息记录", icon: Mail },
]

const adminNavItems = [{ path: "/users", label: "用户管理", icon: Users }]
const roleLabels = {
  admin: "管理员",
  user: "普通用户",
} as const

export function Layout() {
  const { user, isAdmin, logout } = useAuth()
  const location = useLocation()
  const [mobileOpen, setMobileOpen] = useState(false)

  if (!user) return <Navigate to="/login" replace />

  const allNavItems = isAdmin ? [...navItems, ...adminNavItems] : navItems

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-background">
      {/* Sidebar */}
      <aside
        className={`fixed inset-y-0 left-0 z-50 w-60 border-r border-border bg-sidebar transition-transform duration-200 ease-in-out md:static md:translate-x-0 ${
          mobileOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="flex h-full flex-col">
          <div className="flex h-14 items-center border-b border-sidebar-border px-4">
            <Link to="/" className="flex items-center gap-2.5 font-semibold text-sidebar-foreground">
              <div className="flex h-7 w-7 items-center justify-center rounded-md bg-primary text-primary-foreground">
                <Radio className="h-4 w-4" />
              </div>
              <span className="text-sm tracking-tight">UniPush</span>
            </Link>
            <Button
              variant="ghost"
              size="icon"
              className="ml-auto h-8 w-8 text-sidebar-foreground md:hidden"
              onClick={() => setMobileOpen(false)}
            >
              <X className="h-4 w-4" />
            </Button>
          </div>
          <nav className="flex-1 space-y-0.5 px-3 py-4">
            {allNavItems.map((item) => {
              const active = location.pathname === item.path
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  onClick={() => setMobileOpen(false)}
                  className={`group relative flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-all ${
                    active
                      ? "bg-sidebar-accent text-sidebar-foreground"
                      : "text-sidebar-foreground/60 hover:bg-sidebar-accent/60 hover:text-sidebar-foreground"
                  }`}
                >
                  {active && (
                    <span className="absolute left-0 top-1/2 h-4 w-0.5 -translate-y-1/2 rounded-full bg-sidebar-foreground" />
                  )}
                  <item.icon className={`h-4 w-4 ${active ? "text-sidebar-foreground" : "text-sidebar-foreground/40 group-hover:text-sidebar-foreground/70"}`} />
                  {item.label}
                </Link>
              )
            })}
          </nav>
          <div className="border-t border-sidebar-border p-3">
            <div className="space-y-3 rounded-xl border border-sidebar-border/60 bg-sidebar-accent/40 p-3">
              <div className="flex items-center gap-3">
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-sidebar-primary text-sidebar-primary-foreground text-xs font-semibold">
                  {user.display_name.charAt(0).toUpperCase()}
                </div>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-sidebar-foreground">{user.display_name}</p>
                  <p className="truncate text-xs text-sidebar-foreground/50">
                    {roleLabels[user.role]}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <ThemeToggle compact className="flex-1 justify-center border-sidebar-border bg-sidebar hover:bg-sidebar-accent" />
                <Button
                  variant="ghost"
                  size="icon-sm"
                  className="shrink-0 text-sidebar-foreground/60 hover:text-sidebar-foreground hover:bg-sidebar-accent"
                  onClick={logout}
                  title="退出登录"
                >
                  <LogOut className="h-3.5 w-3.5" />
                </Button>
              </div>
            </div>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <div className="flex flex-1 flex-col overflow-hidden">
        <header className="flex h-14 items-center border-b border-border bg-background px-4 md:hidden">
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8"
            onClick={() => setMobileOpen(true)}
          >
            <Menu className="h-4 w-4" />
          </Button>
          <span className="ml-3 text-sm font-semibold">UniPush</span>
          <ThemeToggle compact className="ml-auto justify-center" />
        </header>
        <main className="flex-1 overflow-auto p-4 md:p-6">
          <Outlet />
        </main>
      </div>

      {/* Mobile overlay */}
      {mobileOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm md:hidden"
          onClick={() => setMobileOpen(false)}
        />
      )}
    </div>
  )
}
