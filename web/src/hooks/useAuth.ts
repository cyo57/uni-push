import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { login as apiLogin, getMe } from "@/lib/api"
import type { LoginRequest, CurrentUser } from "@/lib/api"

const TOKEN_KEY = "token"

export function useAuth() {
  const queryClient = useQueryClient()

  const {
    data: user,
    isLoading,
    error,
  } = useQuery<CurrentUser>({
    queryKey: ["me"],
    queryFn: getMe,
    enabled: !!localStorage.getItem(TOKEN_KEY),
    retry: false,
  })

  const loginMutation = useMutation({
    mutationFn: (payload: LoginRequest) => apiLogin(payload),
    onSuccess: (data) => {
      localStorage.setItem(TOKEN_KEY, data.access_token)
      queryClient.invalidateQueries({ queryKey: ["me"] })
    },
  })

  const logout = () => {
    localStorage.removeItem(TOKEN_KEY)
    queryClient.clear()
    window.location.href = "/login"
  }

  return {
    user,
    isLoading,
    error,
    isAdmin: user?.role === "admin",
    login: loginMutation.mutateAsync,
    logout,
  }
}
