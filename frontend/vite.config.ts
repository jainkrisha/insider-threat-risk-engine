import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Proxy /score, /health, /vault/* to the running FastAPI server on port 8000.
// This means the React dev server (port 5173) never has CORS issues.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/score':  { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/health': { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/vault':  { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/trend':  { target: 'http://127.0.0.1:8000', changeOrigin: true },
    },
  },
})
