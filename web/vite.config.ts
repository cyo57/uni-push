import path from "path"
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (!id.includes("node_modules")) return
          if (id.includes("node_modules/recharts")) return "charts"
          if (
            id.includes("node_modules/react-router-dom") ||
            id.includes("node_modules/@tanstack") ||
            id.includes("node_modules/axios") ||
            id.includes("node_modules/next-themes") ||
            id.includes("node_modules/sonner")
          ) {
            return "app-vendor"
          }
          return "vendor"
        },
      },
    },
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
})
