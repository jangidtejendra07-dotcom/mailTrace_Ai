import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'https://TUMHARA_APP_NAME.onrender.com', // Ise apne actual Render backend URL se replace karo
        changeOrigin: true,
      },
      '/graphql': {
        target: 'https://mailtrace-ai-backend.onrender.com', // Ise apne actual Render backend URL se replace karo
        changeOrigin: true,
      },
    },
  },
})