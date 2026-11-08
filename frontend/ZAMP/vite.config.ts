import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    // Dev only: forward API calls to the local FastAPI backend, the same way
    // nginx does in Docker/production, so VITE_API_BASE_URL=/api works everywhere.
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: false, // keep the browser's Host so redirects point back at the dev server
      },
    },
  },
})
