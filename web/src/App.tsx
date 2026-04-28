import { Suspense, lazy } from "react"
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom"
import { useAuth } from "@/hooks/useAuth"
import { Layout } from "@/pages/Layout"

const LoginPage = lazy(() =>
  import("@/pages/LoginPage").then((module) => ({ default: module.LoginPage }))
)
const DashboardPage = lazy(() =>
  import("@/pages/DashboardPage").then((module) => ({ default: module.DashboardPage }))
)
const ChannelsPage = lazy(() =>
  import("@/pages/ChannelsPage").then((module) => ({ default: module.ChannelsPage }))
)
const PushKeysPage = lazy(() =>
  import("@/pages/PushKeysPage").then((module) => ({ default: module.PushKeysPage }))
)
const MessagesPage = lazy(() =>
  import("@/pages/MessagesPage").then((module) => ({ default: module.MessagesPage }))
)
const MessageDetailPage = lazy(() =>
  import("@/pages/MessageDetailPage").then((module) => ({ default: module.MessageDetailPage }))
)
const UsersPage = lazy(() =>
  import("@/pages/UsersPage").then((module) => ({ default: module.UsersPage }))
)
const ProfilePage = lazy(() =>
  import("@/pages/ProfilePage").then((module) => ({ default: module.ProfilePage }))
)
const GroupsPage = lazy(() =>
  import("@/pages/GroupsPage").then((module) => ({ default: module.GroupsPage }))
)
const AuditLogsPage = lazy(() =>
  import("@/pages/AuditLogsPage").then((module) => ({ default: module.AuditLogsPage }))
)

function PageFallback() {
  return <div className="h-full min-h-48 animate-pulse rounded-lg bg-muted/40" />
}

function RequireAuth({ children }: { children: React.ReactNode }) {
  const { user, isLoading } = useAuth()
  if (isLoading) return null
  if (!user) return <Navigate to="/login" replace />
  return <>{children}</>
}

function RequireAdmin({ children }: { children: React.ReactNode }) {
  const { user, isLoading } = useAuth()
  if (isLoading) return null
  if (!user) return <Navigate to="/login" replace />
  if (user.role !== "admin") return <Navigate to="/" replace />
  return <>{children}</>
}

function LazyPage({ children }: { children: React.ReactNode }) {
  return <Suspense fallback={<PageFallback />}>{children}</Suspense>
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route
          path="/login"
          element={
            <LazyPage>
              <LoginPage />
            </LazyPage>
          }
        />
        <Route
          path="/"
          element={
            <RequireAuth>
              <Layout />
            </RequireAuth>
          }
        >
          <Route
            index
            element={
              <LazyPage>
                <DashboardPage />
              </LazyPage>
            }
          />
          <Route
            path="channels"
            element={
              <LazyPage>
                <ChannelsPage />
              </LazyPage>
            }
          />
          <Route
            path="push-keys"
            element={
              <LazyPage>
                <PushKeysPage />
              </LazyPage>
            }
          />
          <Route
            path="messages"
            element={
              <LazyPage>
                <MessagesPage />
              </LazyPage>
            }
          />
          <Route
            path="messages/:id"
            element={
              <LazyPage>
                <MessageDetailPage />
              </LazyPage>
            }
          />
          <Route
            path="users"
            element={
              <RequireAdmin>
                <LazyPage>
                  <UsersPage />
                </LazyPage>
              </RequireAdmin>
            }
          />
          <Route
            path="groups"
            element={
              <RequireAdmin>
                <LazyPage>
                  <GroupsPage />
                </LazyPage>
              </RequireAdmin>
            }
          />
          <Route
            path="audit-logs"
            element={
              <RequireAdmin>
                <LazyPage>
                  <AuditLogsPage />
                </LazyPage>
              </RequireAdmin>
            }
          />
          <Route
            path="profile"
            element={
              <LazyPage>
                <ProfilePage />
              </LazyPage>
            }
          />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
