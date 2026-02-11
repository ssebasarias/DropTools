import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    allowedHosts: [
      'localhost',
      'droptools.cloud',
      'www.droptools.cloud',
      '147.93.43.242',
    ],
  },
  build: {
    // Windows: avoid EPERM when dist is locked by antivirus/explorer
    emptyOutDir: false,
  },
})
