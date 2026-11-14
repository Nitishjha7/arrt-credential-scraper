import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// During development, /api/* is forwarded to the FastAPI server,
// so the React code can call "/api/records" without worrying about CORS.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': 'http://127.0.0.1:8000',
    },
  },
})
